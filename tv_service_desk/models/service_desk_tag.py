from odoo import fields, models
from random import randint


class ServiceDeskTag(models.Model):
    _name = "service.desk.tag"
    _description = "Service Desk Tag"
    _order = "name"

    def _default_color(self):
        return randint(1, 11)

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company")
    color = fields.Integer(default=_default_color)
