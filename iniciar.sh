#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

es_apt_compatible() {
    command -v apt-get >/dev/null 2>&1 && test -r /etc/os-release
}

instalar_python_si_falta() {
    if command -v python3 >/dev/null 2>&1; then return; fi
    if ! es_apt_compatible; then
        echo 'ERROR: se necesita Python 3; instalacion automatica disponible solo en Ubuntu/Linux Mint.' >&2
        exit 1
    fi
    echo '[INFO] Instalando Python 3...'
    sudo apt-get update
    sudo apt-get install -y python3 python3-venv python3-pip
}

instalar_postgresql18_si_falta() {
    if command -v psql >/dev/null 2>&1 &&
       dpkg-query -W -f='${Status}' postgresql-18 2>/dev/null | grep -q 'install ok installed'; then
        return
    fi
    if ! es_apt_compatible; then
        echo 'ERROR: instalar PostgreSQL 18 manualmente. Este instalador admite Ubuntu/Linux Mint.' >&2
        exit 1
    fi
    . /etc/os-release
    case "${ID:-}" in
        ubuntu|linuxmint) ;;
        *) echo 'ERROR: distribucion no compatible con instalacion automatica.' >&2; exit 1 ;;
    esac
    CODENAME="${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}"
    case "$CODENAME" in
        jammy|noble|resolute|stonking) ;;
        *) echo "ERROR: base Ubuntu no reconocida ($CODENAME). Revisar instalacion PostgreSQL." >&2; exit 1 ;;
    esac

    echo "[INFO] PostgreSQL 18 no esta instalado. Preparando paquetes para Ubuntu $CODENAME..."
    sudo apt-get update
    if ! apt-cache show postgresql-18 >/dev/null 2>&1; then
        sudo apt-get install -y curl ca-certificates
        sudo install -d -m 755 /usr/share/postgresql-common/pgdg
        sudo curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
          -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc
        if ! grep -Rql 'apt.postgresql.org/pub/repos/apt' /etc/apt/sources.list.d /etc/apt/sources.list 2>/dev/null; then
            printf 'Types: deb\nURIs: https://apt.postgresql.org/pub/repos/apt\nSuites: %s-pgdg\nArchitectures: %s\nComponents: main\nSigned-By: /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc\n' \
              "$CODENAME" "$(dpkg --print-architecture)" | sudo tee /etc/apt/sources.list.d/pgdg.sources >/dev/null
        fi
        sudo apt-get update
    fi
    sudo apt-get install -y postgresql-18 postgresql-client-18
}

preparar_cluster18() {
    if ! command -v pg_lsclusters >/dev/null 2>&1; then
        echo 'ERROR: no se encuentra pg_lsclusters tras instalar PostgreSQL.' >&2
        exit 1
    fi
    local puerto cluster
    puerto="$(pg_lsclusters -h | awk '$1=="18" && $4=="online" {print $3; exit}')"
    if [ -z "$puerto" ]; then
        cluster="$(pg_lsclusters -h | awk '$1=="18" {print $2; exit}')"
        if [ -z "$cluster" ]; then
            echo '[INFO] Creando el clúster local de PostgreSQL 18...'
            sudo pg_createcluster 18 main --start
        else
            echo "[INFO] Encendiendo el clúster PostgreSQL 18/$cluster..."
            sudo pg_ctlcluster 18 "$cluster" start
        fi
        puerto="$(pg_lsclusters -h | awk '$1=="18" && $4=="online" {print $3; exit}')"
    fi
    if [ -z "$puerto" ]; then
        echo 'ERROR: PostgreSQL 18 no quedo activo. Revisar: pg_lsclusters' >&2
        exit 1
    fi
    export AUTOAUDIT_PGPORT="$puerto"
    echo "[OK] PostgreSQL 18 disponible en el puerto $puerto."
}

preparar_python() {
    if ! python3 -m venv .venv 2>/dev/null; then
        echo '[INFO] Instalando python3-venv / python3-pip...'
        sudo apt-get update
        sudo apt-get install -y python3-venv python3-pip
        python3 -m venv --clear .venv
    fi
    if ! .venv/bin/python -m pip --version >/dev/null 2>&1; then
        python3 -m venv --clear .venv || {
            sudo apt-get install -y python3-venv python3-pip
            python3 -m venv --clear .venv
        }
    fi
    if ! .venv/bin/python -c 'import flask, psycopg, dotenv' >/dev/null 2>&1; then
        echo '[INFO] Instalando dependencias de la interfaz web...'
        .venv/bin/python -m pip install -r requirements.txt
    fi
}

instalar_python_si_falta
instalar_postgresql18_si_falta
preparar_cluster18
if [ ! -x .venv/bin/python ] || [ ! -f .venv/bin/activate ]; then
    preparar_python
elif ! .venv/bin/python -c 'import flask, psycopg, dotenv' >/dev/null 2>&1; then
    preparar_python
fi
exec .venv/bin/python scripts/arrancar.py
