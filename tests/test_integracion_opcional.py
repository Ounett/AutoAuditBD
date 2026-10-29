import os
import pytest

@pytest.mark.skipif(os.getenv('AUTOAUDIT_INTEGRATION') != '1', reason='requiere PostgreSQL de pruebas y opt-in')
def test_connection_and_structure():
    import psycopg
    from dotenv import load_dotenv
    load_dotenv()
    with psycopg.connect(os.environ['DATABASE_URL']) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM auditoria.tabla_auditada")
            assert cur.fetchone()[0] >= 2
            cur.execute("SELECT count(*) FROM pg_trigger WHERE tgname LIKE 'trg_autoaudit_%'")
            assert cur.fetchone()[0] >= 2
