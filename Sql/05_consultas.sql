CREATE OR REPLACE VIEW auditoria.v_configuracion AS
SELECT ta.id_tabla,ta.esquema::text,ta.nombre_tabla::text,ta.activa,
       ca.nombre_columna::text AS columna,ev.nombre AS operacion,
       cfg.id_config,cfg.activo AS regla_activa
FROM auditoria.tabla_auditada ta
JOIN auditoria.columna_auditada ca ON ca.id_tabla=ta.id_tabla
JOIN auditoria.configuracion_auditoria cfg ON cfg.id_columna=ca.id_columna
JOIN auditoria.evento ev ON ev.id_evento=cfg.id_evento;

CREATE OR REPLACE VIEW auditoria.v_historial AS
SELECT b.id_bitacora,b.fecha_hora,u.nombre_usuario AS usuario,e.ip_origen AS ip,
       t.esquema::text,t.nombre_tabla::text AS tabla,ev.nombre AS operacion,
       c.nombre_columna::text AS columna,b.registro_pk,b.valor_anterior,b.valor_nuevo,
       b.fila_anterior,b.fila_nueva,b.aplicacion
FROM auditoria.bitacora b
JOIN auditoria.configuracion_auditoria cfg ON cfg.id_config=b.id_config
JOIN auditoria.columna_auditada c ON c.id_columna=cfg.id_columna
JOIN auditoria.tabla_auditada t ON t.id_tabla=c.id_tabla
JOIN auditoria.evento ev ON ev.id_evento=cfg.id_evento
JOIN auditoria.usuario_auditado u ON u.id_usuario=b.id_usuario
JOIN auditoria.estacion_trabajo e ON e.id_estacion=b.id_estacion;
