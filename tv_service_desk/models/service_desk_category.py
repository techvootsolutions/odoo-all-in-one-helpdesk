from odoo import fields, models


class ServiceDeskCategory(models.Model):
    _name = "service.desk.category"
    _description = "Service Desk Category"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company")
    parent_id = fields.Many2one("service.desk.category", string="Parent Category")
    child_ids = fields.One2many("service.desk.category", "parent_id", string="Subcategories")
    description = fields.Text()
