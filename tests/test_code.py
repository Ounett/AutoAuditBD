
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_installer_has_every_required_script():
    for n in (1,2,3,4,5,6,7,8,9,10):
        assert list((ROOT/'Sql').glob(f'{n:02d}_*.sql'))

def test_ui_assets_exist():
    for name in ('index.html','style.css','app.js'):
        assert (ROOT/'Interfaz'/'static'/name).is_file()

def test_security_roles_and_trigger_implementation():
    sql=(ROOT/'Sql'/'04_generador_triggers.sql').read_text()
    assert 'SECURITY DEFINER' in sql
    assert 'CREATE TRIGGER %I AFTER' in sql
    assert 'IS DISTINCT FROM' in sql
    assert 'fila_anterior' in sql
    assert 'fila_nueva' in sql
    assert 'format(' in sql

def test_localhost_default_and_debug_off():
    code=(ROOT/'app.py').read_text()
    assert '"127.0.0.1"' in code
    assert 'debug=False' in code
