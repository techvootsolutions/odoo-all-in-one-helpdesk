from odoo import api, fields, models


class ProjectTask(models.Model):
    _inherit = "project.task"

    sd_ticket_id = fields.Many2one(
        "service.desk.ticket", string="Service Desk Ticket", ondelete="set null"
    )
    sd_ticket_count = fields.Integer(compute="_compute_sd_ticket_count")

    @api.depends("sd_ticket_id")
    def _compute_sd_ticket_count(self):
        for task in self:
            task.sd_ticket_count = 1 if task.sd_ticket_id else 0

    @api.model_create_multi
    def create(self, vals_list):
        tasks = super().create(vals_list)
        ticket_id = self.env.context.get("sd_link_ticket_id")
        copy_attachments = self.env.context.get("sd_copy_ticket_attachments")
        if ticket_id:
            ticket = self.env["service.desk.ticket"].browse(int(ticket_id)).exists()
            if ticket:
                for task in tasks:
                    if not task.sd_ticket_id:
                        task.sd_ticket_id = ticket.id
                    if copy_attachments:
                        task._copy_service_desk_ticket_attachments(ticket)
        return tasks

    def _copy_service_desk_ticket_attachments(self, ticket):
        self.ensure_one()
        Attachment = self.env["ir.attachment"]
        attachments = Attachment.search([
            ("res_model", "=", "service.desk.ticket"),
            ("res_id", "=", ticket.id),
        ])
        for attachment in attachments:
            attachment.copy({"res_model": "project.task", "res_id": self.id})
        for message in ticket.message_ids:
            for attachment in message.attachment_ids:
                attachment.copy({"res_model": "project.task", "res_id": self.id})

    def action_view_service_desk_tickets(self):
        self.ensure_one()
        if not self.sd_ticket_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": "Helpdesk Tickets",
            "res_model": "service.desk.ticket",
            "view_mode": "kanban,list,form",
            "domain": [("id", "=", self.sd_ticket_id.id)],
            "context": {"create": False},
        }
