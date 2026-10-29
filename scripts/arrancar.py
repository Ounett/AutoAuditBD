#!/usr/bin/env python3
"""Arranque sin pasos manuales: instala/configura una vez, luego abre localhost.

IMPORTANTE: la clave de administrador se solicita solo en la primera instalacion
cuando PostgreSQL no permite acceso administrativo sin autenticar. NUNCA se guarda.
"""
from __future__ import annotations

import getpass
import os
from pathlib import Path
import secrets
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser

from dotenv import dotenv_values
import psycopg

BASE = Path(__file__).resolve().parents[1]
ENV_FILE = BASE / ".env"
PG_HOST = "127.0.0.1"
PG_PORT = os.environ.get("AUTOAUDIT_PGPORT", "5432")
USE_LOCAL_PEER = False
DB_NAME = "autoaudit_visual"
APP_ROLE = "autoaudit_visual_local"
SQL_FILES = (
    "01_estructura.sql",
    "02_diccionario.sql",
    "03_configuracion.sql",
    "04_generador_triggers.sql",
    "05_consultas.sql",
    "06_datos_prueba.sql",
    "10_seguridad.sql",
    "11_permisos_gestion.sql",
    "12_contexto_usuarios.sql",
)


def admin_psql(sql: str | None = None, *, database: str = "postgres",
               password: str = "", script: Path | None = None) -> str:
    """Ejecutar psql sin contrasena en la linea de comandos ni en el historial.

    Usa PGPASSWORD solo en el proceso hijo. -w evita multiples peticiones.
    """
    if USE_LOCAL_PEER:
        # Autorizacion administrativa local via sudo + peer (predeterminada
        # al instalar PostgreSQL en Ubuntu/Mint). No exige clave de postgres.
        cmd = ["sudo", "-n", "-u", "postgres", "psql", "-X", "-w",
               "-p", PG_PORT, "-d", database, "-v", "ON_ERROR_STOP=1", "-At"]
    else:
        cmd = ["psql", "-X", "-w", "-h", PG_HOST, "-p", PG_PORT, "-U", "postgres",
               "-d", database, "-v", "ON_ERROR_STOP=1", "-At"]
    # SIEMPRE transmitir el SQL por stdin. El usuario del sistema "postgres"
    # normalmente NO puede atravesar /home/<usuario>/Descargas (chmod 700).
    # Con -f <ruta> fallaba con "Permiso denegado" pese a tener acceso a PostgreSQL.
    # El archivo se lee con el usuario que ejecuta AutoAudit, ANTES de sudo -u postgres.
    # PostgreSQL recibe el contenido como stdin, sin abrir rutas del directorio personal.
    cmd.extend(["-f", "-"])
    if script is not None:
        try:
            sql = script.read_text(encoding="utf-8")
        except OSError as exc:
            raise RuntimeError(f"No se pudo leer {script.name}: {exc}") from exc
    env = os.environ.copy()
    if USE_LOCAL_PEER:
        env.pop("PGPASSWORD", None)
    else:
        env["PGPASSWORD"] = password
    env.pop("PGSERVICE", None)
    env.pop("PGDATABASE", None)
    if USE_LOCAL_PEER:
        # No permitir que variables PG* heredadas cambien a TCP u otro rol.
        env.pop("PGHOST", None)
        env.pop("PGUSER", None)
        env.pop("PGPORT", None)
    cp = subprocess.run(cmd, cwd=BASE, env=env,
                        input=sql,
                        capture_output=True, text=True, timeout=90)
    if cp.returncode:
        error = (cp.stderr or cp.stdout).strip()
        raise RuntimeError(error[:1000] or "PostgreSQL devolvio un error")
    return cp.stdout.strip()


def check_current_connection() -> bool:
    if not ENV_FILE.exists():
        return False
    values = dotenv_values(ENV_FILE)
    dsn = values.get("DATABASE_URL")
    if not dsn or "CAMBIAR_CLAVE" in dsn:
        return False
    try:
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT to_regclass('auditoria.bitacora') IS NOT NULL")
                return bool(cur.fetchone()[0])
    except (psycopg.Error, OSError):
        return False


