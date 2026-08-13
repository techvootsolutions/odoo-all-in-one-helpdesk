import re
from urllib.parse import quote

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import html2plaintext


class ServiceDeskWhatsappSendWizard(models.TransientModel):
    _name = "service.desk.whatsapp.send.wizard"
    _description = "Send Helpdesk Ticket By Whatsapp"

    ticket_id = fields.Many2one("service.desk.ticket", required=True, ondelete="cascade")
    partner_id = fields.Many2one("res.partner", string="Customer", readonly=True)
    email_to = fields.Char(string="To")
    subject = fields.Char(required=True)
    body = fields.Html(sanitize_attributes=False, required=True)
    attachment_ids = fields.Many2many("ir.attachment", string="Attachments")
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
            res.setdefault("subject", ticket._get_whatsapp_message_subject())
            res.setdefault("body", ticket._build_whatsapp_message_html())
            template = self.env.ref(
                "tv_service_desk.mail_template_ticket_whatsapp_send",
                raise_if_not_found=False,
            )
            if template:
                res.setdefault("template_id", template.id)
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

    def _get_plain_body(self):
        self.ensure_one()
        return html2plaintext(self.body or "").strip()

    def _post_chatter_message(self, plain_body):
        self.ensure_one()
        config = self.env["res.config.settings"].get_whatsapp_message_config()
        if config.get("display_chatter"):
            self.ticket_id.message_post(
                body=plain_body.replace("\n", "<br/>"),
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
                partner_ids=self.ticket_id.partner_id.ids,
            )

    def action_send(self):
        self.ensure_one()
        ticket = self.ticket_id
        plain_body = self._get_plain_body()
        mail_values = {
            "subject": self.subject,
            "body_html": self.body,
            "email_to": self.email_to,
            "email_from": self.env.user.email_formatted or self.env.company.email_formatted,
            "attachment_ids": [(6, 0, self.attachment_ids.ids)],
        }
        self.env["mail.mail"].sudo().create(mail_values).send()
        self._post_chatter_message(plain_body)
        return {"type": "ir.actions.act_window_close"}

    def action_send_by_whatsapp(self):
        self.ensure_one()
        ticket = self.ticket_id
        mobile = ticket._get_partner_mobile()
        if not mobile:
            raise UserError(_("Partner Mobile Number Not Exist !"))
        plain_body = self._get_plain_body()
        whatsapp_text = ticket._format_whatsapp_url_text(plain_body)
        phone = re.sub(r"\D", "", mobile)
        url = "https://web.whatsapp.com/send?phone=%s&text=%s" % (phone, quote(whatsapp_text, safe="*%"))
        self._post_chatter_message(plain_body)
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }

    def action_save_template(self):
        self.ensure_one()
        template = self.template_id or self.env.ref(
            "tv_service_desk.mail_template_ticket_whatsapp_send",
            raise_if_not_found=False,
        )
        if not template:
            raise UserError(_("WhatsApp mail template is not configured."))
        template.write({
            "subject": self.subject,
            "body_html": self.body,
        })
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Success"),
                "message": _("Template saved successfully."),
                "type": "success",
                "sticky": False,
            },
        }
