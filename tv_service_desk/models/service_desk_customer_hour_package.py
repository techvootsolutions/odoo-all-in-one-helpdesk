from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class ServiceDeskCustomerHourPackage(models.Model):
    _name = "service.desk.customer.hour.package"
    _description = "Customer Hour Package"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_start desc, id desc"

    name = fields.Char(required=True, tracking=True)
    partner_id = fields.Many2one("res.partner", string="Customer", required=True, tracking=True)
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    date_start = fields.Date(string="Package Start", required=True, default=fields.Date.context_today)
    date_end = fields.Date(string="Package End", required=True)
    initial_allocated_hours = fields.Float(string="Initial Allocated Hours", default=0.0, tracking=True)
    rolled_over_hours = fields.Float(string="Rolled Over Hours", default=0.0, tracking=True)
    total_allocated_hours = fields.Float(
        string="Total Allocated Hours",
        compute="_compute_hour_balances",
        store=True,
    )
    hours_consumed = fields.Float(
        string="Hours Consumed",
        compute="_compute_hour_balances",
        store=True,
    )
    remaining_hours = fields.Float(
        string="Remaining Hours",
        compute="_compute_hour_balances",
        store=True,
    )
    state = fields.Selection(
        [("open", "Open"), ("close", "Close")],
        string="Status",
        default="open",
        tracking=True,
    )
    timesheet_line_ids = fields.One2many(
        "account.analytic.line",
        "sd_hour_package_id",
        string="Timesheet Lines",
    )

    @api.depends(
        "initial_allocated_hours",
        "rolled_over_hours",
        "timesheet_line_ids.unit_amount",
    )
    def _compute_hour_balances(self):
        for package in self:
            total = package.initial_allocated_hours + package.rolled_over_hours
            consumed = sum(package.timesheet_line_ids.mapped("unit_amount"))
            package.total_allocated_hours = total
            package.hours_consumed = consumed
            package.remaining_hours = max(total - consumed, 0.0)

    @api.model
    def _get_default_allocated_hours(self):
        return float(
            self.env["ir.config_parameter"].sudo().get_param(
                "tv_service_desk.allocated_hours_for_month", 20
            )
        )

    @api.model
    def _get_partner_allocated_hours(self, partner):
        hours = partner.sd_allocated_hours_for_month
        if hours and hours > 0:
            return hours
        return 0.0

    @api.model
    def _get_open_package(self, partner, on_date=None):
        if not partner:
            return self.browse()
        on_date = on_date or fields.Date.context_today(self)
        partners = partner | partner.commercial_partner_id
        return self.search([
            ("partner_id", "in", partners.ids),
            ("state", "=", "open"),
            ("date_start", "<=", on_date),
            ("date_end", ">=", on_date),
        ], limit=1, order="date_start desc")

    def _prepare_package_name(self, partner, date_start):
        return "%s - %s" % (partner.display_name, date_start.strftime("%B %Y"))

    @api.model
    def _prepare_package_dates(self, date_ref=None):
        date_ref = fields.Date.to_date(date_ref or fields.Date.context_today(self))
        date_start = date_ref.replace(day=1)
        date_end = date_start + relativedelta(months=1) - relativedelta(days=1)
        return date_start, date_end

    @api.onchange("date_start")
    def _onchange_date_start(self):
        if self.date_start:
            date_start, date_end = self._prepare_package_dates(self.date_start)
            self.date_start = date_start
            self.date_end = date_end

    def action_close(self):
        self.write({"state": "close"})

    @api.model
    def _ensure_open_hour_package_for_partners(self, partners):
        """Create the current month package for contacts with allocated hours."""
        today = fields.Date.context_today(self)
        date_start, date_end = self._prepare_package_dates(today)
        default_hours = self._get_default_allocated_hours()

        for partner in partners:
            initial_hours = self._get_partner_allocated_hours(partner)
            if initial_hours <= 0:
                continue
            if self._get_open_package(partner, on_date=today):
                continue

            expired = self.search([
                ("partner_id", "=", partner.id),
                ("state", "=", "open"),
                ("date_end", "<", date_start),
            ])
            rollover = sum(expired.mapped("remaining_hours"))
            if expired:
                expired.write({"state": "close"})

            self.create({
                "name": self._prepare_package_name(partner, date_start),
                "partner_id": partner.id,
                "company_id": partner.company_id.id or self.env.company.id,
                "date_start": date_start,
                "date_end": date_end,
                "initial_allocated_hours": initial_hours or default_hours,
                "rolled_over_hours": rollover,
                "state": "open",
            })

    @api.model
    def _run_auto_create_customer_hour_package(self):
        partners = self.env["res.partner"].search([
            ("sd_allocated_hours_for_month", ">", 0),
        ])
        self._ensure_open_hour_package_for_partners(partners)
