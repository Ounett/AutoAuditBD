from pathlib import Path
import importlib.util
import os
import sys
import types
from unittest import mock


def load_module(monkeypatch):
    fake_dotenv = types.ModuleType("dotenv")
    fake_dotenv.dotenv_values = lambda p: dict(line.strip().split("=", 1)
                    for line in Path(p).read_text().splitlines()
                    if line.strip() and not line.startswith("#"))
    fake_psycopg = types.ModuleType("psycopg")
    fake_psycopg.Error = type("PgError", (Exception,), {})
    fake_psycopg.connect = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "dotenv", fake_dotenv)
    monkeypatch.setitem(sys.modules, "psycopg", fake_psycopg)
    name = "test_arranque_module"
    path = Path(__file__).resolve().parents[1] / "scripts" / "arrancar.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_env_stored_as_private_file_and_no_admin_secret(tmp_path, monkeypatch):
    mod = load_module(monkeypatch)
    mod.ENV_FILE = tmp_path / ".env"
    mod.write_env("a1b2c3")
    data = mod.ENV_FILE.read_text()
    assert "autoaudit_visual_local:a1b2c3@" in data
    assert "postgres:" not in data
    assert (mod.ENV_FILE.stat().st_mode & 0o777) == 0o600


def test_repeat_start_reuses_existing_config(tmp_path, monkeypatch):
    mod = load_module(monkeypatch)
    mod.ENV_FILE = tmp_path / ".env"
    mod.write_env("a1b2c3")

    class Cursor:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, sql): pass
        def fetchone(self): return (True,)
    class Conn:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def cursor(self): return Cursor()
    monkeypatch.setattr(mod.psycopg, "connect", lambda *a, **kw: Conn())
    assert mod.check_current_connection() is True
    with mock.patch.object(mod, "bootstrap") as bootstrap, mock.patch.object(mod, "migrate_existing") as migrar, mock.patch.object(mod, "start_server", return_value=0):
        assert mod.main() == 0
        bootstrap.assert_not_called()


def test_first_time_generates_app_role_without_saving_admin_pass(tmp_path, monkeypatch):
    mod = load_module(monkeypatch)
    mod.BASE = tmp_path
    mod.ENV_FILE = tmp_path / ".env"
    (tmp_path / "Sql").mkdir()
    for file in mod.SQL_FILES:
        (tmp_path / "Sql" / file).write_text("SELECT 1;")
    seen = []
    def fake_admin_psql(sql=None, *, password="", database="postgres", script=None):
        seen.append((sql, password, database, script))
        if sql and "server_version_num" in sql:
            if not password:
                raise RuntimeError("fe_sendauth: no password supplied")
            return "180006"
        if sql and "SELECT 1 FROM pg_database" in sql:
            return ""  # DB does not exist
        return "OK"
    class Cursor:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, sql): pass
        def fetchone(self): return (2,)
    class Conn:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def cursor(self): return Cursor()
    monkeypatch.setattr(mod, "admin_psql", fake_admin_psql)
    monkeypatch.setattr(mod, "try_local_peer", lambda: False)
    monkeypatch.setattr(mod.getpass, "getpass", lambda prompt: "clave_privada_admin")
    monkeypatch.setattr(mod.psycopg, "connect", lambda *a, **kw: Conn())
    mod.bootstrap()
    assert mod.ENV_FILE.exists()
    assert "clave_privada_admin" not in mod.ENV_FILE.read_text()
    assert len([x for x in seen if x[3] is not None]) == len(mod.SQL_FILES)
    role_statements = [x[0] for x in seen if x[0] and "ALTER ROLE" in x[0]]
    assert len(role_statements) == 1
    assert "autoaudit_visual_local" in role_statements[0]


def test_local_peer_is_used_without_postgres_password(tmp_path, monkeypatch):
    mod = load_module(monkeypatch)
    mod.BASE = tmp_path
    mod.ENV_FILE = tmp_path / ".env"
    (tmp_path / "Sql").mkdir()
    for file in mod.SQL_FILES:
        (tmp_path / "Sql" / file).write_text("SELECT 1;")
    calls = []
    def fake_psql(sql=None, *, database="postgres", password="", script=None):
        calls.append((sql, password, script, mod.USE_LOCAL_PEER))
        if sql and "server_version_num" in sql:
            if mod.USE_LOCAL_PEER:
                return "180006"
            raise RuntimeError("fe_sendauth: no password supplied")
        if sql and "SELECT 1 FROM pg_database" in sql:
            return ""
        return "OK"
    class Cursor:
        def __enter__(self): return self
        def __exit__(self,*a): pass
        def execute(self,*a): pass
        def fetchone(self): return (2,)
    class Conn:
        def __enter__(self): return self
        def __exit__(self,*a): pass
        def cursor(self): return Cursor()
    def fake_peer():
        mod.USE_LOCAL_PEER = True
        return True
    monkeypatch.setattr(mod,"admin_psql",fake_psql)
    monkeypatch.setattr(mod,"try_local_peer",fake_peer)
    monkeypatch.setattr(mod.getpass,"getpass",lambda *args: (_ for _ in ()).throw(AssertionError("No se debe pedir clave de postgres")))
    monkeypatch.setattr(mod.psycopg,"connect",lambda *a,**kw: Conn())
    mod.bootstrap()
    assert mod.ENV_FILE.exists()
    assert all(password == "" for _,password,_,_ in calls)
    assert any(mode for _,_,_,mode in calls)


def test_peer_sql_script_is_sent_over_stdin_instead_of_opened_as_postgres(tmp_path, monkeypatch):
    mod = load_module(monkeypatch)
    sqlfile = tmp_path / "01_estructura.sql"
    sqlfile.write_text("CREATE SCHEMA IF NOT EXISTS auditoria;", encoding="utf-8")
    mod.USE_LOCAL_PEER = True
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["input"] = kwargs.get("input")
        return types.SimpleNamespace(returncode=0, stdout="CREATE SCHEMA\n", stderr="")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    mod.admin_psql(script=sqlfile, database="autoaudit_visual")
    assert captured["input"] == sqlfile.read_text(encoding="utf-8")
    assert "-f" in captured["cmd"]
    assert captured["cmd"][captured["cmd"].index("-f") + 1] == "-"
    assert str(sqlfile) not in captured["cmd"]
    assert captured["cmd"][:4] == ["sudo", "-n", "-u", "postgres"]
