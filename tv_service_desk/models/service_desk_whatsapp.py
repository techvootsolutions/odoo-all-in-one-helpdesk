from odoo import _, api, fields, models


class ServiceDeskWhatsappConfig(models.Model):
    _name = "service.desk.whatsapp.config"
    _description = "WhatsApp Integration Configuration"
    _rec_name = "company_id"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True)
    api_url = fields.Char(string="Webhook / API URL")
    api_token = fields.Char(string="API Token")
    phone_number_id = fields.Char(string="Phone Number ID")
    default_team_id = fields.Many2one("service.desk.team", string="Default Team")
    notify_on_create = fields.Boolean(default=True)
    notify_on_assign = fields.Boolean(default=True)
    notify_on_close = fields.Boolean(default=True)

    _sql_constraints = [
        ("company_unique", "unique(company_id)", "Only one WhatsApp configuration per company."),
    ]

    @api.model
    def _partner_phone(self, partner):
        """Return partner phone (Odoo 19 uses phone; mobile may exist with extra modules)."""
        if not partner:
            return False
        return partner.phone or getattr(partner, "mobile", False)

    def _send_whatsapp_message(self, partner, body):
        """Hook for external WhatsApp API. Override or extend in a bridge module."""
        self.ensure_one()
        if not self.api_url or not self._partner_phone(partner):
            return False
        self.env["service.desk.whatsapp.message"].create({
            "direction": "outbound",
            "partner_id": partner.id,
            "body": body,
            "state": "queued",
        })
        return True


class ServiceDeskWhatsappMessage(models.Model):
    _name = "service.desk.whatsapp.message"
    _description = "WhatsApp Message Log"
    _order = "create_date desc"

    ticket_id = fields.Many2one("service.desk.ticket", ondelete="cascade")
    partner_id = fields.Many2one("res.partner")
    direction = fields.Selection(
        [("inbound", "Inbound"), ("outbound", "Outbound")],
        required=True,
    )
    body = fields.Text(required=True)
    external_id = fields.Char(string="External Message ID")
    state = fields.Selection(
        [("queued", "Queued"), ("sent", "Sent"), ("received", "Received"), ("failed", "Failed")],
        default="received",
    )
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)

    @api.model
    def process_incoming(self, phone, message_body, external_id=False):
        """Create or update ticket from inbound WhatsApp message."""
        Partner = self.env["res.partner"]
        domain = [("phone", "=", phone)]
        if "mobile" in Partner._fields:
            domain = ["|", ("mobile", "=", phone), ("phone", "=", phone)]
        partner = Partner.search(domain, limit=1)
        config = self.env["service.desk.whatsapp.config"].sudo().search(
            [("company_id", "=", self.env.company.id), ("active", "=", True)],
            limit=1,
        )
        team = config.default_team_id if config else False
        open_tickets = self.env["service.desk.ticket"].search([
            ("partner_id", "=", partner.id) if partner else ("id", "=", False),
            ("stage_id.is_closed", "=", False),
        ], limit=1, order="create_date desc")
        if open_tickets:
            ticket = open_tickets
        else:
            ticket = self.env["service.desk.ticket"].create({
                "subject": _("WhatsApp: %s") % (partner.name if partner else phone),
                "description": message_body,
                "partner_id": partner.id if partner else False,
                "partner_phone": phone,
                "team_id": team.id if team else False,
            })
            if config and config.notify_on_create and partner:
                config._send_whatsapp_message(
                    partner,
                    _("Your ticket %s has been created.") % ticket.name,
                )
        self.create({
            "ticket_id": ticket.id,
            "partner_id": partner.id if partner else False,
            "direction": "inbound",
            "body": message_body,
            "external_id": external_id,
            "state": "received",
        })
        ticket.message_post(
            body=_("<b>WhatsApp</b>: %s") % message_body,
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )
        return ticket
