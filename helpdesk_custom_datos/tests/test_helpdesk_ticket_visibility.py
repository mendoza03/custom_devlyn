from odoo.tests import new_test_user

from odoo.addons.helpdesk.tests.common import HelpdeskCommon


class TestHelpdeskTicketVisibility(HelpdeskCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        section = cls.env["helpdesk.section"].create({
            "name": "Visibility Section",
            "sequence": 1000,
        })
        category = cls.env["helpdesk.ticket.category"].create({
            "name": "Visibility Category",
            "section_id": section.id,
            "sequence": 1000,
        })
        subcategory = cls.env["helpdesk.ticket.subcategory"].create({
            "name": "Visibility Subcategory",
            "category_id": category.id,
            "sequence": 1000,
        })

        cls.other_helpdesk_user = new_test_user(
            cls.env,
            login="helpdesk_user_other",
            groups="base.group_user,helpdesk.group_helpdesk_user",
            company_id=cls.main_company_id,
        )
        cls.helpdesk_all_tickets_user = new_test_user(
            cls.env,
            login="helpdesk_user_all_tickets",
            groups="base.group_user,helpdesk_custom_datos.group_helpdesk_ticket_all",
            company_id=cls.main_company_id,
        )

        ticket_values = {
            "team_id": cls.test_team.id,
            "stage_id": cls.stage_progress.id,
            "x_general_description": "Visibility test ticket",
            "x_section_id": section.id,
            "x_category_id": category.id,
            "x_subcategory_id": subcategory.id,
        }
        cls.ticket_for_primary_user = cls.env["helpdesk.ticket"].create({
            **ticket_values,
            "name": "Ticket User 1",
            "user_id": cls.helpdesk_user.id,
        })
        cls.ticket_for_secondary_user = cls.env["helpdesk.ticket"].create({
            **ticket_values,
            "name": "Ticket User 2",
            "user_id": cls.other_helpdesk_user.id,
        })

    def test_helpdesk_user_only_sees_assigned_tickets(self):
        tickets = self.env["helpdesk.ticket"].with_user(self.helpdesk_user).search([])
        self.assertIn(self.ticket_for_primary_user, tickets)
        self.assertNotIn(self.ticket_for_secondary_user, tickets)

    def test_helpdesk_all_tickets_group_sees_every_ticket(self):
        tickets = self.env["helpdesk.ticket"].with_user(self.helpdesk_all_tickets_user).search([])
        self.assertIn(self.ticket_for_primary_user, tickets)
        self.assertIn(self.ticket_for_secondary_user, tickets)
