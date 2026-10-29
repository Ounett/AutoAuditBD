-- Ejemplo para psql: \copy exporta en el CLIENTE (no se requiere superusuario servidor).
-- En la aplicación, el botón Exportar CSV realiza esta operación.
\copy (SELECT fecha_hora,usuario,esquema,tabla,operacion,columna,valor_anterior,valor_nuevo,ip,registro_pk FROM auditoria.v_historial ORDER BY fecha_hora DESC) TO 'reporte_autoaudit.csv' WITH CSV HEADER ENCODING 'UTF8'
