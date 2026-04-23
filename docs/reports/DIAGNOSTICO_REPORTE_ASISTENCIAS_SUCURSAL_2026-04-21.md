# Diagnostico del Reporte Asistencias por Sucursal - Intermitencias

Fecha del diagnostico: `2026-04-21`

## Objetivo

Evaluar la viabilidad de agregar al reporte **Asistencias por Sucursal** las
horas de comida o, de forma mas precisa, las **intermitencias** entre tramos de
asistencia del mismo empleado en la misma fecha local.

Las preguntas de negocio a responder fueron:

1. si estas intermitencias realmente se estan dando
2. si existe mas de una intermitencia en el mismo dia
3. cual es el mejor criterio para detectarlas
4. como representarlas en el reporte sin romper el layout actual

## Resumen ejecutivo

- El reporte actual **si tiene materia prima** para derivar intermitencias,
  porque el sync biometrico crea multiples `hr.attendance` cuando hay alternancia
  de marcas.
- El modulo actual **no modela intermitencias**. Agrupa todo a **una fila por
  empleado + fecha local** y solo conserva `Hora Entrada`, `Hora Salida` y
  `Tiempo efectivo`.
- En produccion **si hay intermitencias reales**.
  Del `2026-04-01` al `2026-04-20` hubo `64` dias-empleado con `2` tramos sobre
  `322` dias-empleado biometrico (`19.88%`).
- Si se amplia el corte a todo el periodo de Fase 1
  (`2026-03-20` a `2026-04-20`), aparecen `136` dias-empleado con mas de un
  tramo sobre `475` dias-empleado (`28.63%`), incluyendo `2` dias con `3`
  tramos. Es decir: **mas de una intermitencia ya existe**, aunque es rara.
- El sync actual es **raw toggle** y la propia especificacion dice
  "no inferir almuerzo ni descanso". Por eso, llamar "hora de comida" a todo
  gap es arriesgado sin una regla de negocio adicional.
- El mejor criterio operativo es tratar estas ventanas como
  **intermitencias** y calcularlas sobre **dias cerrados/finalizados**. Para
  consulta intradia, el dato deberia marcarse como **provisional**.

## Alcance revisado

Revision funcional y tecnica sobre:

- `odoo_biometric/module/devlyn_dahua_attendance_reporting/services/report_export.py`
- `odoo_biometric/module/devlyn_dahua_attendance_reporting/views/devlyn_attendance_branch_report_views.xml`
- `dahua_interface/attendance_sync_worker.py`
- `dahua_interface/ATTENDANCE_SYNC_PHASE1_SPEC.md`
- consultas `read-only` a `devlyn_com` realizadas el `2026-04-21`

## Como funciona hoy

### 1. El reporte por sucursal

El servicio del reporte:

- filtra `hr.attendance` con `biometric_source = biometric_v1`
- usa `check_in` como base del rango
- agrupa por `(employee_id, fecha_local_de_check_in)`
- consolida una sola fila por dia

Referencias:

- `HEADERS` solo expone `Hora Entrada`, `Hora Salida` y `Tiempo efectivo` en
  [report_export.py](../../odoo_biometric/module/devlyn_dahua_attendance_reporting/services/report_export.py)
- la consolidacion por empleado/fecha local vive en
  [report_export.py](../../odoo_biometric/module/devlyn_dahua_attendance_reporting/services/report_export.py)

En concreto:

- `Hora Entrada` = primer `check_in` local del dia
- `Hora Salida` = ultimo `check_out` local cerrado del dia
- `Tiempo efectivo` = suma de `worked_hours` de todos los `hr.attendance`
  agrupados

Esto significa que el reporte actual **pierde el detalle de los tramos
intermedios**.

### 2. El sync biometrico

El sync actual trabaja por alternancia simple:

- si no hay asistencia abierta, crea `check_in`
- si hay asistencia abierta, escribe `check_out`
- deduplica por `90` segundos
- autocierra al fin del dia a `23:59:59`
- si llega un evento tarde despues del cierre, lo manda a `after_close_review`

Referencias:

- especificacion de Fase 1:
  [ATTENDANCE_SYNC_PHASE1_SPEC.md](../../dahua_interface/ATTENDANCE_SYNC_PHASE1_SPEC.md)
- implementacion:
  [attendance_sync_worker.py](../../dahua_interface/attendance_sync_worker.py)

Implicacion directa:

- con marcas `entrada -> salida -> regreso -> salida`, el sistema genera
  `2` registros `hr.attendance`
- con mas alternancias, puede generar `3`, `4` o mas tramos el mismo dia
- hoy no existe clasificacion oficial que distinga "comida" de cualquier otra
  salida intermedia

