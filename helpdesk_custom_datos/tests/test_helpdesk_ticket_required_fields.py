from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.helpdesk.tests.common import HelpdeskCommon


@tagged("post_install", "-at_install")
class TestHelpdeskTicketRequiredFields(HelpdeskCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.section = cls.env["helpdesk.section"].create({
            "name": "Required Fields Section",
            "sequence": 1003,
        })
        cls.category = cls.env["helpdesk.ticket.category"].create({
            "name": "Required Fields Category",
            "section_id": cls.section.id,
            "sequence": 1003,
        })
        cls.subcategory = cls.env["helpdesk.ticket.subcategory"].create({
            "name": "Trabajos atrasados",
            "category_id": cls.category.id,
            "sequence": 1003,
            "code": "trabajos_atrasados",
        })

    def _base_ticket_values(self):
        return {
            "team_id": self.test_team.id,
            "stage_id": self.stage_new.id,
            "x_general_description": "Required fields test ticket",
            "x_numero_telefonico": "5512345678",
            "x_correo": "required.fields@devlyn.com.mx",
            "x_section_id": self.section.id,
            "x_category_id": self.category.id,
            "x_subcategory_id": self.subcategory.id,
        }

    def test_trabajos_atrasados_requires_new_fields(self):
        with self.assertRaisesRegex(
            ValidationError,
            r"Invoice|Caja|Escenario|Nueva fecha prov",
        ):
            self.env["helpdesk.ticket"].create({
                **self._base_ticket_values(),
                "x_job_type": "Bifocal",
                "x_original_order_number": "ABCP123456",
                "x_order_number": "DEFP123456",
                "x_customer_warehouse": "si",
                "x_lab_indicated": "LAB Norte",
                "x_shipping_guide_number": "GUIA-123",
                "x_frame_bag_number": "BG12345678",
                "x_order_type": "retallado",
            })
