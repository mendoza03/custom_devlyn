# Gestión de Metas de Ventas

Módulo para Odoo 18 que permite gestionar metas de ventas con embudo de conversión.

## Características

* Define metas anuales por importe monetario
* Calcula automáticamente objetivos de leads necesarios
* Embudo de conversión configurable: Leads → Prospecto → Cita → Oportunidad → Apartado → Cierre
* Estructura jerárquica: CCO → DVN → Gerente → Asesor
* Desglose por períodos: Anual, Mensual, Semanal, Diario
* Redondeo automático hacia arriba en todos los cálculos
* Períodos mensuales editables

## Instalación

1. Copia esta carpeta en tu directorio de addons de Odoo
2. Actualiza la lista de aplicaciones
3. Busca "Gestión de Metas de Ventas"
4. Click en Instalar

## Uso

### 1. Configuración Inicial

Ve a **Ventas → Configuración → Metas de Ventas** y configura:
- Precio promedio por unidad
- Número de leads por unidad
- Porcentajes de conversión del embudo

### 2. Crear Meta Anual

Ve a **Metas de Ventas → Metas → Crear**

Llena:
- Empresa
- Año
- Posición (CCO, DVN, Gerente, Asesor)
- Responsable (usuario)
- Meta Padre (opcional, para jerarquía)
- Meta Anual (importe en dinero)

### 3. Generar Períodos

Click en **"Generar Períodos"** para crear 12 meses automáticamente.

### 4. Ajustar Períodos Mensuales

En la pestaña **"MENSUAL"**, puedes editar el importe de cada mes según necesites.

## Estructura de Datos

- **sale.goal.config**: Configuración global de parámetros
- **sale.goal**: Meta anual de cada persona
- **sale.goal.period**: 12 períodos mensuales por meta

## Autor

Axeel Cerrato

## Licencia

LGPL-3
