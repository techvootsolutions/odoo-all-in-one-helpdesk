from odoo import api, fields, models


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    sd_ticket_id = fields.Many2one("service.desk.ticket", string="Service Desk Ticket", ondelete="set null")
    sd_hour_package_id = fields.Many2one(
        "service.desk.customer.hour.package",
        string="Customer Hour Package",
        ondelete="set null",
    )
    start_date = fields.Datetime(string="Start Date")
    end_date = fields.Datetime(string="End Date")

    @api.onchange("start_date", "end_date")
    def _onchange_start_end_date(self):
        if self.start_date and self.end_date:
            duration = (self.end_date - self.start_date).total_seconds() / 3600.0
            self.unit_amount = round(duration, 2)

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._sd_update_contract_hours()
        packages = lines.mapped("sd_hour_package_id")
        if packages:
            packages._compute_hour_balances()
        return lines

    def write(self, vals):
        packages = self.mapped("sd_hour_package_id")
        res = super().write(vals)
        if any(key in vals for key in ("unit_amount", "sd_ticket_id", "sd_hour_package_id")):
            self._sd_update_contract_hours()
            packages |= self.mapped("sd_hour_package_id")
            if packages:
                packages._compute_hour_balances()
        return res

    def unlink(self):
        packages = self.mapped("sd_hour_package_id")
        res = super().unlink()
        if packages:
            packages._compute_hour_balances()
        return res

    def _sd_update_contract_hours(self):
        contracts = self.mapped("sd_ticket_id.support_contract_id").filtered(lambda c: c.state == "active")
        if contracts:
            contracts._check_low_balance()
