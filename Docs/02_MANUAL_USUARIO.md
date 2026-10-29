# Manual de usuario — AutoAudit

La aplicación se abre desde VS Code con `./iniciar.sh` en Linux o `iniciar.bat` en Windows y se usa en `http://127.0.0.1:5050`. El primer administrador inicia sesión con la clave temporal mostrada una sola vez en la terminal. Después se cambia esa clave desde el botón **Contraseña**.

**Resumen:** estadísticas de configuración, auditorías y cambios registrados.

**Datos y tablas:** seleccionar una tabla, consultar filas paginadas (30 por página), crear una fila con **Nuevo registro**, cambiar datos con **Editar** o eliminar mediante **Eliminar** y confirmación. Los cambios de columnas/operaciones configuradas aparecen automáticamente en Historial. El sistema no audita columnas no habilitadas.

**Administración de tablas:** solo admin puede crear tablas en `gestion`, añadir columnas o eliminar esas tablas con confirmación por nombre completo. Las tablas `demo` y el esquema interno de auditoría no se eliminan desde el panel. El historial previo de una tabla eliminada se conserva.

**Auditorías:** administrador configura tabla, columnas y eventos INSERT/UPDATE/DELETE; genera o despliega triggers, y habilita/deshabilita reglas. El usuario normal puede consultar el estado de las configuraciones.

**Historial:** filtros por usuario, tabla, columna u operación. El detalle de una fila permite comparar instantáneas antiguas y nuevas. La exportación descarga CSV.

**Usuarios:** el admin crea cuentas de roles `admin` y `usuario`, y puede habilitar o deshabilitar las otras cuentas. El rol usuario puede editar registros permitidos, pero no configurar triggers, cambiar estructura de tablas ni administrar cuentas. Ambos roles pueden cambiar su contraseña propia.

Para la demostración se recomienda iniciar sesión como admin, crear un registro en `demo.productos`, cambiar `precio`, eliminarlo y consultar Historial. Repetir la operación con un usuario normal para mostrar trazabilidad por sesión.
