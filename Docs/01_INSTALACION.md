# Manual de instalación — AutoAudit (gestión y auditoría)

## Requisitos

El servidor se ejecuta localmente en Linux, Windows o macOS. PostgreSQL 18 es el motor requerido. Linux puede instalarlo automáticamente con `sudo`; en Windows y macOS debe instalarse previamente. VS Code solo sirve para abrir el proyecto y ejecutar la terminal integrada.

## Instalación detallada en Windows

### 1. Instalar Python

Descarga Python 3.11 o posterior desde <https://www.python.org/downloads/windows/>. En el instalador activa **Add python.exe to PATH** antes de pulsar **Install Now**. Comprueba la instalación abriendo PowerShell:

```powershell
py --version
```

Debe aparecer Python 3.11 o una versión posterior.

### 2. Instalar PostgreSQL 18

Descarga el instalador de PostgreSQL 18 para Windows desde <https://www.postgresql.org/download/windows/>. Durante el asistente:

1. Conserva los componentes **PostgreSQL Server** y **Command Line Tools**.
2. Deja el puerto predeterminado `5432`, salvo que ya tengas otro PostgreSQL usando ese puerto.
3. Define una contraseña para el usuario administrador `postgres` y guárdala: AutoAudit la pedirá la primera vez para crear su base y su rol técnico.
4. Puedes dejar PostgreSQL ejecutándose como servicio de Windows con el nombre predeterminado `postgresql-x64-18`.

El instalador normalmente agrega `C:\Program Files\PostgreSQL\18\bin` al `PATH`. Si PowerShell no reconoce `psql`, agrégala manualmente desde **Configuración avanzada del sistema → Variables de entorno → Path**, y abre una terminal nueva.

Comprueba que el cliente esté disponible:

```powershell
psql --version
```

### 3. Iniciar y detener PostgreSQL

La forma visual es abrir `Win + R`, escribir `services.msc`, buscar **postgresql-x64-18**, hacer clic derecho y elegir **Iniciar**, **Detener** o **Reiniciar**. El estado debe ser **En ejecución** antes de iniciar AutoAudit.

También se puede administrar desde PowerShell **como administrador**:

```powershell
Get-Service postgresql-x64-18
Start-Service postgresql-x64-18
Restart-Service postgresql-x64-18
Stop-Service postgresql-x64-18
```

Si el nombre no existe, consulta los servicios instalados:

```powershell
Get-Service *postgres*
```

Usa el nombre que muestre el resultado. Para verificar que PostgreSQL responde:

```powershell
psql -h 127.0.0.1 -U postgres -d postgres -W
```

Escribe la contraseña configurada durante la instalación. Si aparece el prompt `postgres=#`, escribe `\q` para salir. Si aparece `connection refused`, el servicio está detenido, el puerto no coincide o el firewall está bloqueando la conexión local.

### 4. Descargar y preparar AutoAudit

En PowerShell:

```powershell
git clone https://github.com/Ounett/AutoAuditBD.git
cd AutoAuditBD
```

Si no tienes Git, descarga **Code → Download ZIP** desde GitHub, extrae el ZIP y abre esa carpeta en VS Code.

La primera ejecución crea el entorno virtual `.venv` e instala las bibliotecas de `requirements.txt`:

```powershell
.\iniciar.bat
```

También puedes hacer doble clic en `iniciar.bat`. Si Windows muestra una advertencia de seguridad, verifica que el archivo provenga del repositorio correcto y elige permitir su ejecución.

### 5. Primer arranque y siguientes arranques

En el primer arranque, el programa:

1. Comprueba PostgreSQL 18.
2. Crea la base `autoaudit_visual` si todavía no existe.
3. Ejecuta los scripts SQL del proyecto.
4. Crea el rol técnico de la aplicación con una contraseña aleatoria.
5. Guarda únicamente la configuración técnica en `.env`, que queda excluido de Git.
6. Crea la cuenta web `admin` y muestra una contraseña temporal en la terminal.
7. Abre `http://127.0.0.1:5050`.

