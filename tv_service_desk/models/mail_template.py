from odoo import models
from odoo.tools import email_normalize


class MailTemplate(models.Model):
    _inherit = "mail.template"

    def _sd_helpdesk_customer_email_blocked(self, ticket):
        if self.model != "service.desk.ticket" or not ticket.partner_id:
            return False
        if not ticket._is_helpdesk_email_opted_out():
            return False
        rendered_to = self._render_field("email_to", ticket.ids).get(ticket.id, "") or ""
        partner = ticket.partner_id.commercial_partner_id
        partner_emails = {
            email_normalize(email)
            for email in (
                [ticket.partner_email, ticket.partner_id.email, partner.email]
                + partner.child_ids.mapped("email")
            )
            if email
        }
        for address in rendered_to.split(","):
            normalized = email_normalize(address.strip())
            if normalized and normalized in partner_emails:
                return True
        return False

    def send_mail(self, res_id, force_send=False, raise_exception=False, email_values=None,
                  email_layout_xmlid=False):
        if self.model == "service.desk.ticket":
            ticket = self.env["service.desk.ticket"].browse(res_id).exists()
            if ticket and self._sd_helpdesk_customer_email_blocked(ticket):
                return False
        return super().send_mail(
            res_id,
            force_send=force_send,
            raise_exception=raise_exception,
            email_values=email_values,
            email_layout_xmlid=email_layout_xmlid,
        )
