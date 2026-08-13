from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ServiceDeskSupportContract(models.Model):
    _name = "service.desk.support.contract"
    _description = "Support Contract"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_end desc, id desc"

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    partner_id = fields.Many2one("res.partner", required=True, tracking=True)
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    product_id = fields.Many2one(
        "product.product",
        string="Package Product",
        domain="[('type', '=', 'service')]",
    )
    total_hours = fields.Float(required=True, tracking=True)
    used_hours = fields.Float(compute="_compute_hours", store=True)
    remaining_hours = fields.Float(compute="_compute_hours", store=True)
    date_start = fields.Date(required=True, default=fields.Date.context_today)
    date_end = fields.Date(required=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("expired", "Expired"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        tracking=True,
    )
    low_hours_threshold = fields.Float(
        string="Low Balance Warning (Hours)",
        default=2.0,
        help="Send alert when remaining hours fall below this threshold.",
    )
    low_balance_alert_sent = fields.Boolean(copy=False)
    expiry_alert_sent = fields.Boolean(copy=False)
    sale_order_id = fields.Many2one("sale.order", string="Source Sale Order", readonly=True)
    ticket_ids = fields.One2many("service.desk.ticket", "support_contract_id", string="Tickets")
    ticket_count = fields.Integer(compute="_compute_ticket_count")

    @api.depends("ticket_ids.timesheet_ids.unit_amount")
    def _compute_hours(self):
        for contract in self:
            used = sum(contract.ticket_ids.mapped("timesheet_ids.unit_amount"))
            contract.used_hours = used
            contract.remaining_hours = max(contract.total_hours - used, 0.0)

    @api.depends("ticket_ids")
    def _compute_ticket_count(self):
        for contract in self:
            contract.ticket_count = len(contract.ticket_ids)

    @api.constrains("total_hours", "date_start", "date_end")
    def _check_contract(self):
        for contract in self:
            if contract.total_hours <= 0:
                raise ValidationError(_("Total hours must be greater than zero."))
            if contract.date_end < contract.date_start:
                raise ValidationError(_("End date must be after start date."))

    def action_activate(self):
        self.write({"state": "active"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_view_tickets(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Tickets"),
            "res_model": "service.desk.ticket",
            "view_mode": "list,form,kanban",
            "domain": [("support_contract_id", "=", self.id)],
        }

    def _check_low_balance(self):
        template = self.env.ref(
            "tv_service_desk.mail_template_contract_low_balance",
            raise_if_not_found=False,
        )
        for contract in self.filtered(
            lambda c: c.state == "active"
            and c.remaining_hours <= c.low_hours_threshold
            and not c.low_balance_alert_sent
        ):
            contract.low_balance_alert_sent = True
            if template:
                template.send_mail(contract.id, force_send=False)
            contract.activity_schedule(
                "mail.mail_activity_data_todo",
                summary=_("Low support hours: %s") % contract.name,
                user_id=contract.create_uid.id,
            )

    @api.model
    def _cron_contract_expiry(self):
        today = fields.Date.context_today(self)
        template = self.env.ref(
            "tv_service_desk.mail_template_contract_expiry",
            raise_if_not_found=False,
        )
        expiring = self.search([
            ("state", "=", "active"),
            ("date_end", "<=", today + timedelta(days=7)),
            ("date_end", ">=", today),
            ("expiry_alert_sent", "=", False),
        ])
        for contract in expiring:
            contract.expiry_alert_sent = True
            if template:
                template.send_mail(contract.id, force_send=False)
        expired = self.search([("state", "=", "active"), ("date_end", "<", today)])
        expired.write({"state": "expired"})
