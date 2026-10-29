"""AutoAudit Visual Pro: servidor local Flask / PostgreSQL 18.
La interfaz se mantiene ligada a localhost por defecto. No publicar sin autenticación externa.
"""
from __future__ import annotations

import csv
import io
import os
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request, send_from_directory
import psycopg
import gestor_routes
from psycopg.rows import dict_row

load_dotenv()
BASE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder="Interfaz/static", static_url_path="/static")
app.json.ensure_ascii = False
app.json.sort_keys = False
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024


def json_safe(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_safe(v) for v in value]
    return value


@contextmanager
def db():
    connstring = os.environ.get("DATABASE_URL", "")
    if not connstring or "CAMBIAR_CLAVE" in connstring:
        raise RuntimeError("Debe configurarse DATABASE_URL en el archivo .env.")
    with psycopg.connect(connstring, row_factory=dict_row, connect_timeout=5,
                         options="-c application_name=AutoAudit_Visual") as conn:
        yield conn


def query(sql, args=()):
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            return [dict(row) for row in cur.fetchall()]


def execute_one(sql, args=()):
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            row = cur.fetchone()
            return dict(row) if row else {}


def positive_limit(s, default=100, maximum=1000):
    try:
        n = int(s)
    except (ValueError, TypeError):
        n = default
    return min(max(n, 1), maximum)


def filters(args):
    clauses = []
    params = []
    for key, column in (("usuario", "usuario"), ("columna", "columna"),
                        ("tabla", "tabla"), ("operacion", "operacion")):
        v = (args.get(key) or "").strip()
        if v:
            clauses.append(column + " = %s")
            params.append(v)
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


@app.route("/")
def index():
    return send_from_directory(os.path.join(BASE, "Interfaz/static"), "index.html")


@app.get("/api/status")
def status():
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    return jsonify({"listo":True})


@app.get("/api/resumen")
def resumen():
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT (SELECT count(*) FROM auditoria.tabla_auditada) AS tablas, "
                        "(SELECT count(*) FROM auditoria.tabla_auditada WHERE activa) AS activas, "
                        "(SELECT count(*) FROM auditoria.v_configuracion WHERE regla_activa) AS reglas, "
                        "(SELECT count(*) FROM auditoria.bitacora) AS eventos")
            stats = dict(cur.fetchone())
            cur.execute("SELECT operacion,count(*)::int AS cantidad FROM auditoria.v_historial GROUP BY operacion ORDER BY operacion")
            stats["operaciones"] = list(cur.fetchall())
            cur.execute("SELECT id_bitacora,fecha_hora,usuario,tabla,operacion,columna,valor_anterior,valor_nuevo "
                        "FROM auditoria.v_historial ORDER BY id_bitacora DESC LIMIT 6")
            stats["recientes"] = list(cur.fetchall())
            return jsonify(json_safe(stats))


@app.get("/api/catalogo")
def catalogo():
    rows = query("SELECT esquema,tabla,count(*)::int AS columnas FROM auditoria.v_diccionario "
                 "GROUP BY esquema,tabla ORDER BY esquema,tabla")
    return jsonify(rows)


@app.get("/api/columnas")
def columnas():
    esquema = (request.args.get("esquema") or "").strip()
    tabla = (request.args.get("tabla") or "").strip()
    if not esquema or not tabla:
        return jsonify([])
    return jsonify(query("SELECT columna,tipo,obligatorio,es_pk FROM auditoria.v_diccionario "
                         "WHERE esquema=%s AND tabla=%s ORDER BY columna", (esquema,tabla)))


@app.get("/api/configuracion")
def configuracion():
    tabs = query("SELECT id_tabla,esquema::text,nombre_tabla::text,activa,fecha_creacion "
                 "FROM auditoria.tabla_auditada ORDER BY id_tabla")
    rules = query("SELECT id_tabla,esquema,nombre_tabla,id_config,columna,operacion,regla_activa "
                  "FROM auditoria.v_configuracion ORDER BY id_tabla,columna,operacion")
    return jsonify(json_safe({"tablas":tabs,"reglas":rules}))


def json_post():
    if request.headers.get("X-AutoAudit-Action") != "1" or not request.is_json:
        raise ValueError("Se requiere petición JSON con cabecera X-AutoAudit-Action: 1")
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError("JSON inválido")
    return data


