from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    sd_opt_out_emails = fields.Boolean(
        string="Opt Out Helpdesk Emails",
        help="When enabled, this contact will not receive helpdesk email notifications.",
    )

    def _sd_is_helpdesk_email_opted_out(self):
        self.ensure_one()
        return bool(self.commercial_partner_id.sd_opt_out_emails)

    sd_ticket_count = fields.Integer(compute="_compute_sd_ticket_count")
    sd_hour_package_count = fields.Integer(compute="_compute_sd_hour_package_count")
    sd_allocated_hours_for_month = fields.Float(
        string="Allocated Hours For Month",
        default=0.0,
    )
    sd_hour_package_ids = fields.One2many(
        "service.desk.customer.hour.package",
        "partner_id",
        string="Hour Packages",
    )
    sd_support_contract_ids = fields.One2many(
        "service.desk.support.contract",
        "partner_id",
        string="Support Contracts",
    )
    sd_contract_count = fields.Integer(compute="_compute_sd_contract_count")
    sd_rating_avg = fields.Float(compute="_compute_sd_rating_avg", digits=(3, 2))

    def _compute_sd_hour_package_count(self):
        package_data = self.env["service.desk.customer.hour.package"]._read_group(
            [("partner_id", "in", self.ids)],
            ["partner_id"],
            ["__count"],
        )
        counts = {partner.id: count for partner, count in package_data}
        for partner in self:
            partner.sd_hour_package_count = counts.get(partner.id, 0)

    def _compute_sd_contract_count(self):
        for partner in self:
            partner.sd_contract_count = len(partner.sd_support_contract_ids)

    def _compute_sd_rating_avg(self):
        Rating = self.env["service.desk.ticket.rating"]
        for partner in self:
            ratings = Rating.search([("partner_id", "=", partner.id)])
            if ratings:
                partner.sd_rating_avg = sum(int(r.rating) for r in ratings) / len(ratings)
            else:
                partner.sd_rating_avg = 0.0

    def _compute_sd_ticket_count(self):
        ticket_data = self.env["service.desk.ticket"]._read_group(
            [("partner_id", "in", self.ids)],
            ["partner_id"],
            ["__count"],
        )
        counts = {partner.id: count for partner, count in ticket_data}
        for partner in self:
            partner.sd_ticket_count = counts.get(partner.id, 0)

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        partners._sd_sync_hour_packages()
        return partners

    def write(self, vals):
        res = super().write(vals)
        if "sd_allocated_hours_for_month" in vals:
            self._sd_sync_hour_packages()
        return res

    def _sd_sync_hour_packages(self):
        HourPackage = self.env["service.desk.customer.hour.package"]
        to_ensure = self.filtered(lambda partner: partner.sd_allocated_hours_for_month > 0)
        if to_ensure:
            HourPackage._ensure_open_hour_package_for_partners(to_ensure)

    def action_view_service_desk_tickets(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Service Desk Tickets",
            "res_model": "service.desk.ticket",
            "view_mode": "kanban,list,form",
            "domain": [("partner_id", "=", self.id)],
            "context": {"default_partner_id": self.id},
        }

    def action_view_hour_packages(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Hour Packages",
            "res_model": "service.desk.customer.hour.package",
            "view_mode": "list,form",
            "domain": [("partner_id", "=", self.id)],
            "context": {"default_partner_id": self.id},
        }
