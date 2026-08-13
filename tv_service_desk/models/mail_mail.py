from odoo import fields, models


class MailMail(models.Model):
    _inherit = "mail.mail"

    def action_view_service_desk_ticket(self):
        self.ensure_one()
        if self.model != "service.desk.ticket" or not self.res_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": self.env["service.desk.ticket"].browse(self.res_id).name,
            "res_model": "service.desk.ticket",
            "res_id": self.res_id,
            "view_mode": "form",
            "target": "current",
        }
