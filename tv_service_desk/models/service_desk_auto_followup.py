from datetime import timedelta

from odoo import api, fields, models


class ServiceDeskAutoFollowup(models.Model):
    _name = "service.desk.auto.followup"
    _description = "Auto Followup"
    _order = "sequence, name, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    line_ids = fields.One2many(
        "service.desk.auto.followup.line",
        "followup_id",
        string="Followup Configuration Lines",
    )


class ServiceDeskAutoFollowupLine(models.Model):
    _name = "service.desk.auto.followup.line"
    _description = "Auto Followup Line"
    _order = "sequence, id"

    followup_id = fields.Many2one(
        "service.desk.auto.followup",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    interval = fields.Integer(string="Interval", required=True, default=1)
    mail_template_id = fields.Many2one(
        "mail.template",
        string="Email Template",
        required=True,
        domain="[('model', '=', 'service.desk.ticket')]",
    )


class ServiceDeskTicketFollowupHistory(models.Model):
    _name = "service.desk.ticket.followup.history"
    _description = "Ticket Followup History"
    _order = "schedule_date, id"

    ticket_id = fields.Many2one(
        "service.desk.ticket",
        required=True,
        ondelete="cascade",
    )
    followup_date = fields.Date(string="Date of follow-up")
    schedule_date = fields.Date(string="Schedule Date", required=True)
    mail_template_id = fields.Many2one(
        "mail.template",
        string="Email Template",
        required=True,
        domain="[('model', '=', 'service.desk.ticket')]",
    )
    status = fields.Selection(
        [
            ("pending", "Pending"),
            ("success", "Success"),
            ("failed", "Failed"),
        ],
        string="Status",
        default="pending",
        required=True,
    )
    failure_reason = fields.Char(string="Failure Reason")

    def _send_followup_email(self):
        for history in self:
            ticket = history.ticket_id
            partner = ticket.partner_id
            template = history.mail_template_id
            if not template:
                history.write({
                    "status": "failed",
                    "failure_reason": "Missing email template.",
                })
                continue
            if ticket._is_helpdesk_email_opted_out():
                history.write({
                    "status": "failed",
                    "failure_reason": "Partner opted out of Helpdesk emails.",
                })
                continue
            if not partner or not (partner.email or ticket.partner_email):
                history.write({
                    "status": "failed",
                    "failure_reason": "Missing customer email address.",
                })
                continue
            try:
                template.send_mail(ticket.id, force_send=True)
                history.write({
                    "status": "success",
                    "followup_date": fields.Date.context_today(history),
                    "failure_reason": False,
                })
            except Exception as error:
                history.write({
                    "status": "failed",
                    "failure_reason": str(error),
                })
