REVOKE ALL ON SCHEMA auditoria FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA auditoria FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA auditoria FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA auditoria FROM PUBLIC;
GRANT USAGE ON SCHEMA auditoria TO auditoria_admin,auditoria_lector;
GRANT SELECT ON ALL TABLES IN SCHEMA auditoria TO auditoria_admin,auditoria_lector;
GRANT EXECUTE ON FUNCTION auditoria.configurar_tabla(text,text,text[],text[]) TO auditoria_admin;
GRANT EXECUTE ON FUNCTION auditoria.cambiar_tabla(bigint,boolean) TO auditoria_admin;
GRANT EXECUTE ON FUNCTION auditoria.cambiar_regla(bigint,boolean) TO auditoria_admin;
GRANT EXECUTE ON FUNCTION auditoria.desplegar_trigger(bigint) TO auditoria_admin;
GRANT EXECUTE ON FUNCTION auditoria.comprobar_admin() TO auditoria_admin;
GRANT USAGE ON SCHEMA demo TO auditoria_admin;
GRANT SELECT ON ALL TABLES IN SCHEMA demo TO auditoria_admin;
DO $$ BEGIN
  IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='audit_web') THEN
    CREATE ROLE audit_web LOGIN;
  END IF;
END $$;
GRANT CONNECT ON DATABASE autoaudit_visual TO audit_web;
GRANT auditoria_admin TO audit_web;
