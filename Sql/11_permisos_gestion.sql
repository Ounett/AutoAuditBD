-- Actualización no destructiva para el módulo visual de datos.
-- Auditar no requiere conceder UPDATE/DELETE sobre la bitácora.
CREATE SCHEMA IF NOT EXISTS gestion;
GRANT USAGE, CREATE ON SCHEMA gestion TO auditoria_admin;
GRANT USAGE ON SCHEMA demo TO auditoria_admin;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA demo TO auditoria_admin;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA demo TO auditoria_admin;
-- Las tablas futuras del esquema gestion son creadas por la cuenta técnica
-- que ejecuta la interfaz, por lo que puede gestionarlas como propietaria.
