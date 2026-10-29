# Manual de instalación — AutoAudit (gestión y auditoría)

## Requisitos

El servidor se ejecuta en Ubuntu/Linux Mint local, con autorización sudo para instalar paquetes durante la primera ejecución. PostgreSQL 18 es el motor requerido; el iniciador puede instalarlo automáticamente. VS Code solo sirve para abrir el proyecto y ejecutar la terminal integrada.

## Procedimiento completo

1. Descargar y extraer el ZIP completo.
2. Abrir la carpeta `AutoAudit_Visual_Pro_Gestion` desde Visual Studio Code.
3. Abrir Terminal → Nueva terminal.
4. Ejecutar `./iniciar.sh`.
5. Esperar a que se instalen los paquetes y las funciones PostgreSQL. Cuando corresponda, proporcionar la contraseña sudo de la cuenta Linux (no es una contraseña guardada por AutoAudit).
6. Revisar en la terminal el usuario **admin** y la contraseña temporal generada para la web. La contraseña solo se muestra en el primer inicio.
7. Abrir `http://127.0.0.1:5050` si el navegador no se abre automáticamente.
8. Iniciar sesión como `admin` y cambiar la contraseña desde el botón **Contraseña**.

El instalador guarda una cuenta técnica de PostgreSQL en `.env` con permisos de archivo restringidos y las cuentas web con contraseñas hash en `.local/usuarios.sqlite3`. Ambos archivos deben permanecer fuera del repositorio. Se crea `autoaudit_visual` sin tocar `autoaudit_db`.

**Arranque posterior:** `./iniciar.sh`. **Apagado:** `Ctrl+C` en la terminal. **Recuperación de la cuenta admin:** `.venv/bin/python scripts/restablecer_admin.py`.

## Instalación existente

Si ya existe una instalación anterior de `autoaudit_visual`, el iniciador conserva las tablas y aplica los scripts de migración de permisos/contexto de usuarios una sola vez, con autorización administrativa cuando haga falta. No conviene borrar la base de datos ni ejecutar `DROP DATABASE` para actualizar la interfaz.

## Seguridad

El servidor web escucha exclusivamente en localhost (127.0.0.1). Los roles admin/usuario son roles de aplicación y no equivalen a cuentas de PostgreSQL. La bitácora conserva la historia de operaciones auditadas; no debe modificarse manualmente. No se debe exponer la instancia a Internet.
