from odoo import models, fields

class ProductLayoutSpot(models.Model):
    _name = 'product.layout.spot'
    _description = 'Product Layout Spot'

    design_id = fields.Many2one('product.layout.design', required=True)
    name = fields.Char(string='Label')
    product_id = fields.Many2one('product.template', string='Product')
    pos_x = fields.Integer(string='X')
    pos_y = fields.Integer(string='Y')


class ProductLayoutDesign(models.Model):
    _name = 'product.layout.design'
    _description = 'Product Layout Design'

    name = fields.Char(string='Design Name')
    spot_ids = fields.One2many('product.layout.spot', 'design_id', string='Spots')
    image = fields.Binary("Plano de fondo")

    def action_open_html_layout(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/product_layout/view/{self.id}',
            'target': 'new',
        }

