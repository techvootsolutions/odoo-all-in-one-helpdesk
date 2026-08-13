from odoo import fields, models


class ServiceDeskTeamSkillLine(models.Model):
    _name = "service.desk.team.skill"
    _description = "Team Member Skill Mapping"
    _order = "team_id, user_id"

    team_id = fields.Many2one("service.desk.team", required=True, ondelete="cascade")
    user_id = fields.Many2one("res.users", required=True, ondelete="cascade")
    category_ids = fields.Many2many(
        "service.desk.category",
        "service_desk_team_skill_category_rel",
        "skill_id",
        "category_id",
        string="Categories",
    )
    ticket_type_ids = fields.Many2many(
        "service.desk.ticket.type",
        "service_desk_team_skill_type_rel",
        "skill_id",
        "type_id",
        string="Ticket Types",
    )
