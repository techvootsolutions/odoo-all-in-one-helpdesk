from odoo import fields, models


class ServiceDeskCreateTaskWizard(models.TransientModel):
    _name = "service.desk.create.task.wizard"
    _description = "Create Project Task from Ticket"

    ticket_id = fields.Many2one("service.desk.ticket", required=True)
    name = fields.Char(required=True)
    project_id = fields.Many2one("project.project", required=True)
    user_ids = fields.Many2many("res.users", string="Assignees")
    description = fields.Html()

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ticket = self.env["service.desk.ticket"].browse(
            self.env.context.get("default_ticket_id")
        )
        if ticket:
            res.update({
                "name": ticket.name,
                "description": ticket.description,
            })
            project_id = int(self.env["ir.config_parameter"].sudo().get_param(
                "tv_service_desk.default_timesheet_project_id", 0
            ))
            if project_id:
                res["project_id"] = project_id
        return res

    def action_create(self):
        self.ensure_one()
        task = self.env["project.task"].create({
            "name": self.name,
            "project_id": self.project_id.id,
            "user_ids": [(6, 0, self.user_ids.ids)],
            "description": self.description,
            "sd_ticket_id": self.ticket_id.id,
            "partner_id": self.ticket_id.partner_id.id,
        })
        task._copy_service_desk_ticket_attachments(self.ticket_id)
        return {
            "type": "ir.actions.act_window",
            "res_model": "project.task",
            "view_mode": "form",
            "res_id": task.id,
        }
