"""Controles estáticos de componentes; no sustituyen la prueba SQL real."""
import ast
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_python_modules_parse():
    for name in ('app.py','auth_local.py','gestor_routes.py','scripts/arrancar.py','scripts/restablecer_admin.py'):
        ast.parse((ROOT/name).read_text(),filename=name)

def test_crud_all_verbs_and_privileges():
    t=(ROOT/'gestor_routes.py').read_text()
    for method in ('SELECT','INSERT','UPDATE','DELETE'):
        assert method in t
    for endpoint in ('/api/data/registros','/api/data/tablas','/api/auth/login','/api/auth/users'):
        assert endpoint in t
    assert 'sql.Identifier' in t
    assert 'X-CSRF-Token' in t

def test_audit_actor_and_grants():
    t=(ROOT/'Sql/12_contexto_usuarios.sql').read_text()
    assert "current_setting('autoaudit.actor',true)" in t
    permissions=(ROOT/'Sql/11_permisos_gestion.sql').read_text()
    assert 'GRANT SELECT, INSERT, UPDATE, DELETE' in permissions
    assert 'CREATE SCHEMA IF NOT EXISTS gestion' in permissions

def test_login_frontend_and_no_external_cdn():
    html=(ROOT/'Interfaz/static/index.html').read_text()
    assert 'login-form' in html and 'page-users' in html and 'page-records' in html
    assert 'http://' not in html and 'https://' not in html

def test_migration_preserves_database():
    s=(ROOT/'scripts/arrancar.py').read_text()
    assert 'migrate_existing' in s
    assert 'DROP DATABASE' not in s
    assert '12_contexto_usuarios.sql' in s
