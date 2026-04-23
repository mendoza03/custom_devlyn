from odoo.addons.helpdesk.tests.common import HelpdeskCommon


class TestHelpdeskTicketAutoClose(HelpdeskCommon):

    def test_ticket_auto_closes_after_24_weekday_hours(self):
        section = self.env["helpdesk.section"].create({
            "name": "Auto Close Section",
            "sequence": 999,
        })
        category = self.env["helpdesk.ticket.category"].create({
            "name": "Auto Close Category",
            "section_id": section.id,
            "sequence": 999,
        })
        subcategory = self.env["helpdesk.ticket.subcategory"].create({
            "name": "Auto Close Subcategory",
            "category_id": category.id,
            "sequence": 999,
        })

        with self._ticket_patch_now("2026-04-24 10:00:00"):
            ticket = self.env["helpdesk.ticket"].create({
                "name": "Auto close inactivity",
                "team_id": self.test_team.id,
                "stage_id": self.stage_progress.id,
                "x_general_description": "Auto close inactivity",
                "x_section_id": section.id,
                "x_category_id": category.id,
                "x_subcategory_id": subcategory.id,
            })

        with self._ticket_patch_now("2026-04-27 09:00:00"):
            self.env["helpdesk.ticket"]._cron_auto_close_inactive_weekday_tickets()
            self.assertEqual(ticket.stage_id, self.stage_progress)
            self.assertFalse(ticket.close_date)

        with self._ticket_patch_now("2026-04-27 10:00:00"):
            self.env["helpdesk.ticket"]._cron_auto_close_inactive_weekday_tickets()
            self.assertEqual(ticket.stage_id, self.stage_done)
            self.assertTrue(ticket.close_date)
