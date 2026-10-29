-- Ejecutar como postgres, tras 01-06. Repetible.
-- La aplicación usa una cuenta miembro de auditoria_admin para configurar.
REVOKE ALL ON SCHEMA auditoria FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA auditoria FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA auditoria FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA auditoria FROM PUBLIC;
GRANT USAGE ON SCHEMA auditoria TO auditoria_admin,auditoria_lector;
GRANT SELECT ON ALL TABLES IN SCHEMA auditoria TO auditoria_admin,auditoria_lector;
-- Queda prohibido INSERT, UPDATE y DELETE directo de bitácora para rol no propietario.
GRANT EXECUTE ON FUNCTION auditoria.configurar_tabla(text,text,text[],text[]) TO auditoria_admin;
GRANT EXECUTE ON FUNCTION auditoria.cambiar_tabla(bigint,boolean) TO auditoria_admin;
GRANT EXECUTE ON FUNCTION auditoria.cambiar_regla(bigint,boolean) TO auditoria_admin;
GRANT EXECUTE ON FUNCTION auditoria.desplegar_trigger(bigint) TO auditoria_admin;
GRANT EXECUTE ON FUNCTION auditoria.comprobar_admin() TO auditoria_admin;
-- No se concede EXECUTE de capturar_cambio a usuarios de interfaz.
GRANT USAGE ON SCHEMA demo TO auditoria_admin;
GRANT SELECT ON ALL TABLES IN SCHEMA demo TO auditoria_admin;
-- Roles creados para realizar pruebas y DBeaver: audit_web puede leer y configurar.
DO $$ BEGIN
  IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='audit_web') THEN
    CREATE ROLE audit_web LOGIN;
  END IF;
END $$;
GRANT CONNECT ON DATABASE autoaudit_visual TO audit_web;
GRANT auditoria_admin TO audit_web;
-- La contraseña de audit_web se asigna por separado con \password audit_web.
