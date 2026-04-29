# Helpdesk SLA Enterprise XLSX Reports

Enterprise XLSX reporting module for Odoo Helpdesk.

## What it does

- Generates a professional XLSX workbook for SLA reporting.
- Avoids SQL views to prevent module installation locks.
- Provides security groups:
  - SLA Report User
  - SLA Report Manager
- Adds a standalone menu: Helpdesk SLA → Enterprise XLSX Reports → Generate SLA Report.
- Includes:
  - Executive Summary
  - SLA Details
  - Team Summary
  - Agent Summary
  - Monthly Summary

## Install

1. Copy this folder into your custom addons path.
2. Update Apps List.
3. Install: Helpdesk SLA Enterprise XLSX Reports.
4. Assign users to the group: SLA Report User.

## Notes

- Native Odoo SLA status is used when available through `helpdesk.sla.status`.
- When no native SLA exists for a ticket, the report uses the fallback SLA target hours from the wizard.
- First response is calculated from the first internal user message on the ticket.
