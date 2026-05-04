from odoo.addons.helpdesk.tests.common import HelpdeskCommon


class TestHelpdeskTicketOnchange(HelpdeskCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.section_a = cls.env["helpdesk.section"].create({
            "name": "Onchange Section A",
            "sequence": 1100,
        })
        cls.category_a = cls.env["helpdesk.ticket.category"].create({
            "name": "Onchange Category A",
            "section_id": cls.section_a.id,
            "sequence": 1100,
        })
        cls.subcategory_a = cls.env["helpdesk.ticket.subcategory"].create({
            "name": "Onchange Subcategory A",
            "category_id": cls.category_a.id,
            "sequence": 1100,
        })
        cls.section_b = cls.env["helpdesk.section"].create({
            "name": "Onchange Section B",
            "sequence": 1101,
        })

    def test_onchange_section_clears_category_and_subcategory(self):
        ticket = self.env["helpdesk.ticket"].new({
            "team_id": self.test_team.id,
            "stage_id": self.stage_new.id,
            "x_general_description": "Onchange test ticket",
            "x_section_id": self.section_a.id,
            "x_category_id": self.category_a.id,
            "x_subcategory_id": self.subcategory_a.id,
        })

        ticket.x_section_id = self.section_b
        ticket._onchange_x_section_id_clear_classification()

        self.assertFalse(ticket.x_category_id)
        self.assertFalse(ticket.x_subcategory_id)
