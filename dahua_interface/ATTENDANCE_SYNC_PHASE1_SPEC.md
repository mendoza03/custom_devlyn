# Especificacion de Fase 1: Attendance Sync V1

## Estado actual

Implementado y desplegado en la EC2 `52.6.240.186` el `20 de marzo de 2026` con:

- modulo Odoo `hr_biometric_attendance_sync`
- servicio `systemd` `attendance-sync-worker`
- usuario tecnico `biometric.sync`
- staging en `hr.biometric.event`
- escritura funcional en `hr.attendance`

## Objetivo

Subir de forma continua eventos biometrico a Odoo y crear `hr.attendance` con alternancia simple, sin inferencia avanzada.

## Fuente de datos

- base fuente: `biometric_ingest`
- tabla fuente: `normalized_event`
- filtro: `event_kind = 'access_control'`

## Criterios de entrada al sync

- `UserID` no vacio
- empleado encontrado por `hr_employee.employee_number`

Si el evento no cumple lo anterior:

- igual se registra en `hr.biometric.event`
- no crea ni modifica `hr.attendance`

## Reglas de Fase 1

- dedupe de 90 segundos por empleado
- si no existe asistencia abierta del empleado, crear `check_in`
- si existe asistencia abierta del empleado, escribir `check_out`
- si el evento llega tarde despues del cierre de su dia, registrar `after_close_review`
- no inferir almuerzo ni descanso

## Cierre diario

- timezone operativa: `America/Mexico_City`
- hora de cierre: `23:59`
- reconciliacion tardia: `00:15`

Politica:

- toda asistencia abierta con `biometric_source = biometric_v1` se cierra a `23:59:59` local del dia de su `check_in`
- se marca `biometric_auto_closed = True`
- se registra razon `auto_close_eod_v1`

## Trazabilidad obligatoria

Cada evento debe dejar:

- `normalized_event_id`
- `attendance_action`
- `sync_status`
- `attendance_id`
- `message`
- payload biometrico relevante

Politica de corridas:

- solo se registra `hr.biometric.sync.run` cuando el ciclo procesa eventos reales
- si no hay eventos pendientes, el poll no deja corrida en Odoo
- los jobs de cierre y reconciliacion si mantienen su propia corrida

## Casos que debe cubrir

- empleado valido con check-in nuevo
- empleado valido con check-out
- duplicado ignorado
- empleado no encontrado
- evento denegado
- evento tardio posterior al cierre
- autocierre nocturno
