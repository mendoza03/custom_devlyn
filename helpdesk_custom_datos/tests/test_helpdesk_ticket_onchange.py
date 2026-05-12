from odoo.addons.helpdesk.tests.common import HelpdeskCommon
from odoo.tests import new_test_user


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

    def test_allowed_scope_includes_subcategory_user_assignment(self):
        scoped_user = new_test_user(
            self.env,
            login="helpdesk_scope_by_subcategory",
            groups="base.group_user,helpdesk.group_helpdesk_user",
            company_id=self.main_company_id,
        )
        self.subcategory_a.user_ids = [(4, scoped_user.id)]

        ticket = self.env["helpdesk.ticket"].with_user(scoped_user).new({
            "team_id": self.test_team.id,
            "stage_id": self.stage_new.id,
            "x_general_description": "Scope by subcategory user",
        })
        ticket._compute_x_allowed_helpdesk_scope_ids()

        self.assertIn(self.section_a, ticket.x_allowed_section_ids)
        self.assertIn(self.category_a, ticket.x_allowed_category_ids)
        self.assertIn(self.subcategory_a, ticket.x_allowed_subcategory_ids)
