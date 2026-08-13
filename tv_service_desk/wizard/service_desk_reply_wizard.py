from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ServiceDeskReplyWizard(models.TransientModel):
    _name = "service.desk.reply.wizard"
    _description = "Reply to Service Desk Ticket"

    ticket_id = fields.Many2one("service.desk.ticket", required=True, ondelete="cascade")
    partner_id = fields.Many2one("res.partner", string="Customer", readonly=True)
    email_to = fields.Char(string="To")
    subject = fields.Char(required=True)
    body = fields.Html(sanitize_attributes=False, required=True)
    attachment_ids = fields.Many2many("ir.attachment", string="Attachments")
    partner_opt_out_helpdesk_emails = fields.Boolean(
        string="Opt Out Helpdesk Emails",
        compute="_compute_partner_opt_out_helpdesk_emails",
    )

    @api.depends("ticket_id", "ticket_id.partner_id", "ticket_id.partner_id.sd_opt_out_emails")
    def _compute_partner_opt_out_helpdesk_emails(self):
        for wizard in self:
            wizard.partner_opt_out_helpdesk_emails = (
                wizard.ticket_id._is_helpdesk_email_opted_out() if wizard.ticket_id else False
            )
    template_id = fields.Many2one(
        "mail.template",
        string="Load template",
        domain="[('model', '=', 'service.desk.ticket')]",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ticket = self.env["service.desk.ticket"].browse(
            self.env.context.get("default_ticket_id")
        )
        if ticket:
            res.setdefault("ticket_id", ticket.id)
            res.setdefault("partner_id", ticket.partner_id.id)
            res.setdefault("email_to", ticket.partner_email or ticket.partner_id.email)
            template = self.env["res.config.settings"].get_config_mail_template(
                "tv_service_desk.reply_mail_template_id",
                "tv_service_desk.mail_template_ticket_reply",
            )
            if template:
                res.setdefault("template_id", template.id)
                res.setdefault(
                    "subject",
                    template._render_field("subject", ticket.ids).get(ticket.id, ""),
                )
                res.setdefault(
                    "body",
                    template._render_field("body_html", ticket.ids).get(ticket.id, ""),
                )
        return res

    @api.onchange("template_id")
    def _onchange_template_id(self):
        if self.template_id and self.ticket_id:
            self.body = self.template_id._render_field(
                "body_html",
                self.ticket_id.ids,
            ).get(self.ticket_id.id, self.body)
            if self.template_id.subject:
                self.subject = self.template_id._render_field(
                    "subject",
                    self.ticket_id.ids,
                ).get(self.ticket_id.id, self.subject)

    def action_send_reply(self):
        self.ensure_one()
        ticket = self.ticket_id
        if ticket._is_helpdesk_email_opted_out():
            raise UserError(_(
                "This partner has opted out of Helpdesk emails. "
                "The email cannot be sent."
            ))
        mail_values = {
            "subject": self.subject,
            "body_html": self.body,
            "email_to": self.email_to,
            "email_from": self.env.user.email_formatted or self.env.company.email_formatted,
            "attachment_ids": [(6, 0, self.attachment_ids.ids)],
        }
        self.env["mail.mail"].sudo().create(mail_values).send()
        ticket.message_post(
            body=self.body,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            partner_ids=ticket.partner_id.ids,
            attachment_ids=self.attachment_ids.ids,
        )
        return {"type": "ir.actions.act_window_close"}

    def action_save_template(self):
        self.ensure_one()
        template = self.template_id or self.env["res.config.settings"].get_config_mail_template(
            "tv_service_desk.reply_mail_template_id",
            "tv_service_desk.mail_template_ticket_reply",
        )
        if not template:
            raise UserError(_("Reply mail template is not configured."))
        template.write({
            "subject": self.subject,
            "body_html": self.body,
        })
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Template Saved"),
                "message": _("The email template has been updated."),
                "type": "success",
                "sticky": False,
            },
        }
