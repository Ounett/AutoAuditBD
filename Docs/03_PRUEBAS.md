# Validación y capturas — AutoAudit

La evidencia debe obtenerse ejecutando la aplicación en PostgreSQL 18. Este documento enumera los pasos; no presenta resultados todavía no comprobados.

| ID | Prueba | Captura sugerida |
|---|---|---|
| F01 | Abrir `./iniciar.sh` en Linux o `iniciar.bat` en Windows y entrar con la cuenta admin de la web | Login y panel |
| F02 | En Datos y tablas abrir `demo.productos` | Tabla con filas |
| F03 | Usar **Nuevo registro** y registrar un producto nuevo | Formulario y fila creada |
| F04 | Cambiar el precio mediante **Editar** | Fila modificada |
| F05 | Eliminar ese producto y confirmar | Resultado DELETE |
| F06 | En Historial filtrar por tabla `productos` | INSERT/UPDATE/DELETE, valores anteriores y nuevos |
| F07 | Crear una cuenta rol usuario, cerrar sesión y entrar con ella | Usuarios y sesión diferente |
| F08 | Cambiar un registro con el usuario nuevo y verificar autor del evento | Bitácora con nombre del usuario de la web |
| F09 | Admin crea una tabla nueva en `gestion`; insertar fila | Tabla nueva auditada |
| F10 | Admin desactiva/activa una regla y comprueba cambios | Estado de trigger e historial |
| F11 | Exportar CSV desde Historial | CSV en LibreOffice Calc |
| S01 | Intentar escribir directamente en `auditoria.bitacora` como rol no propietario | Error de permisos |
| P01 | Ejecutar `Sql/08_rendimiento.sql` desde PostgreSQL 18 | Tiempos medidos |

**Validación desde SQL (opcional):** desde terminal en la carpeta del proyecto, con PostgreSQL correctamente autenticado:

```bash
psql -h 127.0.0.1 -U postgres -W -d autoaudit_visual -v ON_ERROR_STOP=1 -f Sql/07_pruebas.sql
```

Para comprobar los triggers:

```sql
SELECT tgname, tgrelid::regclass AS tabla, tgenabled
FROM pg_trigger WHERE tgname LIKE 'trg_autoaudit_%';
```

**Nota:** si se ejecutan operaciones desde psql/DBeaver, el historial registra el rol de PostgreSQL; desde la web registra el nombre del usuario que inició sesión. Las pruebas de rendimiento y seguridad deben anotarse con resultados reales, sin inventar capturas ni mediciones.
