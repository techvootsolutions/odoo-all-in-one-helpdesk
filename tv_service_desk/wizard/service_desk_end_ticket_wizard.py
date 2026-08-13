from odoo import api, fields, models


class ServiceDeskEndTicketWizard(models.TransientModel):
    _name = "service.desk.end.ticket.wizard"
    _description = "End Helpdesk Ticket Timer"

    ticket_id = fields.Many2one("service.desk.ticket", required=True, ondelete="cascade")
    timesheet_line_id = fields.Many2one("account.analytic.line", required=True, ondelete="cascade")
    name = fields.Char(string="Description")
    project_id = fields.Many2one("project.project", string="Project")
    hour_package_id = fields.Many2one(
        "service.desk.customer.hour.package",
        string="Customer Hour Package",
        domain="[('partner_id', 'child_of', partner_id), ('state', '=', 'open')]",
    )
    partner_id = fields.Many2one(related="ticket_id.partner_id")
    start_date = fields.Datetime(string="Start Date")
    end_date = fields.Datetime(string="End Date", default=fields.Datetime.now)
    duration = fields.Float(string="Duration (HH:MM)")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ticket = self.env["service.desk.ticket"].browse(
            self.env.context.get("default_ticket_id")
        ).exists()
        line = self.env["account.analytic.line"].browse(
            self.env.context.get("default_timesheet_line_id")
        ).exists()
        if ticket:
            res["name"] = ticket._get_default_timesheet_description()
        if line:
            end = fields.Datetime.now()
            res.update({
                "start_date": line.start_date,
                "end_date": end,
                "project_id": line.project_id.id,
            })
            if line.start_date:
                res["duration"] = (end - line.start_date).total_seconds() / 3600.0
        if ticket and ticket.partner_id:
            package = self.env["service.desk.customer.hour.package"]._get_open_package(
                ticket.partner_id
            )
            if package:
                res["hour_package_id"] = package.id
        return res

    @api.onchange("project_id")
    def _onchange_project_id_hour_package(self):
        if self.ticket_id and self.ticket_id.partner_id:
            package = self.env["service.desk.customer.hour.package"]._get_open_package(
                self.ticket_id.partner_id
            )
            self.hour_package_id = package

    @api.onchange("start_date", "end_date")
    def _onchange_start_end_date(self):
        if self.start_date and self.end_date:
            self.duration = (self.end_date - self.start_date).total_seconds() / 3600.0

    def action_end_ticket(self):
        self.ensure_one()
        duration_hours = self.duration
        if self.start_date and self.end_date:
            duration_hours = (self.end_date - self.start_date).total_seconds() / 3600.0
        self.timesheet_line_id.write({
            "name": self.name,
            "project_id": self.project_id.id,
            "sd_hour_package_id": self.hour_package_id.id,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "unit_amount": round(duration_hours, 2),
        })
        ticket = self.ticket_id
        if ticket.timer_user_id == self.env.user:
            ticket.write({"timer_user_id": False, "timer_start": False})
        return {"type": "ir.actions.act_window_close"}