@app.post("/api/configurar")
def configurar():
    data = json_post()
    schema = data.get("esquema")
    table = data.get("tabla")
    cols = data.get("columnas")
    ops = data.get("operaciones")
    if not isinstance(schema,str) or not isinstance(table,str) or not isinstance(cols,list) or not isinstance(ops,list):
        raise ValueError("Tabla, esquema, columnas y operaciones son obligatorios")
    if any(not isinstance(s,str) or len(s)>63 for s in cols + ops):
        raise ValueError("Columnas u operaciones inválidas")
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT auditoria.configurar_tabla(%s,%s,%s,%s) AS id_tabla", (schema,table,cols,ops))
            table_id = cur.fetchone()["id_tabla"]
            cur.execute("SELECT auditoria.desplegar_trigger(%s) AS mensaje", (table_id,))
            msg = cur.fetchone()["mensaje"]
    return jsonify({"id_tabla":table_id,"mensaje":msg})


@app.post("/api/regla")
def regla():
    data = json_post()
    rule_id = int(data.get("id_config"))
    active = data.get("activo")
    if type(active) is not bool:
        raise ValueError("El estado debe ser booleano")
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id_tabla FROM auditoria.v_configuracion WHERE id_config=%s",(rule_id,))
            found = cur.fetchone()
            if not found: raise ValueError("No se encontró la regla")
            cur.execute("SELECT auditoria.cambiar_regla(%s,%s)",(rule_id,active))
            cur.execute("SELECT auditoria.desplegar_trigger(%s) AS mensaje", (found["id_tabla"],))
            msg=cur.fetchone()["mensaje"]
    return jsonify({"mensaje":msg})


@app.post("/api/tabla")
def tabla():
    data = json_post()
    table_id = int(data.get("id_tabla"))
    active = data.get("activo")
    if type(active) is not bool:
        raise ValueError("El estado debe ser booleano")
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT auditoria.cambiar_tabla(%s,%s)", (table_id,active))
            cur.execute("SELECT auditoria.desplegar_trigger(%s) AS mensaje", (table_id,))
            msg=cur.fetchone()["mensaje"]
    return jsonify({"mensaje":msg})


@app.post("/api/desplegar")
def desplegar():
    data = json_post()
    table_id=int(data.get("id_tabla"))
    return jsonify(execute_one("SELECT auditoria.desplegar_trigger(%s) AS mensaje",(table_id,)))


@app.get("/api/historial")
def historial():
    where, params = filters(request.args)
    limit=positive_limit(request.args.get("limite"),100,1000)
    rows=query("SELECT id_bitacora,fecha_hora,usuario,esquema,tabla,operacion,columna,"
               "valor_anterior,valor_nuevo,ip,registro_pk,fila_anterior,fila_nueva,aplicacion "
               "FROM auditoria.v_historial"+where+" ORDER BY id_bitacora DESC LIMIT %s",params+[limit])
    return jsonify(json_safe(rows))


@app.get("/api/exportar.csv")
def exportar():
    where, params = filters(request.args)
    limit=positive_limit(request.args.get("limite"),1000,10000)
    rows=query("SELECT fecha_hora,usuario,esquema,tabla,operacion,columna,valor_anterior,valor_nuevo,ip,"
               "registro_pk,aplicacion FROM auditoria.v_historial"+where+" ORDER BY id_bitacora DESC LIMIT %s",params+[limit])
    out=io.StringIO()
    writer=csv.DictWriter(out,fieldnames=["fecha_hora","usuario","esquema","tabla","operacion","columna", "valor_anterior","valor_nuevo","ip","registro_pk","aplicacion"])
    writer.writeheader()
    for row in rows: writer.writerow(json_safe(row))
    return Response("\ufeff"+out.getvalue(),mimetype="text/csv; charset=utf-8",headers={"Content-Disposition":"attachment; filename=autoaudit_historial.csv"})


@app.errorhandler(Exception)
def error(err):
    # Jamás exponer DSN ni trazas; los mensajes PostgreSQL de validación se muestran parcialmente.
    from werkzeug.exceptions import HTTPException
    if isinstance(err,HTTPException):
        return jsonify({"error":err.description}),err.code
    if isinstance(err, (ValueError, TypeError)):
        return jsonify({"error":str(err)}),400
    if isinstance(err, psycopg.Error):
        public_msg = str(err).split("\n")[0]
        if len(public_msg)>250: public_msg=public_msg[:250]
        return jsonify({"error":public_msg}),400
    app.logger.exception("Error del servidor")
    return jsonify({"error":"Error del servidor. Revisar la configuración y la terminal."}),500


gestor_routes.register(app,db,json_safe)


if __name__=="__main__":
    host=os.environ.get("AUTOAUDIT_HOST","127.0.0.1")
    port=int(os.environ.get("AUTOAUDIT_PORT","5050"))
    if host not in ("127.0.0.1", "localhost"):
        raise RuntimeError("El servidor solo puede usarse en localhost")
    print(f"AutoAudit Visual: http://{host}:{port}")
    app.run(host=host,port=port,debug=False)
