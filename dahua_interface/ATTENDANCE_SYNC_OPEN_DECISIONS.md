# Faltantes Funcionales para Fase 2 y Fase 3

Estos puntos no bloquean la Fase 1, pero deben cerrarse antes del motor de inferencia.

## Reglas pendientes

- politica oficial de entrada, comida, regreso y salida
- manejo de numero impar de marcas
- manejo de eventos tardios del dia anterior
- prioridad entre biometria y correccion manual
- estrategia de recalc retroactivo

## Datos pendientes

- catalogo `DeviceID -> sucursal -> puerta -> rol`
- politica de almuerzo por sucursal o jornada
- turnos especiales o nocturnos
- criterio oficial de cierre diario por operacion

## Observaciones actuales

- el dispositivo sigue reportando marcas utiles como `entry`
- `employee_number` es la llave correcta para match con Odoo
- `to_attendance_device` no es la ruta de integracion elegida para Fase 1
