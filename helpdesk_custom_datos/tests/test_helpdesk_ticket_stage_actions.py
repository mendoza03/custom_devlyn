from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.helpdesk.tests.common import HelpdeskCommon


@tagged("post_install", "-at_install")
class TestHelpdeskTicketStageActions(HelpdeskCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.section = cls.env["helpdesk.section"].create({
            "name": "Stage Actions Section",
            "sequence": 1002,
        })
        cls.category = cls.env["helpdesk.ticket.category"].create({
            "name": "Stage Actions Category",
            "section_id": cls.section.id,
            "sequence": 1002,
        })
        cls.subcategory = cls.env["helpdesk.ticket.subcategory"].create({
            "name": "Stage Actions Subcategory",
            "category_id": cls.category.id,
            "sequence": 1002,
            "code": "stage_actions_subcategory",
        })

    def _create_ticket(self):
        return self.env["helpdesk.ticket"].create({
            "team_id": self.test_team.id,
            "stage_id": self.stage_new.id,
            "x_general_description": "Stage actions test ticket",
            "x_section_id": self.section.id,
            "x_category_id": self.category.id,
            "x_subcategory_id": self.subcategory.id,
        })

    def test_write_in_progress_requires_commitment_date(self):
        ticket = self._create_ticket()

        with self.assertRaisesRegex(
            ValidationError,
            r"Al cambiar el estatus a 'En proceso de solución'",
        ):
            ticket.write({"stage_id": self.stage_progress.id})

    def test_in_progress_wizard_updates_stage_and_commitment_date(self):
        ticket = self._create_ticket()
        wizard = self.env["helpdesk.ticket.commitment.wizard"].create({
            "ticket_id": ticket.id,
            "commitment_date": "2026-05-01",
        })

        wizard.action_confirm()

        self.assertEqual(ticket.stage_id, self.stage_progress)
        self.assertEqual(str(ticket.x_commitment_date), "2026-05-01")

    def test_action_set_solved_changes_stage(self):
        ticket = self._create_ticket()
        ticket.write({
            "stage_id": self.stage_progress.id,
            "x_commitment_date": "2026-05-01",
        })

        ticket.action_set_stage_solved()

        self.assertEqual(ticket.stage_id, self.stage_done)
