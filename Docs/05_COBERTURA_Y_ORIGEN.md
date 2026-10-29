# Cobertura de la guía oficial y alcance de esta versión

La guía original de AutoAudit exige módulos de configuración, generación dinámica, bitácora, consultas/reporte, MER completo, seguridad, pruebas y documentación. La arquitectura de esta versión incluye los cuatro módulos y las siete entidades principales requeridas.

| Criterio | Implementación | Comprobación pendiente |
|---|---|---|
| Tablas y columnas desde diccionario | v_diccionario, /api/catalogo | Captura del explorador |
| Selección INSERT/UPDATE/DELETE | configurar_tabla, modal de interfaz | Crear configuración diferente |
| Generación AFTER por tabla | desplegar_trigger | Consultar pg_trigger |
| Valores antes y después | capturar_cambio, JSONB | Prueba 07 y detalle de fila |
| Usuario/fecha/IP | bitacora, usuario_auditado, estacion_trabajo | Captura de historial |
| Historial filtrado | /api/historial | Captura de filtros |
| Exportación estándar | /api/exportar.csv | Archivo CSV |
| Acceso administrativo | funciones y roles | Prueba de permisos |
| Integridad referencial | 5 FK + UNIQUE | Pruebas de integridad |
| Rendimiento | Sql/08_rendimiento.sql | Medición en VM |
| Ubuntu 26.04 LTS / PostgreSQL 18 | Compatible en diseño | Ejecutar en entorno exacto |

## Procedencia y diferencias

La fuente pública proporcionada fue `https://github.com/balvaradod/AutoAudit/blob/main/Sql/01_estructura.sql`. Se pudo observar su esquema de siete entidades bajo `auditoria`, sus roles y su estructura de carpetas (`Docs`, `Interfaz`, `Sql`). No se tuvo acceso completo al contenido de todos los archivos del repositorio: por ello, **la implementación incluida es una versión nueva autocontenida basada en ese modelo**, no una modificación verificada íntegramente del código original. No se publicaron commits.

En comparación con la estructura observada, se añadieron columnas JSONB de instantáneas completas, fecha con zona, claves primarias compuestas, control de roles mediante funciones, páginas web y scripts de prueba. Si se quisiera hacer una migración desde una base ya existente, habría que desarrollar un plan de conversión y respaldo específico: **esta distribución utiliza `autoaudit_visual` y aplica migraciones no destructivas a una instalación previa compatible**.

## Estado de validación al empaquetar

- Verificación de compilación Python: sí.
- Verificación sintáctica de JavaScript: sí.
- Verificación estática de rutas, autenticación, CRUD y estructura: sí.
- Nuevos módulos web de gestión: implementados; pendientes de integración real.
- Pruebas reales de integración con PostgreSQL 18: no se pudieron ejecutar aquí.
- Capturas reales y resultados de rendimiento: pendientes de la VM.

Ningún resultado pendiente debe presentarse como aprobado antes de verificarse.
