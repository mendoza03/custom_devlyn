# -*- coding: utf-8 -*-
import logging
import requests
from odoo import fields, models, api
from odoo.exceptions import UserError
from datetime import date, datetime
import json

_logger = logging.getLogger(__name__)

class Property(models.Model):
    _inherit = 'product.template'
    
    def serialize_dates(self, data):
        """Convierte objetos date/datetime a strings ISO format"""
        if isinstance(data, (date, datetime)):
            return data.isoformat()
        elif isinstance(data, dict):
            return {k: self.serialize_dates(v) for k, v in data.items()}
        elif isinstance(data, (list, tuple)):
            return [self.serialize_dates(item) for item in data]
        return data
    
    def write(self, vals):
        records = super().write(vals)
        
        # URL de FastAPI 
        API_URL = "http://138.186.200.38/update_product"
        
        for record in self:
            _logger.info("Enviando actualizacion a API para producto ID: %s", record.id)
            
            safe_vals = self.serialize_dates(vals)
            
            payload = {
                "product_id": record.id,
                "name": record.name,
                "state": record.state,
                "changes": safe_vals,
                "price": record.price_per_m,
                "type": record.terrain_type,
                # Fecha de apartado
                "property_date": record.property_date.isoformat() if record.property_date else None,
                # Nombre del asesor (many2one)
                "asesor": record.asesor.name if record.asesor else None,
                # Nombre del lead (many2one)
                "lead": record.lead.name if record.lead else None,
            }
            
            try:
                response = requests.post(
                    API_URL,
                    json=payload,
                    timeout=10
                )
                
                if response.status_code != 200:
                    _logger.error(
                        "Error al enviar datos a API. Codigo: %s, Respuesta: %s", 
                        response.status_code, response.text
                    )
                    
            except requests.exceptions.RequestException as e:
                _logger.error("Error de conexion con la API: %s", str(e))
               
        return records