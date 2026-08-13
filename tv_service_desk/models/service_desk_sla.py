from datetime import timedelta

from odoo import _, api, fields, models


class ServiceDeskSlaPolicy(models.Model):
    _name = "service.desk.sla.policy"
    _description = "Service Desk SLA Policy"
    _order = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company")
    description = fields.Text()
    team_id = fields.Many2one("service.desk.team", string="Helpdesk Team")
    sla_target_type = fields.Selection(
        [("reaching_stage", "Reaching Stage")],
        string="SLA Target Type",
        default="reaching_stage",
        required=True,
    )
    sla_days = fields.Integer(
        string="Days",
        compute="_compute_duration_fields",
        inverse="_inverse_duration_fields",
        store=True,
        readonly=False,
    )
    sla_hours = fields.Integer(
        string="Hours",
        compute="_compute_duration_fields",
        inverse="_inverse_duration_fields",
        store=True,
        readonly=False,
    )
    sla_minutes = fields.Integer(
        string="Minutes",
        compute="_compute_duration_fields",
        inverse="_inverse_duration_fields",
        store=True,
        readonly=False,
    )
    target_stage_id = fields.Many2one(
        "service.desk.stage",
        string="Target Stage",
        required=True,
        help="Ticket should reach this stage before the deadline.",
    )
    time_hours = fields.Float(
        string="Resolution Time (Hours)",
        compute="_compute_time_hours",
        store=True,
        readonly=False,
    )
    first_response_hours = fields.Float(
        string="First Response Time (Hours)",
        help="Maximum hours for the first staff reply.",
    )
    priority_id = fields.Many2one("service.desk.priority")
    ticket_type_id = fields.Many2one("service.desk.ticket.type")
    category_id = fields.Many2one("service.desk.category", string="Category")
    partner_category_id = fields.Many2one(
        "res.partner.category",
        string="Customer Tag",
    )
    customer_type = fields.Selection(
        [
            ("all", "All Customers"),
            ("company", "Companies"),
            ("individual", "Individuals"),
        ],
        default="all",
        string="Customer Type",
    )
    contract_required = fields.Boolean(
        string="Requires Support Contract",
        help="Apply only when the ticket is linked to an active support contract.",
    )
    team_ids = fields.Many2many(
        "service.desk.team",
        "service_desk_team_sla_rel",
        "policy_id",
        "team_id",
        string="Teams",
    )
    ticket_count = fields.Integer(compute="_compute_ticket_count")

    @api.depends("time_hours")
    def _compute_duration_fields(self):
        for policy in self:
            hours = policy.time_hours or 0.0
            policy.sla_days = int(hours // 24)
            policy.sla_hours = int(hours % 24)
            policy.sla_minutes = int(round((hours % 1) * 60))

    def _inverse_duration_fields(self):
        for policy in self:
            policy.time_hours = (policy.sla_days * 24.0) + policy.sla_hours + (policy.sla_minutes / 60.0)

    @api.depends("sla_days", "sla_hours", "sla_minutes")
    def _compute_time_hours(self):
        for policy in self:
            policy.time_hours = (policy.sla_days * 24.0) + policy.sla_hours + (policy.sla_minutes / 60.0)

    @api.depends()
    def _compute_ticket_count(self):
        for policy in self:
            policy.ticket_count = self.env["service.desk.ticket"].search_count([
                ("sla_policy_id", "=", policy.id),
            ])

    def _compute_deadline(self, ticket, start_dt=None):
        """Return SLA deadline datetime for a ticket."""
        self.ensure_one()
        start_dt = start_dt or ticket.create_date or fields.Datetime.now()
        calendar = ticket.team_id.working_calendar_id
        if calendar:
            return calendar.plan_hours(self.time_hours, start_dt, compute_leaves=True)
        return start_dt + timedelta(hours=self.time_hours)

    def _compute_first_response_deadline(self, ticket, start_dt=None):
        self.ensure_one()
        if not self.first_response_hours:
            return False
        start_dt = start_dt or ticket.create_date or fields.Datetime.now()
        calendar = ticket.team_id.working_calendar_id
        if calendar:
            return calendar.plan_hours(self.first_response_hours, start_dt, compute_leaves=True)
        return start_dt + timedelta(hours=self.first_response_hours)

    def matches_ticket(self, ticket):
        self.ensure_one()
        if self.team_id and ticket.team_id != self.team_id:
            return False
        if not self.team_id and self.team_ids and ticket.team_id not in self.team_ids:
            return False
        if self.priority_id and ticket.priority_id != self.priority_id:
            return False
        if self.ticket_type_id and ticket.ticket_type_id != self.ticket_type_id:
            return False
        if self.category_id and ticket.category_id != self.category_id:
            return False
        if self.partner_category_id and self.partner_category_id not in ticket.partner_id.category_id:
            return False
        if self.customer_type == "company" and not ticket.partner_id.is_company:
            return False
        if self.customer_type == "individual" and ticket.partner_id.is_company:
            return False
        if self.contract_required and (
            not ticket.support_contract_id or ticket.support_contract_id.state != "active"
        ):
            return False
        return True

    def action_view_tickets(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "SLA Tickets",
            "res_model": "service.desk.ticket",
            "view_mode": "list,form,kanban",
            "domain": [("sla_policy_id", "=", self.id)],
        }
