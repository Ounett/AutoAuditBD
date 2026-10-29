from __future__ import annotations
import hmac
import re
import secrets
import time
from functools import wraps
from flask import jsonify, request, session, abort
from psycopg import sql
import auth_local

VALID_NAME=re.compile(r'^[a-z][a-z0-9_]{1,39}$')
SCHEMAS=('demo','gestion','public')
TYPES={'TEXT':'TEXT','VARCHAR':'VARCHAR(120)','ENTERO':'INTEGER',
       'DECIMAL':'NUMERIC(12,2)','FECHA':'DATE','BOOLEANO':'BOOLEAN'}
FAILED={}

def register(app, db, jsonify_safe):
    app.secret_key=auth_local.initialize()
    app.config.update(SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Strict',
                      PERMANENT_SESSION_LIFETIME=60*60*8)

    def current_user():
        uid=session.get('uid')
        if not uid: return None
        u=auth_local.get_user(uid)
        return u if u and u['activo'] else None

    def roles(*allowed):
        def deco(fn):
            @wraps(fn)
            def wrapped(*a,**kw):
                u=current_user()
                if not u: abort(401)
                if u['rol'] not in allowed: abort(403)
                return fn(*a,**kw)
            return wrapped
        return deco

    @app.before_request
    def protect():
        if not request.path.startswith('/api/') or request.path in ('/api/status','/api/auth/login'):
            return
        if not current_user():
            return jsonify({'error':'Debe iniciar sesión'}),401
        if request.method in ('POST','PUT','PATCH','DELETE'):
            token=session.get('csrf') or ''
            supplied=request.headers.get('X-CSRF-Token','')
            if not token or not hmac.compare_digest(token,supplied):
                return jsonify({'error':'Solicitud rechazada: token inválido'}),403
            if not request.is_json:
                return jsonify({'error':'Se requiere una petición JSON'}),400

    @app.after_request
    def secure_headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Referrer-Policy']='same-origin'
        response.headers['Content-Security-Policy']=("default-src 'self'; script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
        if request.path.startswith('/api/'):
            response.headers['Cache-Control']='no-store'
        return response

    def body():
        data=request.get_json(silent=True)
        if not isinstance(data,dict): raise ValueError('Cuerpo JSON inválido')
        return data

    def check_table(cur, schema, table, perm='SELECT'):
        if schema not in SCHEMAS or not isinstance(table,str):
            raise ValueError('Esquema o tabla no permitidos')
        cur.execute('''SELECT c.oid,has_table_privilege(current_user,c.oid,%s) AS permitido
                       FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                       WHERE n.nspname=%s AND c.relname=%s AND c.relkind IN ('r','p')''',
                    (perm,schema,table))
        item=cur.fetchone()
        if not item: raise ValueError('La tabla no existe')
        if not item['permitido']: abort(403,description='Sin permiso de '+perm)

    def columns(cur, schema, table):
        cur.execute('''SELECT column_name AS nombre,data_type AS tipo,
                (is_nullable='YES') AS nullable,column_default AS defecto,
                (is_identity='YES') AS identidad,(is_generated <> 'NEVER') AS generado
                FROM information_schema.columns
                WHERE table_schema=%s AND table_name=%s ORDER BY ordinal_position''',
                (schema,table))
        result=[dict(r) for r in cur.fetchall()]
        cur.execute('''SELECT a.attname AS nombre FROM pg_index i
            JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=ANY(i.indkey)
            JOIN pg_class c ON c.oid=i.indrelid
            JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname=%s AND c.relname=%s AND i.indisprimary
            ORDER BY a.attnum''',
            (schema,table))
        pks=[r['nombre'] for r in cur.fetchall()]
        for c in result: c['pk']=c['nombre'] in pks
        return result,pks

    def pk_where(pk,names):
        if not names or not isinstance(pk,dict) or set(pk)!=set(names) or any(
                v is None or isinstance(v,(dict,list)) for v in pk.values()):
            raise ValueError('Se requiere la clave primaria completa')
        return sql.SQL(' AND ').join(sql.SQL('{} = %s').format(sql.Identifier(n)) for n in names),[pk[n] for n in names]

    def clean_values(raw,cols,update=False):
        if not isinstance(raw,dict) or len(raw)>100: raise ValueError('Datos inválidos')
        catalog={x['nombre']:x for x in cols}
        out={}
        for k,v in raw.items():
            c=catalog.get(k)
            if not c or c['identidad'] or c['generado'] or (update and c['pk']):
                raise ValueError('Columna no editable: '+str(k))
            if isinstance(v,(list,dict)) or (isinstance(v,str) and len(v)>20000):
                raise ValueError('Valor no permitido: '+str(k))
            out[k]=v
        return out

    def actor(cur):
        cur.execute("SELECT set_config('autoaudit.actor',%s,true)",(current_user()['usuario'],))
        cur.execute("SELECT set_config('autoaudit.client_ip',%s,true)",((request.remote_addr or 'local')[:45],))

    @app.post('/api/auth/login')
    def login():
        data=body(); ip=request.remote_addr or 'local'; now=time.monotonic()
        attempts=[x for x in FAILED.get(ip,[]) if now-x<300]
        FAILED[ip]=attempts
        if len(attempts)>=8:
            return jsonify({'error':'Demasiados intentos. Reintentar en cinco minutos.'}),429
        user=auth_local.authenticate(str(data.get('usuario',''))[:64],str(data.get('clave','')))
        if not user:
            attempts.append(now)
            return jsonify({'error':'Credenciales incorrectas'}),401
        FAILED.pop(ip,None)
        session.clear(); session['uid']=user['id'];session['csrf']=secrets.token_urlsafe(32)
        session.permanent=True
        return jsonify({'usuario':user['usuario'],'rol':user['rol'],'csrf':session['csrf']})

    @app.get('/api/auth/me')
    def me():
        u=current_user()
        return jsonify({'usuario':u['usuario'],'rol':u['rol'],'csrf':session['csrf']})

    @app.post('/api/auth/logout')
    def logout():
        session.clear()
        return jsonify({'mensaje':'Sesión cerrada'})

    @app.post('/api/auth/password')
    def change_password():
        data=body(); u=current_user()
        if not auth_local.check_old_password(u['id'],str(data.get('actual',''))):
            raise ValueError('Contraseña actual incorrecta')
        auth_local.set_password(u['id'],str(data.get('nueva','')))
        return jsonify({'mensaje':'Contraseña actualizada'})

    @app.get('/api/auth/users')
    @roles('admin')
    def users(): return jsonify(auth_local.list_users())

    @app.post('/api/auth/users')
    @roles('admin')
    def create_user():
        data=body()
        auth_local.add_user(str(data.get('usuario','')).strip(),str(data.get('clave','')),data.get('rol'))
        return jsonify({'mensaje':'Usuario creado'}),201

    @app.post('/api/auth/users/estado')
    @roles('admin')
    def change_state():
        data=body()
        if type(data.get('activo')) is not bool: raise ValueError('Estado inválido')
        auth_local.set_enabled(int(data['id']),data['activo'],current_user()['id'])
        return jsonify({'mensaje':'Estado guardado'})

    for endpoint in ('configurar','regla','tabla','desplegar'):
        app.view_functions[endpoint]=roles('admin')(app.view_functions[endpoint])

    @app.get('/api/data/tablas')
    def list_tables():
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute('''SELECT n.nspname AS esquema,c.relname AS tabla,
                    has_table_privilege(current_user,c.oid,'SELECT') AS lectura,
                    has_table_privilege(current_user,c.oid,'INSERT') AS insercion,
                    has_table_privilege(current_user,c.oid,'UPDATE') AS edicion,
                    has_table_privilege(current_user,c.oid,'DELETE') AS eliminacion,
                    EXISTS(SELECT 1 FROM pg_index i WHERE i.indrelid=c.oid AND i.indisprimary) AS tiene_pk
                    FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                    WHERE n.nspname=ANY(%s) AND c.relkind IN ('r','p')
                    ORDER BY n.nspname,c.relname''',(list(SCHEMAS),))
                return jsonify([dict(x) for x in cur.fetchall()])

    @app.get('/api/data/registros')
    def list_records():
        schema=request.args.get('esquema','');table=request.args.get('tabla','')
        try: page=max(1,min(100000,int(request.args.get('pagina','1'))))
        except ValueError: page=1
        with db() as conn:
            with conn.cursor() as cur:
                check_table(cur,schema,table)
                cols,pks=columns(cur,schema,table)
                target=sql.Identifier(schema,table)
                cur.execute(sql.SQL('SELECT count(*) AS n FROM {}').format(target))
                total=cur.fetchone()['n']
                ordering=sql.SQL(' ORDER BY {} DESC').format(sql.Identifier(pks[0])) if pks else sql.SQL('')
                cur.execute(sql.SQL('SELECT * FROM {}{} LIMIT 30 OFFSET %s').format(target,ordering),((page-1)*30,))
                rows=[dict(x) for x in cur.fetchall()]
        return jsonify(jsonify_safe({'columnas':cols,'pk':pks,'registros':rows,'total':total,'pagina':page}))

    @app.post('/api/data/registros')
    @roles('admin','usuario')
    def add_record():
        data=body();schema=data.get('esquema');table=data.get('tabla')
        with db() as conn:
            with conn.cursor() as cur:
                check_table(cur,schema,table,'INSERT')
                cols,_=columns(cur,schema,table)
                values=clean_values(data.get('valores'),cols)
                actor(cur)
                target=sql.Identifier(schema,table)
                if values:
                    cmd=sql.SQL('INSERT INTO {} ({}) VALUES ({}) RETURNING *').format(
                        target,sql.SQL(',').join(map(sql.Identifier,values)),
                        sql.SQL(',').join([sql.Placeholder()]*len(values)))
                    cur.execute(cmd,list(values.values()))
                else: cur.execute(sql.SQL('INSERT INTO {} DEFAULT VALUES RETURNING *').format(target))
                created=dict(cur.fetchone())
        return jsonify({'mensaje':'Registro añadido','registro':jsonify_safe(created)}),201

    @app.put('/api/data/registros')
    @roles('admin','usuario')
    def edit_record():
        data=body();schema=data.get('esquema');table=data.get('tabla')
        with db() as conn:
            with conn.cursor() as cur:
                check_table(cur,schema,table,'UPDATE')
                cols,pks=columns(cur,schema,table)
                values=clean_values(data.get('valores'),cols,update=True)
                if not values: raise ValueError('No hay datos para modificar')
                wh,params=pk_where(data.get('pk'),pks)
                actor(cur)
                setters=sql.SQL(',').join(sql.SQL('{}=%s').format(sql.Identifier(k)) for k in values)
                cur.execute(sql.SQL('UPDATE {} SET {} WHERE {} RETURNING *').format(
                    sql.Identifier(schema,table),setters,wh),list(values.values())+params)
                row=cur.fetchone()
                if not row: abort(404,description='La fila ya no existe')
        return jsonify({'mensaje':'Registro modificado','registro':jsonify_safe(dict(row))})

    @app.delete('/api/data/registros')
    @roles('admin','usuario')
    def remove_record():
        data=body();schema=data.get('esquema');table=data.get('tabla')
        with db() as conn:
            with conn.cursor() as cur:
                check_table(cur,schema,table,'DELETE')
                _,pks=columns(cur,schema,table)
                wh,params=pk_where(data.get('pk'),pks)
                actor(cur)
                cur.execute(sql.SQL('DELETE FROM {} WHERE {} RETURNING *').format(sql.Identifier(schema,table),wh),params)
                row=cur.fetchone()
                if not row: abort(404,description='La fila ya no existe')
        return jsonify({'mensaje':'Registro eliminado','registro':jsonify_safe(dict(row))})

    @app.post('/api/data/tablas')
    @roles('admin')
    def create_table():
        data=body();name=data.get('nombre'); cols=data.get('columnas')
        if not isinstance(name,str) or not VALID_NAME.fullmatch(name):
            raise ValueError('Nombre inválido (minúsculas, números y _)')
        if not isinstance(cols,list) or not 1<=len(cols)<=12:
            raise ValueError('Se requieren de 1 a 12 columnas')
        names=[];definitions=[]
        for c in cols:
            if not isinstance(c,dict) or not VALID_NAME.fullmatch(str(c.get('nombre',''))):
                raise ValueError('Nombre de columna inválido')
            n=c['nombre'];typ=c.get('tipo')
            if n=='id' or n in names or typ not in TYPES: raise ValueError('Columna duplicada o tipo inválido')
            names.append(n)
            definitions.append(sql.SQL('{} {} {}').format(sql.Identifier(n),sql.SQL(TYPES[typ]),
                sql.SQL('NOT NULL') if c.get('obligatorio') is True else sql.SQL('')))
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql.SQL('CREATE TABLE {} (id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,{})').format(
                    sql.Identifier('gestion',name),sql.SQL(',').join(definitions)))
                cur.execute('SELECT auditoria.configurar_tabla(%s,%s,%s,%s) AS id',
                            ('gestion',name,names,['INSERT','UPDATE','DELETE']))
                tid=cur.fetchone()['id']
                cur.execute('SELECT auditoria.desplegar_trigger(%s)',(tid,))
        return jsonify({'mensaje':f'Tabla gestion.{name} creada con auditoría activa'}),201

    @app.post('/api/data/tablas/columna')
    @roles('admin')
    def add_column():
        data=body(); table=data.get('tabla');name=data.get('nombre');typ=data.get('tipo')
        if not isinstance(table,str) or not VALID_NAME.fullmatch(table) or not isinstance(name,str) or not VALID_NAME.fullmatch(name) or typ not in TYPES:
            raise ValueError('Tabla, columna o tipo inválidos')
        with db() as conn:
            with conn.cursor() as cur:
                check_table(cur,'gestion',table,'UPDATE')
                cur.execute(sql.SQL('ALTER TABLE {} ADD COLUMN {} {}').format(
                    sql.Identifier('gestion',table),sql.Identifier(name),sql.SQL(TYPES[typ])))
        return jsonify({'mensaje':'Columna agregada. Puede activarse en Auditorías.'})

    @app.delete('/api/data/tablas')
    @roles('admin')
    def delete_table():
        data=body();table=data.get('tabla')
        if not isinstance(table,str) or not VALID_NAME.fullmatch(table) or data.get('confirmar')!='gestion.'+table:
            raise ValueError('Confirmar escribiendo gestion.nombre_tabla')
        with db() as conn:
            with conn.cursor() as cur:
                check_table(cur,'gestion',table,'DELETE')
                cur.execute('SELECT id_tabla FROM auditoria.tabla_auditada WHERE esquema=%s AND nombre_tabla=%s',('gestion',table))
                row=cur.fetchone()
                if row:
                    cur.execute('SELECT auditoria.cambiar_tabla(%s,false)',(row['id_tabla'],))
                    cur.execute('SELECT auditoria.desplegar_trigger(%s)',(row['id_tabla'],))
                cur.execute(sql.SQL('DROP TABLE {} RESTRICT').format(sql.Identifier('gestion',table)))
        return jsonify({'mensaje':'Tabla eliminada; se conserva la bitácora histórica'})
