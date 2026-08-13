# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ServiceDeskAlarm(models.Model):
    _name = "service.desk.alarm"
    _description = "Helpdesk Ticket Alarm"
    _rec_name = "name"
    _order = "id desc"

    name = fields.Char(string="Name", compute="_compute_name", store=True)
    reminder_before = fields.Integer(string="Reminder Before", required=True, default=5)
    reminder_unit = fields.Selection([
        ("minute", "Minute(s)"),
        ("hour", "Hour(s)"),
        ("day", "Day(s)"),
    ], string="Reminder Unit", required=True, default="minute")
    type = fields.Selection([
        ("email", "Email"),
        ("popup", "Popup"),
    ], string="Type", required=True, default="email")

    @api.depends("reminder_before", "reminder_unit", "type")
    def _compute_name(self):
        unit_labels = {
            "minute": "Minute(s)",
            "hour": "Hour(s)",
            "day": "Day(s)",
        }
        for record in self:
            unit = unit_labels.get(record.reminder_unit, "")
            record.name = f"{record.reminder_before} {unit} [{record.type}]"
