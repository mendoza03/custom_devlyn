# Validacion Odoo para Integracion de Asistencias

Fecha de referencia: **20 de marzo de 2026**.

## Resumen

No se validaron "todos los modulos de Odoo" del servidor en sentido global.

Si se valido de forma puntual y suficiente el alcance funcional necesario para esta fase del proyecto:

- `hr`
- `hr_attendance`
- `to_attendance_device`
- `hr_biometric_attendance_sync`
- `odoo_biometric_bridge`

La validacion se hizo sobre la instancia real `devlyn_com` en la EC2 `52.6.240.186`.

## Modulos validados

### 1. `hr`

Validado:

- existe y esta `installed`
- el match biometrico -> empleado funciona por `hr_employee.employee_number`
- empleados totales: `1727`
- empleados con `employee_number`: `1725`
- recursos en `UTC`: `1722`
- recursos en `America/Mexico_City`: `5`

Conclusion:

- `employee_number` es la llave correcta para la Fase 1
- la configuracion horaria del maestro de empleados sigue siendo muy generica para inferencia avanzada

### 2. `hr_attendance`

Validado:

- existe y esta `installed`
- ya esta recibiendo eventos del sync biometrico v1
- `hr_attendance` total actual: `47`
- registros creados por biometria (`biometric_source = biometric_v1`): `30`
- asistencias biometricas abiertas al corte: `7`

Conclusion:

- el modulo ya esta integrado funcionalmente con la biometria
- la logica activa sigue siendo provisional por alternancia simple

### 3. `to_attendance_device`

Validado:

- existe y esta `installed`
- no se usa como ruta principal de integracion
- `attendance_device`: `0`
- `attendance_device_user`: `0`
- `user_attendance`: `0`
- `attendance_device_state_line`: `0`

Conclusion:

- el modulo esta presente pero sin configuracion operativa
- no forma parte del flujo activo de Fase 1

### 4. `hr_biometric_attendance_sync`

Validado:

- modulo custom instalado en `devlyn_com`
- menus visibles bajo `Asistencias -> Biometria`
- modelos creados:
  - `hr.biometric.event`
  - `hr.biometric.sync.cursor`
  - `hr.biometric.sync.run`
  - `hr.biometric.sync.config`
- extension activa sobre `hr.attendance`
- servicio `attendance-sync-worker` activo

Estado al corte:

- `hr_biometric_event`: `71`
- `hr_biometric_sync_run`: `37`

Conclusion:

- el staging y la trazabilidad en Odoo ya quedaron funcionales
- el worker ya escribe eventos y asistencias reales

### 5. `odoo_biometric_bridge`

Validado:

- el modulo sigue `installed`
- no se usa para la integracion con dispositivos de pared
- no participa en el flujo de asistencias implementado en esta fase

Conclusion:

- se mantiene instalado por contexto historico
- queda fuera del alcance funcional actual

## Configuracion Odoo validada

Se valido tambien la configuracion base que impacta asistencias:

- `attendance_kiosk_mode = manual`
- `attendance_barcode_source = front`
- `attendance_overtime_validation = no_validation`
- `hr_presence_control_attendance = true`

Conclusion:

- Odoo no estaba preparado previamente para una integracion de dispositivo fisico ya operativa
- por eso se implemento una capa propia de staging y sync

## Lo que si se reviso funcionalmente

- match por `employee_number`
- escritura de staging biometrico
- escritura de `hr.attendance`
- deduplicacion inicial
- eventos sin `device_id_resolved`
- empleado no encontrado
- modulo `to_attendance_device` para confirmar que no era la ruta elegida

## Lo que no se valido en esta fase

No se hizo auditoria funcional completa de otros modulos del ERP como:

- helpdesk
- ventas
- CRM
- compras
- contabilidad
- inventario
- otros addons custom no relacionados con asistencias

Tampoco se cerro aun la validacion funcional completa de:

- reglas de comida o descanso
- salida final
- turnos especiales
- feriados
- recalc retroactivo
- prioridad entre correccion manual y biometria

## Conclusión

Si quedo validada toda la informacion relevante de Odoo para esta fase de integracion biometrica con asistencias.

No quedo validado "todo Odoo" como plataforma completa, porque ese no era el alcance tecnico de esta etapa.
