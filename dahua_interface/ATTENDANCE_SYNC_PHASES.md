# Fases de Integracion Biometrica con Asistencias Odoo

Fecha de referencia: **19 de marzo de 2026 (UTC)**.

## Fase 1. Entrega rapida

Objetivo:

- reflejar biometria en Odoo de forma continua
- crear `hr.attendance` con logica provisional
- dejar trazabilidad completa de cada evento sincronizado

Entregables:

- servicio `attendance_sync_worker`
- modulo Odoo `hr_biometric_attendance_sync`
- staging `hr.biometric.event`
- corridas `hr.biometric.sync.run`
- configuracion `hr.biometric.sync.config`
- cursor `hr.biometric.sync.cursor`
- cierre diario automatico
- reconciliacion tardia sin reapertura automatica

Gate de salida:

- eventos nuevos entran a Odoo en menos de 1 minuto
- `hr.attendance` se crea/actualiza por alternancia simple
- duplicados dentro de 90 segundos no alteran asistencias
- las asistencias abiertas se autocierra al final del dia

Riesgos conocidos:

- no existe inferencia real de comida o salida final
- un evento valido puede producir una asistencia funcionalmente incorrecta
- el calendario actual de Odoo sigue siendo demasiado generico para reglas finas

## Fase 2. Motor de inferencia

Objetivo:

- inferir entrada, comida, regreso y salida final
- usar reglas por jornada, sucursal y dispositivo

Entregables esperados:

- perfiles de jornada
- reglas de clasificacion por ventanas
- manejo de numero impar de marcas
- tratamiento de eventos tardios con recalc limitada

Gate de salida:

- las asistencias dejan de depender solo de alternancia simple
- se reduce el ruido operativo en jornadas incompletas

## Fase 3. Operacion madura

Objetivo:

- estabilizar la operacion
- introducir revision manual, excepciones y recalc controlado

Entregables esperados:

- reglas por sede y casos especiales
- dashboard de calidad del sync
- recalc retroactivo controlado
- criterios de prioridad entre ajuste manual y biometria

Gate de salida:

- flujo operativo estable
- menor cantidad de excepciones
- trazabilidad completa para auditoria y soporte
