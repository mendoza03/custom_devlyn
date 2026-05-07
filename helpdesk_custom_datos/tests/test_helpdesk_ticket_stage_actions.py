from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tests import new_test_user

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
        cls.other_helpdesk_user = new_test_user(
            cls.env,
            login="stage_actions_helpdesk_user_other",
            groups="base.group_user,helpdesk.group_helpdesk_user",
            company_id=cls.main_company_id,
        )

    def _create_ticket(self):
        return self.env["helpdesk.ticket"].create({
            "team_id": self.test_team.id,
            "stage_id": self.stage_new.id,
            "x_general_description": "Stage actions test ticket",
            "x_centro_sap": "SAP001",
            "x_numero_telefonico": "5512345678",
            "x_correo": "stage.actions@devlyn.com.mx",
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

    def test_user_id_can_be_updated_outside_new_stage(self):
        ticket = self._create_ticket()
        ticket.write({
            "stage_id": self.stage_progress.id,
            "x_commitment_date": "2026-05-01",
            "user_id": self.helpdesk_user.id,
        })

        ticket.write({"user_id": self.other_helpdesk_user.id})

        self.assertEqual(ticket.user_id, self.other_helpdesk_user)

    def test_other_locked_fields_still_require_new_stage(self):
        ticket = self._create_ticket()
        ticket.write({
            "stage_id": self.stage_progress.id,
            "x_commitment_date": "2026-05-01",
        })

        with self.assertRaisesRegex(
            UserError,
            r"Solo se pueden modificar estos campos cuando el ticket está en estado Nuevo.",
        ):
            ticket.write({"x_general_description": "Intento bloqueado"})
