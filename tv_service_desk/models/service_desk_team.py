from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval


class ServiceDeskTeam(models.Model):
    _name = "service.desk.team"
    _description = "Service Desk Team"
    _inherit = ["mail.alias.mixin", "mail.thread"]
    _order = "sequence, name"

    name = fields.Char(required=True, tracking=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    leader_id = fields.Many2one("res.users", string="Team Head", tracking=True)
    auto_assign_user = fields.Boolean(string="Auto Assign User", default=False)
    auto_assign_method = fields.Selection(
        [
            ("equal_open", "Each user has an equal number of open tickets"),
            ("custom_filter", "Assign by Custom Filters"),
        ],
        string="Method",
        default="equal_open",
    )
    auto_assign_domain = fields.Char(
        string="Filters",
        default="[]",
        help="Domain used to count open tickets per team member when assigning by custom filters.",
    )
    member_ids = fields.Many2many(
        "res.users",
        "service_desk_team_member_rel",
        "team_id",
        "user_id",
        string="Members",
    )
    color = fields.Integer(string="Color Index")
    is_default = fields.Boolean(string="Default Team")
    description = fields.Html()
    ticket_count = fields.Integer(compute="_compute_ticket_count")
    email = fields.Char(
        string="Email Alias",
        help="Contact or inbound email address for this team when no alias domain is configured.",
    )
    alias_domain_configured = fields.Boolean(
        compute="_compute_alias_domain_configured",
    )
    assignment_method = fields.Selection(
        [
            ("manual", "Manual"),
            ("round_robin", "Round Robin"),
            ("least_loaded", "Least Open Tickets"),
            ("skill_based", "Skill Based"),
        ],
        default="manual",
        required=True,
    )
    last_assignee_id = fields.Many2one(
        "res.users",
        string="Last Assigned User",
        help="Used for round-robin assignment rotation.",
    )
    skill_line_ids = fields.One2many(
        "service.desk.team.skill",
        "team_id",
        string="Skill Mapping",
    )
    open_stage_ids = fields.Many2many(
        "service.desk.stage",
        "service_desk_team_open_stage_rel",
        "team_id",
        "stage_id",
        string="Open Ticket Stages",
        help="Stages considered open when balancing workload.",
    )
    working_calendar_id = fields.Many2one(
        "resource.calendar",
        string="Working Schedule",
        help="Used for SLA deadline computation.",
    )
    sla_policy_ids = fields.Many2many(
        "service.desk.sla.policy",
        "service_desk_team_sla_rel",
        "team_id",
        "policy_id",
        string="SLA Policies",
    )
    sla_count = fields.Integer(compute="_compute_sla_count")

    @api.depends("company_id")
    def _compute_alias_domain_configured(self):
        configured = bool(self.env["mail.alias.domain"].sudo().search_count([]))
        for team in self:
            team.alias_domain_configured = configured

    def _compute_sla_count(self):
        for team in self:
            team.sla_count = self.env["service.desk.sla.policy"].search_count([
                ("team_id", "=", team.id),
            ])

    def action_view_sla_policies(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Helpdesk SLA",
            "res_model": "service.desk.sla.policy",
            "view_mode": "list,form",
            "domain": [("team_id", "=", self.id)],
        }

    @api.depends()
    def _compute_ticket_count(self):
        ticket_data = self.env["service.desk.ticket"]._read_group(
            [("team_id", "in", self.ids)],
            ["team_id"],
            ["__count"],
        )
        counts = {team.id: count for team, count in ticket_data}
        for team in self:
            team.ticket_count = counts.get(team.id, 0)

    def _alias_get_creation_values(self):
        values = super()._alias_get_creation_values()
        values["alias_model_id"] = self.env["ir.model"]._get("service.desk.ticket").id
        values["alias_defaults"] = {
            "team_id": self.id,
            "company_id": self.company_id.id,
        }
        return values

    @api.model_create_multi
    def create(self, vals_list):
        teams = super().create(vals_list)
        for team in teams:
            if team.is_default:
                self.search([
                    ("is_default", "=", True),
                    ("id", "!=", team.id),
                    ("company_id", "=", team.company_id.id),
                ]).write({"is_default": False})
        return teams

    def write(self, vals):
        res = super().write(vals)
        if vals.get("is_default"):
            for team in self.filtered("is_default"):
                self.search([
                    ("is_default", "=", True),
                    ("id", "!=", team.id),
                    ("company_id", "=", team.company_id.id),
                ]).write({"is_default": False})
        return res

    def action_view_tickets(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Tickets",
            "res_model": "service.desk.ticket",
            "view_mode": "kanban,list,form",
            "domain": [("team_id", "=", self.id)],
            "context": {"default_team_id": self.id},
        }

    def _get_skill_candidates(self, ticket):
        self.ensure_one()
        members = self.member_ids
        if not self.skill_line_ids:
            return members
        matched = self.env["res.users"]
        for line in self.skill_line_ids:
            if line.category_ids and ticket.category_id not in line.category_ids:
                continue
            if line.ticket_type_ids and ticket.ticket_type_id not in line.ticket_type_ids:
                continue
            matched |= line.user_id
        return matched or members

    def _get_open_ticket_counts(self, candidates):
        open_domain = [("team_id", "=", self.id), ("user_id", "in", candidates.ids)]
        if self.open_stage_ids:
            open_domain.append(("stage_id", "in", self.open_stage_ids.ids))
        else:
            open_domain.append(("stage_id.is_closed", "=", False))
        grouped = self.env["service.desk.ticket"]._read_group(
            open_domain,
            ["user_id"],
            ["__count"],
        )
        return {user.id: count for user, count in grouped if user}

    def _uses_auto_assign(self):
        self.ensure_one()
        return bool(
            self.auto_assign_user
            or self.assignment_method in ("round_robin", "least_loaded", "skill_based")
        )

    def _get_auto_assign_method(self):
        self.ensure_one()
        if self.auto_assign_user:
            return self.auto_assign_method
        if self.assignment_method == "least_loaded":
            return "equal_open"
        if self.assignment_method == "round_robin":
            return "round_robin"
        if self.assignment_method == "skill_based":
            return "skill_based"
        return False

    def _get_custom_filter_ticket_counts(self, candidates):
        self.ensure_one()
        try:
            base_domain = safe_eval(self.auto_assign_domain or "[]")
        except (ValueError, SyntaxError):
            base_domain = []
        if not isinstance(base_domain, list):
            base_domain = []
        Ticket = self.env["service.desk.ticket"]
        counts = {}
        for user in candidates:
            counts[user.id] = Ticket.search_count(base_domain + [("user_id", "=", user.id)])
        return counts

    def _get_next_assignee(self, partner=None, ticket=None):
        """Return a user id based on the team assignment strategy."""
        self.ensure_one()
        if not self._uses_auto_assign():
            return False

        method = self._get_auto_assign_method()
        candidates = self.member_ids
        if not candidates and self.leader_id:
            candidates = self.leader_id
        if ticket and method == "skill_based":
            candidates = self._get_skill_candidates(ticket)
        if not candidates:
            return False

        if method == "round_robin":
            ordered = candidates.sorted("id")
            if not self.last_assignee_id or self.last_assignee_id not in ordered:
                next_user = ordered[0]
            else:
                idx = list(ordered.ids).index(self.last_assignee_id.id)
                next_user = ordered[(idx + 1) % len(ordered)]
            self.sudo().write({"last_assignee_id": next_user.id})
            return next_user.id

        if method == "custom_filter":
            counts = self._get_custom_filter_ticket_counts(candidates)
            return min(candidates, key=lambda u: (counts.get(u.id, 0), u.id)).id

        counts = self._get_open_ticket_counts(candidates)
        return min(candidates, key=lambda u: (counts.get(u.id, 0), u.id)).id

    rating_avg = fields.Float(
        string="Average Rating",
        compute="_compute_rating_stats",
        digits=(3, 2),
    )
    rating_count = fields.Integer(compute="_compute_rating_stats")

    def _compute_rating_stats(self):
        Rating = self.env["service.desk.ticket.rating"]
        for team in self:
            ratings = Rating.search([("team_id", "=", team.id)])
            if ratings:
                team.rating_avg = sum(int(r.rating) for r in ratings) / len(ratings)
                team.rating_count = len(ratings)
            else:
                team.rating_avg = 0.0
                team.rating_count = 0
