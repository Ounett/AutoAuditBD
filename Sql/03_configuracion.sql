CREATE OR REPLACE FUNCTION auditoria.comprobar_admin() RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog, auditoria, pg_temp AS $$
BEGIN
  IF NOT pg_has_role(session_user,'auditoria_admin','MEMBER') AND session_user <> 'postgres' THEN
    RAISE EXCEPTION 'Se requiere membresia en auditoria_admin';
  END IF;
END $$;

CREATE OR REPLACE FUNCTION auditoria.configurar_tabla(p_esquema TEXT,p_tabla TEXT,p_columnas TEXT[],p_eventos TEXT[])
RETURNS BIGINT LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog, auditoria, pg_temp AS $$
DECLARE v_oid OID; v_id BIGINT; v_col TEXT; v_ev TEXT; v_cid BIGINT; v_eid INT;
BEGIN
  PERFORM auditoria.comprobar_admin();
  IF p_esquema IS NULL OR p_tabla IS NULL OR p_esquema IN ('auditoria','information_schema') OR p_esquema LIKE 'pg_%' THEN
    RAISE EXCEPTION 'Esquema no permitido';
  END IF;
  SELECT c.oid INTO v_oid FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
  WHERE n.nspname=p_esquema AND c.relname=p_tabla AND c.relkind IN ('r','p');
  IF v_oid IS NULL THEN RAISE EXCEPTION 'La tabla %.% no existe',p_esquema,p_tabla; END IF;
  IF NOT EXISTS(SELECT 1 FROM pg_index WHERE indrelid=v_oid AND indisprimary) THEN
    RAISE EXCEPTION 'La tabla debe tener clave primaria';
  END IF;
  IF COALESCE(array_length(p_columnas,1),0)=0 OR COALESCE(array_length(p_eventos,1),0)=0 THEN
    RAISE EXCEPTION 'Se requiere al menos una columna y una operacion';
  END IF;
  FOREACH v_col IN ARRAY p_columnas LOOP
    IF NOT EXISTS(SELECT 1 FROM pg_attribute WHERE attrelid=v_oid AND attname=v_col AND attnum>0 AND NOT attisdropped) THEN
      RAISE EXCEPTION 'La columna % no existe',v_col;
    END IF;
  END LOOP;
  FOREACH v_ev IN ARRAY p_eventos LOOP
    IF v_ev NOT IN ('INSERT','UPDATE','DELETE') THEN RAISE EXCEPTION 'Evento no permitido: %',v_ev; END IF;
  END LOOP;
  INSERT INTO auditoria.tabla_auditada(esquema,nombre_tabla,activa) VALUES(p_esquema,p_tabla,TRUE)
  ON CONFLICT(esquema,nombre_tabla) DO UPDATE SET activa=TRUE RETURNING id_tabla INTO v_id;
  UPDATE auditoria.configuracion_auditoria cfg SET activo=FALSE,fecha_cambio=now()
    FROM auditoria.columna_auditada ca WHERE cfg.id_columna=ca.id_columna AND ca.id_tabla=v_id;
  FOREACH v_col IN ARRAY p_columnas LOOP
    INSERT INTO auditoria.columna_auditada(id_tabla,nombre_columna) VALUES(v_id,v_col)
    ON CONFLICT(id_tabla,nombre_columna) DO UPDATE SET nombre_columna=EXCLUDED.nombre_columna
    RETURNING id_columna INTO v_cid;
    FOREACH v_ev IN ARRAY p_eventos LOOP
      SELECT id_evento INTO v_eid FROM auditoria.evento WHERE nombre=v_ev;
      INSERT INTO auditoria.configuracion_auditoria(id_columna,id_evento,activo)
      VALUES(v_cid,v_eid,TRUE)
      ON CONFLICT(id_columna,id_evento) DO UPDATE SET activo=TRUE,fecha_cambio=now();
    END LOOP;
  END LOOP;
  RETURN v_id;
END $$;

CREATE OR REPLACE FUNCTION auditoria.cambiar_regla(p_config BIGINT,p_activo BOOLEAN)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog, auditoria, pg_temp AS $$
BEGIN
  PERFORM auditoria.comprobar_admin();
  UPDATE auditoria.configuracion_auditoria SET activo=p_activo,fecha_cambio=now() WHERE id_config=p_config;
  IF NOT FOUND THEN RAISE EXCEPTION 'Regla desconocida: %',p_config; END IF;
END $$;

CREATE OR REPLACE FUNCTION auditoria.cambiar_tabla(p_tabla BIGINT,p_activa BOOLEAN)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog, auditoria, pg_temp AS $$
BEGIN
  PERFORM auditoria.comprobar_admin();
  UPDATE auditoria.tabla_auditada SET activa=p_activa WHERE id_tabla=p_tabla;
  IF NOT FOUND THEN RAISE EXCEPTION 'Tabla desconocida: %',p_tabla; END IF;
END $$;