def write_env(app_password: str) -> None:
    # La contrasena automatica solo usa hexadecimal: no requiere escapes URL.
    contenido = (f"DATABASE_URL=postgresql://{APP_ROLE}:{app_password}@{PG_HOST}:{PG_PORT}/{DB_NAME}\n"
                 "AUTOAUDIT_HOST=127.0.0.1\nAUTOAUDIT_PORT=5050\n")
    tmp = ENV_FILE.with_name(".env.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(contenido)
        os.replace(tmp, ENV_FILE)
        os.chmod(ENV_FILE, 0o600)
    finally:
        if tmp.exists():
            tmp.unlink()


def try_local_peer() -> bool:
    """Intentar administracion de la instancia local mediante sudo/peer.

    Se usa sudo para autorizar la instalacion; no se deshabilita autenticacion.
    """
    global USE_LOCAL_PEER
    if not shutil.which("sudo"):
        return False
    try:
        # Si no hay sudo en cache, puede pedir la clave de Linux una vez.
        print("[INFO] Intentando administrar PostgreSQL con sudo local...", flush=True)
        subprocess.run(["sudo", "-v"], check=True, timeout=90)
        USE_LOCAL_PEER = True
        admin_psql("SHOW server_version_num;\n", password="")
        return True
    except (subprocess.CalledProcessError, RuntimeError, OSError, subprocess.TimeoutExpired):
        USE_LOCAL_PEER = False
        return False


def bootstrap() -> None:
    print("\n" + "=" * 63)
    print("AUTOAUDIT | INSTALACION AUTOMATICA INICIAL")
    print("=" * 63)
    print("Se creara/preparara 'autoaudit_visual' sin tocar 'autoaudit_db'.")
    print("La cuenta de la aplicacion se generara con clave aleatoria.")
    print("Se probara sudo local primero para evitar pedir una clave de PostgreSQL.\n")

    password = ""
    try:
        server_version = admin_psql("SHOW server_version_num;\n", password="").strip()
    except RuntimeError:
        if try_local_peer():
            server_version = admin_psql("SHOW server_version_num;\n").strip()
            print("[OK] Acceso administrativo local autorizado con sudo/peer.")
        else:
            for i in range(3):
                password = getpass.getpass("Contraseña de PostgreSQL (postgres, solo instalacion): ")
                try:
                    server_version = admin_psql("SHOW server_version_num;\n", password=password).strip()
                    break
                except RuntimeError as exc:
                    print("No se pudo autenticar: " + str(exc).splitlines()[0])
                    if i == 2:
                        raise RuntimeError("No se pudo acceder como postgres. Compruebe la clave.") from exc

    try:
        major = int(server_version) // 10000
    except ValueError as exc:
        raise RuntimeError("No se pudo determinar la version de PostgreSQL") from exc
    if major != 18:
        raise RuntimeError(f"Se necesita PostgreSQL 18 para la guia; se detecto {major}.")
    print("[OK] PostgreSQL 18 disponible.")

    db_exists = admin_psql(
        f"SELECT 1 FROM pg_database WHERE datname='{DB_NAME}';\n",password=password)
    if db_exists.strip() != "1":
        admin_psql(f"CREATE DATABASE {DB_NAME};\n",password=password)
        print(f"[OK] Base de datos {DB_NAME} creada.")
    else:
        print(f"[OK] Base de datos {DB_NAME} ya existe; no se eliminara.")

    for name in SQL_FILES:
        print("  Instalando " + name + " ...", flush=True)
        try:
            admin_psql(database=DB_NAME, password=password, script=BASE / "Sql" / name)
        except RuntimeError as exc:
            raise RuntimeError(f"Error al instalar Sql/{name}: {exc}") from exc
    print("[OK] Estructura, funciones, triggers y permisos configurados.")

    app_password = secrets.token_hex(24)
    admin_psql(f"""
DO $sql$ BEGIN
  IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='{APP_ROLE}') THEN
     CREATE ROLE {APP_ROLE} LOGIN;
  END IF;
END $sql$;
ALTER ROLE {APP_ROLE} WITH LOGIN PASSWORD '{app_password}';
GRANT auditoria_admin TO {APP_ROLE};
GRANT CONNECT ON DATABASE {DB_NAME} TO {APP_ROLE};
""", password=password)

    dsn = f"postgresql://{APP_ROLE}:{app_password}@{PG_HOST}:{PG_PORT}/{DB_NAME}"
    with psycopg.connect(dsn, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM auditoria.tabla_auditada")
            print(f"[OK] Usuario de la aplicacion probado ({cur.fetchone()[0]} tablas configuradas).")

    write_env(app_password)
    # Evitar retener innecesariamente una copia adicional de la clave administrativa.
    password = ""
    print("[OK] Credenciales locales guardadas en .env (permisos 600).")
    print("[OK] La proxima vez solo sera necesario: ./iniciar.sh\n")


def migrate_existing() -> None:
    """Primera ejecución de esta versión sobre una base ya existente."""
    marker=BASE / '.local' / 'gestion_migrated_v1'
    if marker.exists():
        return
    print('[INFO] Actualizando permisos de edición y contexto de usuarios...')
    if not try_local_peer():
        # Solo se solicita la credencial de PostgreSQL si no hay autenticación peer.
        key=getpass.getpass('Clave administrador postgres para actualización inicial: ')
    else:
        key=''
    for name in ('11_permisos_gestion.sql','12_contexto_usuarios.sql'):
        admin_psql(database=DB_NAME,password=key,script=BASE / 'Sql' / name)
    marker.parent.mkdir(exist_ok=True)
    marker.write_text('Aplicada migracion de gestión visual\n',encoding='utf8')
    os.chmod(marker,0o600)
    print('[OK] Gestión de registros habilitada.')


def start_server() -> int:
    values = dotenv_values(ENV_FILE)
    host = values.get("AUTOAUDIT_HOST") or "127.0.0.1"
    if host not in ("127.0.0.1", "localhost"):
        raise RuntimeError("Se bloquea el acceso publico. AUTOAUDIT_HOST debe ser 127.0.0.1")
    port = int(values.get("AUTOAUDIT_PORT") or "5050")
    url = f"http://127.0.0.1:{port}"
    print("=" * 63)
    print("AUTOAUDIT | SERVIDOR LOCAL")
    print("=" * 63)
    print("Presionar Ctrl+C para detener el servidor.")
    print("Abriendo " + url + " ...\n",flush=True)

    env = os.environ.copy()
    env.update({k: v for k, v in values.items() if v is not None})
    env["AUTOAUDIT_HOST"] = "127.0.0.1"
    process = subprocess.Popen([sys.executable, "app.py"], cwd=BASE, env=env)
    try:
        opened = False
        for _ in range(60):
            if process.poll() is not None:
                raise RuntimeError("El servidor no se inicio. Revise el error de Flask arriba.")
            try:
                with urllib.request.urlopen(url + "/api/status", timeout=0.5) as response:
                    if response.status == 200:
                        opened = True
                        break
            except (urllib.error.URLError, TimeoutError, OSError):
                time.sleep(0.25)
        if not opened:
            raise RuntimeError("No se pudo confirmar el servidor en localhost.")
        try:
            if not webbrowser.open(url, new=1):
                print("Abra manualmente " + url)
        except Exception:
            print("Abra manualmente " + url)
        return process.wait()
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=4)
            except subprocess.TimeoutExpired:
                process.kill()


def main() -> int:
    try:
        if not check_current_connection():
            bootstrap()
        else:
            print("[OK] Instalacion anterior detectada; no se reinstala PostgreSQL.")
        migrate_existing()
        return start_server()
    except KeyboardInterrupt:
        print("\nAutoAudit detenido.")
        return 0
    except (RuntimeError, OSError, subprocess.TimeoutExpired, psycopg.Error) as exc:
        print("\nERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
