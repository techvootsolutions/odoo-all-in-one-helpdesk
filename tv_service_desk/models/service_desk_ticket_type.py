from odoo import fields, models


class ServiceDeskTicketType(models.Model):
    _name = "service.desk.ticket.type"
    _description = "Service Desk Ticket Type"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company")
    description = fields.Text()
    sla_policy_ids = fields.Many2many(
        "service.desk.sla.policy",
        "service_desk_type_sla_rel",
        "type_id",
        "policy_id",
        string="SLA Policies",
    )
    follow_up = fields.Boolean(string="Follow-up?")
    auto_followup_trigger = fields.Boolean(string="Auto Follow-up trigger?")
    followup_template_id = fields.Many2one(
        "service.desk.auto.followup",
        string="Followup Template",
    )
    sla_count = fields.Integer(compute="_compute_sla_count")

    def _compute_sla_count(self):
        for type_rec in self:
            type_rec.sla_count = self.env["service.desk.sla.policy"].search_count([
                ("ticket_type_id", "=", type_rec.id),
            ])

    def action_view_sla_policies(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Helpdesk SLA",
            "res_model": "service.desk.sla.policy",
            "view_mode": "list,form",
            "domain": [("ticket_type_id", "=", self.id)],
        }
