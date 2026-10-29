#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
: "${PGUSER:=postgres}"
: "${PGHOST:=127.0.0.1}"
: "${PGPORT:=5432}"
: "${PGDATABASE:=autoaudit_visual}"
export PGUSER PGHOST PGPORT PGDATABASE
printf 'Instalando AutoAudit en %s como %s (%s:%s)\n' "$PGDATABASE" "$PGUSER" "$PGHOST" "$PGPORT"
for sql in Sql/{01_estructura,02_diccionario,03_configuracion,04_generador_triggers,05_consultas,06_datos_prueba,10_seguridad,11_permisos_gestion,12_contexto_usuarios}.sql; do
    printf '\n==> %s\n' "$sql"
    psql -X -v ON_ERROR_STOP=1 -f "$sql"
done
printf '\nSQL instalado. Para preparar cuentas e iniciar la interfaz se recomienda ./iniciar.sh\n'
