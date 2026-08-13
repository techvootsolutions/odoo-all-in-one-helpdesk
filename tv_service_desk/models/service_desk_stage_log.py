from odoo import fields, models


class ServiceDeskStageLog(models.Model):
    _name = "service.desk.stage.log"
    _description = "Service Desk Stage Change History"
    _order = "change_date desc, id desc"

    ticket_id = fields.Many2one(
        "service.desk.ticket",
        required=True,
        ondelete="cascade",
    )
    old_stage_id = fields.Many2one(
        "service.desk.stage",
        string="Previous Stage",
        ondelete="set null",
    )
    new_stage_id = fields.Many2one("service.desk.stage", string="New Stage", required=True)
    user_id = fields.Many2one("res.users", string="Changed By", default=lambda self: self.env.user)
    change_date = fields.Datetime(default=fields.Datetime.now, required=True)
    duration_hours = fields.Float(
        string="Hours in Previous Stage",
        help="Time spent in the previous stage before this change.",
    )