## Evidencia productiva

Las metricas siguientes se obtuvieron con consultas `read-only` sobre
`hr_attendance` y `hr_biometric_event`, usando timezone operativa
`America/Mexico_City`.

### Ventana A: `2026-04-01` a `2026-04-20`

- `322` dias-empleado biometricos
- `258` dias-empleado con `1` tramo
- `64` dias-empleado con `2` tramos
- `0` dias-empleado con `3` o mas tramos
- `64` gaps detectables entre tramos
- promedio del gap: `103.10` minutos
- mediana del gap: `64.22` minutos
- percentil 90 del gap: `254.74` minutos
- `0` dias multi-tramo con cambio de centro/sucursal dentro del mismo dia
- `18` de los `64` dias multi-tramo tienen al menos un tramo auto-cerrado

Distribucion de gaps en esta ventana:

- `< 30 min`: `0`
- `30 - 60 min`: `16`
- `60 - 90 min`: `34`
- `90 - 180 min`: `4`
- `>= 180 min`: `10`

Lectura operativa:

- si nos limitamos a abril cerrado, la intermitencia existe y es frecuente
  (`19.88%` de los dias-empleado)
- dentro de ese corte, aun no aparece mas de una intermitencia por dia

### Ventana B: `2026-03-20` a `2026-04-20` (todo Fase 1 cerrado)

- `475` dias-empleado biometricos
- `136` dias-empleado con mas de un tramo (`28.63%`)
- `134` dias-empleado con `2` tramos
- `2` dias-empleado con `3` tramos
- maximo historico observado: `3` tramos en un dia

Distribucion historica de gaps:

- `< 15 min`: `4`
- `15 - 30 min`: `4`
- `30 - 60 min`: `36`
- `60 - 90 min`: `54`
- `90 - 180 min`: `11`
- `>= 180 min`: `29`

Hallazgo importante:

- ya existen gaps muy cortos, por ejemplo de `3.47` minutos
- eso confirma que **no todo gap debe etiquetarse automaticamente como
  comida**

### Casos reales con mas de una intermitencia

Empleado `24367` - `JIMENEZ CRUZ DIEGO ARMANDO`

`2026-03-26`

- tramo 1: `12:00:51 - 18:44:00`
- intermitencia 1: `18:44:00 - 19:14:37` (`30.62 min`)
- tramo 2: `19:14:37 - 20:16:34`
- intermitencia 2: `20:16:34 - 21:37:17` (`80.72 min`)
- tramo 3: `21:37:17 - 23:59:59` (`auto_close`)

`2026-03-27`

- tramo 1: `10:59:52 - 17:01:24`
- intermitencia 1: `17:01:24 - 17:15:43` (`14.32 min`)
- tramo 2: `17:15:43 - 21:04:05`
- intermitencia 2: `21:04:05 - 21:07:33` (`3.47 min`)
- tramo 3: `21:07:33 - 23:59:59` (`auto_close`)

Estos dos dias bastan para concluir que:

- la representacion no debe asumir "solo una comida"
- la representacion tampoco debe asumir que toda intermitencia es larga

### Ventana C: dia actual `2026-04-21`

Al momento del diagnostico:

- `21` dias-empleado ya visibles en el corte del dia
- los `21` siguen abiertos
- `2` ya traen `2` tramos, pero el segundo sigue abierto

Casos reales:

Empleado `6217` - `PEREZ PEREZ LUIS`

- tramo 1: `11:21:38 - 17:09:29` (`worked_hours = 5.7975`)
- gap actual: `17:09:29 - 18:06:44` (`57.25 min`)
- tramo 2: `18:06:44 - OPEN`

Empleado `40739` - `RIVAS VILLADA XIMENA ARIADNA`

- tramo 1: `10:24:43 - 17:05:18` (`worked_hours = 6.676388888888889`)
- gap actual: `17:05:18 - 18:10:25` (`65.12 min`)
- tramo 2: `18:10:25 - OPEN`

Esto expone una limitacion del reporte actual:

- como el segundo tramo esta abierto, el consolidado del dia toma la ultima
  salida cerrada (`17:09:29` / `17:05:18`)
- el tramo abierto aporta `worked_hours = 0`
- por tanto, el reporte intradia puede mostrar una fila parcialmente correcta,
  pero **inestable y engañosa** para este caso

## Respuesta a las 4 preguntas

### 1. Si estas intermitencias se estan dando

Si.

Conclusion operativa:

- abril cerrado (`2026-04-01` a `2026-04-20`): `64 / 322` dias-empleado con
  intermitencia (`19.88%`)
- historico Fase 1 (`2026-03-20` a `2026-04-20`): `136 / 475` dias-empleado con
  intermitencia (`28.63%`)

