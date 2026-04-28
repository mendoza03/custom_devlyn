from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.helpdesk.tests.common import HelpdeskCommon


@tagged("post_install", "-at_install")
class TestHelpdeskTicketDuplicateReference(HelpdeskCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.section = cls.env["helpdesk.section"].create({
            "name": "Duplicate Reference Section",
            "sequence": 1001,
        })
        cls.category = cls.env["helpdesk.ticket.category"].create({
            "name": "Duplicate Reference Category",
            "section_id": cls.section.id,
            "sequence": 1001,
        })
        cls.subcategory = cls.env["helpdesk.ticket.subcategory"].create({
            "name": "Duplicate Reference Subcategory",
            "category_id": cls.category.id,
            "sequence": 1001,
            "code": "duplicate_reference_subcategory",
        })

    def _base_ticket_values(self):
        return {
            "team_id": self.test_team.id,
            "x_general_description": "Duplicate reference test ticket",
            "x_section_id": self.section.id,
            "x_category_id": self.category.id,
            "x_subcategory_id": self.subcategory.id,
        }

    def test_duplicate_order_number_same_subcategory_is_blocked(self):
        self.env["helpdesk.ticket"].create({
            **self._base_ticket_values(),
            "stage_id": self.stage_progress.id,
            "x_order_number": "ABCP123456",
        })

        with self.assertRaisesRegex(
            ValidationError,
            r"Este pedido cuenta con el ticket .* se encuentra pendiente de solución",
        ):
            self.env["helpdesk.ticket"].create({
                **self._base_ticket_values(),
                "stage_id": self.stage_new.id,
                "x_order_number": "ABCP123456",
            })

    def test_duplicate_sale_order_same_subcategory_is_blocked(self):
        self.env["helpdesk.ticket"].create({
            **self._base_ticket_values(),
            "stage_id": self.stage_progress.id,
            "x_refac_sale_order": "ABCV123456",
        })

        with self.assertRaisesRegex(
            ValidationError,
            r"Este pedido cuenta con el ticket .* se encuentra pendiente de solución",
        ):
            self.env["helpdesk.ticket"].create({
                **self._base_ticket_values(),
                "stage_id": self.stage_new.id,
                "x_refac_sale_order": "ABCV123456",
            })

    def test_duplicate_reference_ignores_cancelled_tickets(self):
        self.env["helpdesk.ticket"].create({
            **self._base_ticket_values(),
            "stage_id": self.stage_cancel.id,
            "x_order_number": "ZZZP654321",
        })

        ticket = self.env["helpdesk.ticket"].create({
            **self._base_ticket_values(),
            "stage_id": self.stage_new.id,
            "x_order_number": "ZZZP654321",
        })

        self.assertTrue(ticket)

    def test_order_number_is_normalized_before_validation_and_duplicate_check(self):
        ticket = self.env["helpdesk.ticket"].create({
            **self._base_ticket_values(),
            "stage_id": self.stage_progress.id,
            "x_original_order_number": "  asdp151515  ",
        })

        self.assertEqual(ticket.x_original_order_number, "ASDP151515")

        with self.assertRaisesRegex(
            ValidationError,
            r"Este pedido cuenta con el ticket .* se encuentra pendiente de solución",
        ):
            self.env["helpdesk.ticket"].create({
                **self._base_ticket_values(),
                "stage_id": self.stage_new.id,
                "x_order_number": "ASDP151515",
            })