La contraseña de `postgres` no se guarda. La contraseña temporal de `admin` debe cambiarse desde el botón **Contraseña**. En los siguientes arranques basta con:

```powershell
.\iniciar.bat
```

Para apagar AutoAudit, vuelve a la terminal y presiona `Ctrl+C`. Para apagar PostgreSQL, usa `Stop-Service postgresql-x64-18` o la consola de servicios; normalmente conviene dejarlo iniciado para el próximo uso.

### 6. Si algo falla en Windows

- **`psql no se reconoce`:** agrega `C:\Program Files\PostgreSQL\18\bin` al `PATH`, abre una terminal nueva y repite `psql --version`.
- **`connection refused` o no se pudo conectar:** inicia `postgresql-x64-18` y confirma que usa el puerto `5432`.
- **Contraseña de PostgreSQL incorrecta:** no es la contraseña de la web. Es la contraseña definida para `postgres` durante la instalación de PostgreSQL.
- **El puerto `5432` ya está ocupado:** identifica qué instalación está activa con `Get-Service *postgres*`; si PostgreSQL usa otro puerto, configura `AUTOAUDIT_PGPORT` antes de ejecutar el iniciador.
- **PowerShell bloquea scripts:** `iniciar.bat` no necesita política de ejecución de PowerShell; ejecútalo con `.\iniciar.bat` desde la carpeta del proyecto.
- **Se cerró la terminal y no sabes si sigue activo:** abre `http://127.0.0.1:5050`. Si no responde, ejecuta de nuevo `.\iniciar.bat`.

No copies `.env`, `.venv` ni `.local` desde otra computadora. Cada instalación debe crear sus propias credenciales y cuentas locales.

## Procedimiento completo

1. Descargar y extraer el ZIP completo.
2. Abrir la carpeta `AutoAudit_Visual_Pro_Gestion` desde Visual Studio Code.
3. Abrir Terminal → Nueva terminal.
4. Ejecutar `./iniciar.sh` en Linux, o `iniciar.bat` en Windows.
5. Esperar a que se instalen los paquetes y las funciones PostgreSQL. En Linux puede solicitarse la contraseña sudo; en Windows se solicitará la contraseña del usuario `postgres` si la conexión local no permite acceso sin contraseña.
6. Revisar en la terminal el usuario **admin** y la contraseña temporal generada para la web. La contraseña solo se muestra en el primer inicio.
7. Abrir `http://127.0.0.1:5050` si el navegador no se abre automáticamente.
8. Iniciar sesión como `admin` y cambiar la contraseña desde el botón **Contraseña**.

El instalador guarda una cuenta técnica de PostgreSQL en `.env` con permisos de archivo restringidos y las cuentas web con contraseñas hash en `.local/usuarios.sqlite3`. Ambos archivos deben permanecer fuera del repositorio. Se crea `autoaudit_visual` sin tocar `autoaudit_db`.

**Arranque posterior:** `./iniciar.sh` o `iniciar.bat`. **Apagado:** `Ctrl+C` en la terminal. **Recuperación de la cuenta admin:** `.venv/bin/python scripts/restablecer_admin.py` en Linux/macOS o `.venv\Scripts\python.exe scripts\restablecer_admin.py` en Windows.

## Instalación existente

Si ya existe una instalación anterior de `autoaudit_visual`, el iniciador conserva las tablas y aplica los scripts de migración de permisos/contexto de usuarios una sola vez, con autorización administrativa cuando haga falta. No conviene borrar la base de datos ni ejecutar `DROP DATABASE` para actualizar la interfaz.

## Seguridad

El servidor web escucha exclusivamente en localhost (127.0.0.1). Los roles admin/usuario son roles de aplicación y no equivalen a cuentas de PostgreSQL. La bitácora conserva la historia de operaciones auditadas; no debe modificarse manualmente. No se debe exponer la instancia a Internet.
