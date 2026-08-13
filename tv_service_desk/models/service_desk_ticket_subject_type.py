from odoo import fields, models


class ServiceDeskTicketSubjectType(models.Model):
    _name = "service.desk.ticket.subject.type"
    _description = "Ticket Subject Type"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
