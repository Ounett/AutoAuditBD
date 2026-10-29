# AutoAudit | Gestión y auditoría de PostgreSQL

Aplicación local para administrar registros y auditar los cambios que ocurren en PostgreSQL 18. El proyecto usa Flask (Python), HTML/CSS/JavaScript sin frameworks de frontend y triggers `AFTER` en PL/pgSQL. La base se denomina `autoaudit_visual` y no modifica la antigua base `autoaudit_db`.

## Inicio en VS Code — Linux, Windows y macOS

1. Extraer el ZIP y abrir la carpeta **AutoAudit_Visual_Pro_Gestion** en Visual Studio Code.
2. Abrir **Terminal → Nueva terminal**.
3. Ejecutar el iniciador según el sistema:

   - **Linux:** `./iniciar.sh`
   - **Windows:** doble clic en `iniciar.bat` o ejecutar `.\iniciar.bat` en PowerShell.
   - **macOS:** ejecutar `python3 -m venv .venv`, instalar `requirements.txt` y después `python3 scripts/arrancar.py`.

En Linux, el primer arranque puede instalar automáticamente PostgreSQL 18, Python y sus bibliotecas. En Windows y macOS se debe instalar PostgreSQL 18 y Python 3.11 o posterior previamente; el iniciador prepara el entorno virtual y las bibliotecas de Python. El programa prepara la base y abre **http://127.0.0.1:5050** automáticamente.

### Windows

La guía paso a paso, incluyendo cómo instalar PostgreSQL, iniciar su servicio desde `services.msc` o PowerShell, comprobar `psql` y resolver errores frecuentes, está en [Docs/01_INSTALACION.md](Docs/01_INSTALACION.md).

Resumen rápido:

1. Instalar Python 3.11+ y PostgreSQL 18.
2. Iniciar el servicio `postgresql-x64-18`.
3. Confirmar que `psql --version` funciona.
4. Clonar este repositorio y abrir su carpeta.
5. Ejecutar `.\iniciar.bat`.

El iniciador solicitará la contraseña del usuario `postgres` únicamente durante la instalación inicial o una migración pendiente; no guarda esa contraseña.

**Primer inicio de sesión:** revisar la terminal de VS Code. Allí aparecerá un usuario `admin` y una **contraseña temporal aleatoria**, solo al crear por primera vez el sistema de cuentas. La contraseña no se escribe en el código ni se almacena en texto plano. Debe cambiarse desde el botón **Contraseña** de la esquina superior derecha.

**Siguientes arranques:** ejecutar únicamente el iniciador correspondiente (`./iniciar.sh` o `iniciar.bat`) y acceder con los usuarios de la aplicación. No es necesario volver a ingresar contraseñas de PostgreSQL. Para cerrar el servidor, usar `Ctrl+C` en la terminal.

### Si ya se instaló AutoAudit Visual Pro anteriormente

La versión nueva detecta `.env` y la base `autoaudit_visual`. Aplica una migración **no destructiva** (`11_permisos_gestion.sql` y `12_contexto_usuarios.sql`) la primera vez para habilitar gestión visual y guardar el usuario de cada sesión. No elimina tablas ni bitácoras anteriores. Si se necesitan permisos administrativos para esa migración, el instalador puede solicitar `sudo` o, cuando `peer` no esté habilitado, la contraseña del administrador PostgreSQL **solo esa primera vez**. **No se deben copiar `.env`, `.venv` ni `.local` de una computadora a otra.**

### Si se olvida la contraseña de `admin`

Desde la carpeta del proyecto, con acceso a la cuenta Linux propietaria de la instalación:

```bash
# Linux/macOS:
.venv/bin/python scripts/restablecer_admin.py
# Windows:
.venv\Scripts\python.exe scripts\restablecer_admin.py
```

La nueva contraseña temporal se muestra únicamente en esa terminal. No se modifica PostgreSQL.

## Funciones

| Sección | Administrador | Usuario |
|---|---|---|
| Panel y estadísticas | Sí | Sí |
| Ver tablas y registros | Sí | Sí |
| Crear, editar y eliminar filas (INSERT, UPDATE, DELETE) | Sí | Sí, en tablas permitidas |
| Crear tablas nuevas (`gestion`) | Sí | No |
| Agregar columnas y eliminar tablas `gestion` | Sí | No |
| Configurar triggers y auditorías | Sí | Solo consultar |
| Consultar y exportar historial CSV | Sí | Sí |
| Crear y desactivar cuentas | Sí | No |
| Cambiar contraseña propia | Sí | Sí |

**Alcance de la edición de tablas:** la aplicación permite gestionar filas en tablas donde el rol técnico tiene permisos y cuyo esquema es `demo`, `gestion` o `public`. Las tablas creadas desde el panel van al esquema `gestion`. **Solo esas tablas `gestion` se pueden eliminar desde la interfaz** y se requiere confirmación exacta. Las tablas `demo` se conservan para la práctica; los esquemas de auditoría y de sistema no pueden eliminarse desde la web. La eliminación física de una tabla no borra el historial ya registrado.

**Nota sobre la auditoría:** se registran únicamente las columnas y operaciones habilitadas. El usuario de la sesión web se transmite a PostgreSQL dentro de la transacción y se guarda en la bitácora para cambios hechos desde la aplicación. Operaciones externas desde DBeaver o `psql` conservan como autor el rol de base de datos. La IP de las operaciones web locales será `127.0.0.1`.

## Prueba funcional recomendada

1. Abrir `Datos y tablas → demo.productos`.
2. Crear un producto de ejemplo (INSERT).
3. Editar su precio (UPDATE).
4. Eliminar ese producto (DELETE).
5. Abrir `Historial`: comprobar usuario, operación, columna, valor anterior y nuevo.
6. En `Usuarios` crear una cuenta de rol `usuario`, iniciar sesión con ella y repetir una modificación.
7. El administrador puede crear una tabla de prueba desde `Crear tabla`, con auditoría activa.
8. Realizar capturas propias de estos resultados y adjuntarlas al informe.

## Estructura

- `app.py` — API Flask de auditoría, consultas y exportación.
- `gestor_routes.py` — login, roles, validación de tablas y operaciones CRUD.
- `auth_local.py` — cuentas y contraseñas hash almacenadas localmente (SQLite protegido).
- `Interfaz/static/` — interfaz visual responsive de colores neutros.
- `Sql/01..12` — modelo, diccionario de datos, generador, consultas, seguridad y migraciones.
- `scripts/arrancar.py` — instalador lógico y ejecución multiplataforma de la interfaz.
- `scripts/restablecer_admin.py` — recuperación local de contraseña.
- `tests/` — comprobaciones automatizadas y prueba opcional de integración.

Las credenciales técnicas de PostgreSQL se guardan en `.env` con permisos de usuario; las cuentas web y la clave de sesión se guardan en `.local/` y no deben subirse a GitHub. El servidor se limita a `127.0.0.1`; **no se debe exponer tal cual a Internet** ni utilizar con datos sensibles reales sin una revisión de seguridad adicional.

## Verificaciones

```bash
.venv/bin/python -m pytest tests -v
AUTOAUDIT_INTEGRATION=1 .venv/bin/python -m pytest tests -v
```

La sintaxis y las pruebas locales no garantizan por sí mismas el funcionamiento con PostgreSQL 18; deben ejecutarse las pruebas de extremo a extremo en Ubuntu. La guía del curso solicita Ubuntu **26.04 LTS**; Linux Mint 22.3 y Ubuntu 24.04 sirven para desarrollo, pero no sustituyen ese requisito de entrega.
