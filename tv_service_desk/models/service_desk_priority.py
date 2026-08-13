from odoo import fields, models


class ServiceDeskPriority(models.Model):
    _name = "service.desk.priority"
    _description = "Service Desk Priority"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company")
    color = fields.Integer()
    weight = fields.Integer(
        default=1,
        help="Higher weight means higher urgency for SLA sorting.",
    )
