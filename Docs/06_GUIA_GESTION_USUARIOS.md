# Manual de la interfaz: administración de datos y cuentas

## Inicio de la aplicación

La aplicación se ejecuta desde VS Code con `./iniciar.sh`, abriendo `http://127.0.0.1:5050`. El primer acceso utiliza la cuenta administradora y la clave temporal impresa por el iniciador. La clave debe cambiarse desde **Contraseña**. No se utiliza la contraseña PostgreSQL para ingresar a la web.

## Crear y modificar registros

La sección **Datos y tablas** muestra en el panel lateral las tablas accesibles. Al seleccionar `demo.productos`, el sistema consulta sus columnas y primeros 30 registros. Para agregar un producto se pulsa **Nuevo registro** y se llenan los campos requeridos; el ID identidad se genera automáticamente. Para cambiar un precio se utiliza **Editar** en la fila. **Eliminar** solicita confirmación antes de borrar la fila. Los cambios de las columnas auditadas quedan en **Historial**; un cambio de una columna no auditada no aparece en la bitácora por diseño.

## Crear y eliminar tablas

Solo un administrador puede seleccionar **Crear tabla**. Los nombres admiten letras minúsculas, números y guion bajo; las columnas ofrecen tipos `TEXT`, `VARCHAR(120)`, `INTEGER`, `NUMERIC(12,2)`, `DATE` y `BOOLEAN`. El sistema crea la tabla en el esquema `gestion`, agrega clave primaria `id` y configura auditoría de las columnas nuevas para INSERT, UPDATE y DELETE. **Agregar columna** permite ampliar las tablas propias; su nueva columna puede habilitarse desde Auditorías. **Eliminar tabla** solo se permite en `gestion` con confirmación exacta. Los registros en bitácora permanecen después del borrado físico.

## Configuración de auditorías

La sección **Auditorías** permite al administrador elegir tablas, columnas y tipos de operación. Se generan triggers `AFTER` de PostgreSQL. La auditoría puede activarse o desactivarse por tabla o regla. Los usuarios normales solo pueden visualizar la configuración.

## Usuarios

Desde la sección **Usuarios**, el administrador crea cuentas con roles **admin** (configura auditoría, tablas y usuarios) o **usuario** (consulta y modifica filas permitidas). Un usuario no tiene acceso a la configuración, creación o eliminación de tablas ni a otras cuentas. Las contraseñas se guardan como hash, y la sesión requiere protección CSRF para modificaciones.

## Historial y exportación

La bitácora permite filtrar por usuario, tabla, columna y operación. El botón **Detalle** muestra la fila anterior y nueva; **Exportar CSV** genera un archivo que puede abrirse con LibreOffice Calc. El usuario web se registra para operaciones ejecutadas desde la aplicación. La auditoría retiene el historial incluso cuando desaparece la fila o una tabla de `gestion`.

## Capturas para entrega

1. Inicio de sesión y panel de estadísticas.
2. Lista de tablas y registros.
3. Formulario de alta y resultado de INSERT.
4. Edición de precio y resultado de UPDATE.
5. Eliminación confirmada y resultado de DELETE.
6. Bitácora filtrada con usuario, valores anterior/nuevo.
7. Usuarios con roles distintos.
8. Configuración de triggers y descarga CSV.

Las imágenes deben ser capturas de una instalación funcionando; el proyecto no incluye capturas ficticias como evidencias.
