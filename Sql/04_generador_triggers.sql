-- El generador construye exclusivamente identificadores previamente validados.
-- Un trigger AFTER por tabla, con función compartida de captura.
CREATE OR REPLACE FUNCTION auditoria.capturar_cambio() RETURNS TRIGGER
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog, auditoria, pg_temp AS $$
DECLARE
  v_id BIGINT := TG_ARGV[0]::BIGINT;
  v_activa BOOLEAN;
  v_old JSONB;
  v_new JSONB;
  v_clave JSONB := '{}'::jsonb;
  v_pk TEXT;
  v_val_old JSONB;
  v_val_new JSONB;
  v_usuario BIGINT;
  v_estacion BIGINT;
  v_item RECORD;
  v_ip TEXT := COALESCE(NULLIF(current_setting('autoaudit.client_ip',true),''), inet_client_addr()::text,'local');
BEGIN
  SELECT activa INTO v_activa FROM auditoria.tabla_auditada
  WHERE id_tabla=v_id AND esquema=TG_TABLE_SCHEMA AND nombre_tabla=TG_TABLE_NAME;
  IF NOT COALESCE(v_activa,FALSE) THEN RETURN NULL; END IF;

  IF TG_OP IN ('UPDATE','DELETE') THEN v_old := to_jsonb(OLD); END IF;
  IF TG_OP IN ('INSERT','UPDATE') THEN v_new := to_jsonb(NEW); END IF;

  FOR v_pk IN
    SELECT a.attname::text FROM pg_index i
    JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=ANY(i.indkey)
    WHERE i.indrelid=TG_RELID AND i.indisprimary
    ORDER BY a.attnum
  LOOP
    v_clave := v_clave || jsonb_build_object(v_pk,COALESCE(v_new,v_old)->v_pk);
  END LOOP;

  FOR v_item IN
    SELECT cfg.id_config, ca.nombre_columna::text AS columna
    FROM auditoria.configuracion_auditoria cfg
    JOIN auditoria.columna_auditada ca ON ca.id_columna=cfg.id_columna
    JOIN auditoria.evento ev ON ev.id_evento=cfg.id_evento
    WHERE ca.id_tabla=v_id AND cfg.activo AND ev.nombre=TG_OP
  LOOP
    v_val_old := CASE WHEN v_old IS NULL THEN NULL ELSE v_old->v_item.columna END;
    v_val_new := CASE WHEN v_new IS NULL THEN NULL ELSE v_new->v_item.columna END;
    -- Los UPDATE sin cambio real no se registran.
    IF TG_OP <> 'UPDATE' OR v_val_old IS DISTINCT FROM v_val_new THEN
      INSERT INTO auditoria.usuario_auditado(nombre_usuario) VALUES(COALESCE(NULLIF(current_setting('autoaudit.actor',true),''), session_user))
      ON CONFLICT(nombre_usuario) DO UPDATE SET nombre_usuario=EXCLUDED.nombre_usuario
      RETURNING id_usuario INTO v_usuario;
      INSERT INTO auditoria.estacion_trabajo(ip_origen) VALUES(left(v_ip,45))
      ON CONFLICT(ip_origen) DO UPDATE SET ip_origen=EXCLUDED.ip_origen
      RETURNING id_estacion INTO v_estacion;
      INSERT INTO auditoria.bitacora(
        id_config,id_usuario,id_estacion,registro_pk,valor_anterior,valor_nuevo,
        fila_anterior,fila_nueva,aplicacion
      ) VALUES (
        v_item.id_config,v_usuario,v_estacion,v_clave,
        CASE WHEN v_val_old IS NULL THEN NULL ELSE v_val_old #>> '{}' END,
        CASE WHEN v_val_new IS NULL THEN NULL ELSE v_val_new #>> '{}' END,
        v_old,v_new,current_setting('application_name',true)
      );
    END IF;
  END LOOP;
  RETURN NULL;
END $$;

CREATE OR REPLACE FUNCTION auditoria.desplegar_trigger(p_tabla BIGINT) RETURNS TEXT
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog, auditoria, pg_temp AS $$
DECLARE r RECORD; v_eventos TEXT; v_nombre TEXT; v_orden TEXT;
BEGIN
  PERFORM auditoria.comprobar_admin();
  SELECT esquema,nombre_tabla,activa INTO r FROM auditoria.tabla_auditada WHERE id_tabla=p_tabla;
  IF NOT FOUND THEN RAISE EXCEPTION 'Tabla no configurada: %',p_tabla; END IF;
  IF NOT EXISTS(
    SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname=r.esquema AND c.relname=r.nombre_tabla AND c.relkind IN ('r','p')
  ) THEN RAISE EXCEPTION 'Tabla de origen eliminada: %.%',r.esquema,r.nombre_tabla; END IF;
  v_nombre := 'trg_autoaudit_'||p_tabla;
  EXECUTE format('DROP TRIGGER IF EXISTS %I ON %I.%I',v_nombre,r.esquema,r.nombre_tabla);
  SELECT string_agg(nombre,' OR ' ORDER BY CASE nombre WHEN 'INSERT' THEN 1 WHEN 'UPDATE' THEN 2 ELSE 3 END)
  INTO v_eventos FROM (
    SELECT DISTINCT ev.nombre FROM auditoria.configuracion_auditoria cfg
    JOIN auditoria.columna_auditada ca ON cfg.id_columna=ca.id_columna
    JOIN auditoria.evento ev ON cfg.id_evento=ev.id_evento
    WHERE ca.id_tabla=p_tabla AND cfg.activo
  ) e;
  IF r.activa AND v_eventos IS NOT NULL THEN
    v_orden := format('CREATE TRIGGER %I AFTER %s ON %I.%I FOR EACH ROW EXECUTE FUNCTION auditoria.capturar_cambio(%L)',
       v_nombre,v_eventos,r.esquema,r.nombre_tabla,p_tabla::text);
    EXECUTE v_orden;
    RETURN 'Trigger '||v_nombre||' activo para '||r.esquema||'.'||r.nombre_tabla||' ('||v_eventos||')';
  END IF;
  RETURN 'Trigger eliminado o sin operaciones activas para '||r.esquema||'.'||r.nombre_tabla;
END $$;
