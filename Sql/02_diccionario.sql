-- Catálogo y diccionario PostgreSQL. Las tablas internas se excluyen.
CREATE OR REPLACE VIEW auditoria.v_diccionario AS
SELECT n.nspname::text AS esquema, c.relname::text AS tabla,
       a.attname::text AS columna, format_type(a.atttypid,a.atttypmod) AS tipo,
       a.attnotnull AS obligatorio,
       EXISTS (
         SELECT 1 FROM pg_index i
         WHERE i.indrelid=c.oid AND i.indisprimary AND a.attnum=ANY(i.indkey)
       ) AS es_pk
FROM pg_class c
JOIN pg_namespace n ON n.oid=c.relnamespace
JOIN pg_attribute a ON a.attrelid=c.oid
WHERE c.relkind IN ('r','p') AND a.attnum>0 AND NOT a.attisdropped
  AND n.nspname NOT IN ('auditoria','information_schema')
  AND n.nspname NOT LIKE 'pg_%';