### 2. Hay mas de una intermitencia

Si, aunque es poco frecuente en lo observado hasta hoy.

Conclusion operativa:

- en abril cerrado no hubo dias con mas de una intermitencia
- en el historico de Fase 1 si hubo `2` dias con `3` tramos
- por lo tanto el diseno **debe soportar N intermitencias**, no solo una

### 3. Cual seria el mejor criterio para detectarla

Recomendacion:

- calcular intermitencias sobre **dias finalizados**
- no venderlas como "comida" mientras no exista una regla de negocio que
  clasifique el gap

Criterio tecnico recomendado para un dia finalizado:

- fecha local menor al dia local actual, y
- sin `hr.attendance` abierto para ese empleado/fecha, o
- proceso de cierre diario ya ejecutado para esa fecha

Si se quiere un criterio estricto de auditoria:

- agregar una bandera que indique si existen eventos `after_close_review` para
  ese empleado/fecha, porque esos eventos tardios no se reaplican en automatico

Motivos para no depender solo del intradia:

- el dia actual puede seguir abriendo y cerrando tramos
- el modulo actual oculta parcialmente el ultimo tramo abierto
- el autocierre a `23:59:59` estabiliza el dataset, pero puede introducir un
  `check_out` sintetico

Resumen de criterio:

- **historico / export oficial**: usar solo dias finalizados
- **visor intradia**: si se muestra, marcarlo como `provisional`

### 4. Como representar mas de una intermitencia

Recomendacion principal:

- mantener **una fila por empleado + fecha**
- agregar columnas resumen
- agregar un campo de detalle serializado para no depender de un numero fijo

Propuesta de layout minimo:

- `Cantidad intermitencias`
- `Tiempo intermitente total`
- `Detalle intermitencias`
- `Estado del dia` (`provisional`, `cerrado`, `cerrado_con_auto_close`)

Formato sugerido para `Detalle intermitencias`:

```text
18:44:00-19:14:37 (00:31) | 20:16:34-21:37:17 (01:21)
```

Si negocio insiste en columnas planas para Excel:

- `Intermitencia 1 inicio`
- `Intermitencia 1 fin`
- `Intermitencia 1 tiempo`
- `Intermitencia 2 inicio`
- `Intermitencia 2 fin`
- `Intermitencia 2 tiempo`
- `Intermitencias adicionales`

Pero esto deberia ser la opcion secundaria, porque:

- ya hay casos reales con mas de una intermitencia
- mas adelante podria existir un tercer gap
- el sync actual no garantiza que esas ventanas correspondan exactamente a
  "comida"

## Riesgos y consideraciones funcionales

### 1. "Tiempo efectivo" ya tiene valor y no debe reemplazarse

`Tiempo efectivo` ya suma `worked_hours` de todos los tramos del dia. Es decir:

- **ya excluye** las intermitencias
- lo que hoy falta no es el neto, sino el detalle del tiempo intermedio

### 2. "Hora Salida" puede ser sintetica por autocierre

Historico abril `2026-04-01` a `2026-04-20`:

- `105` asistencias fueron auto-cerradas
- `18` dias multi-tramo tienen al menos un `auto_close`

Implicacion:

- el ultimo `check_out` del dia no siempre representa una marca humana real

### 3. "Comida" no es sinonimo de "gap"

Los gaps cortos observados (`3.47 min`, `14.32 min`) muestran que:

- hay salidas/reingresos operativos o ruido funcional que no deben etiquetarse
  automaticamente como comida

## Implicaciones tecnicas para el modulo

Para soportar intermitencias correctamente, el modulo tendria que:

1. dejar de perder el orden de tramos al consolidar el dia
2. derivar gaps a partir de la secuencia ordenada de `hr.attendance`
3. exponer resumen y detalle en el `viewer`
4. exportar ese mismo detalle al XLSX
5. marcar si la fila del dia es provisional o final

Archivos a tocar en una implementacion futura:

- `services/report_export.py`
- `models/devlyn_attendance_branch_report_viewer.py`
- `views/devlyn_attendance_branch_report_views.xml`
- `tests/` del addon

## Recomendacion final

La ampliacion es **viable**, pero el nombre correcto del primer entregable
deberia ser **intermitencias** y no "horas de comida".

La ruta mas segura es:

1. detectar y guardar todas las intermitencias del dia
2. exponer `cantidad`, `total` y `detalle`
3. marcar filas intradia como `provisionales`
4. dejar la clasificacion "esto si cuenta como comida" para una regla posterior
   de negocio o Fase 2 de inferencia

Con el comportamiento actual del sistema, ese enfoque es el que mejor respeta
la realidad del dato y evita falsas interpretaciones.
