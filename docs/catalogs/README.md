# Catálogos Fuente del Reporte

Esta carpeta contiene los archivos fuente entregados por el negocio para construir el reporte **Asistencias por Sucursal**.

## Archivos

- `Catalogos.xlsx`
  Fuente de catálogos base para:
  - sucursales
  - regiones
  - zonas
  - distritos
  - formato
  - estatus
  - nivel óptica ventas
- `Layout_reporte.xlsx`
  Layout de referencia solicitado para el reporte.

## Uso dentro del proyecto

Estos archivos **no** se consumen directamente en runtime de Odoo.

El flujo actual es:

1. revisar y validar el Excel fuente
2. normalizarlo a seeds versionados dentro del addon
3. cargar esos seeds a tablas vivas en Odoo

Addon relacionado:

- `odoo_biometric/module/devlyn_dahua_attendance_reporting/`
