from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ServiceDeskMergeWizard(models.TransientModel):
    _name = "service.desk.merge.wizard"
    _description = "Merge Service Desk Tickets"

    ticket_ids = fields.Many2many(
        "service.desk.ticket",
        "service_desk_merge_wizard_ticket_rel",
        "wizard_id",
        "ticket_id",
        string="Tickets",
        required=True,
    )
    team_id = fields.Many2one("service.desk.team", string="Team")
    team_head_id = fields.Many2one("res.users", string="Team Head")
    user_id = fields.Many2one("res.users", string="Assigned User")
    ticket_type_id = fields.Many2one("service.desk.ticket.type", string="Ticket Type")
    priority_id = fields.Many2one("service.desk.priority", string="Priority")
    assigned_user_ids = fields.Many2many(
        "res.users",
        "service_desk_merge_wizard_assigned_user_rel",
        "wizard_id",
        "user_id",
        string="Assign Multi Users",
    )
    partner_id = fields.Many2one("res.partner", string="Partner", required=True)
    alarm_ids = fields.Many2many(
        "service.desk.alarm",
        "service_desk_merge_wizard_alarm_rel",
        "wizard_id",
        "alarm_id",
        string="Ticket Reminder",
    )
    subject = fields.Char(string="Subject", required=True)
    tag_ids = fields.Many2many("service.desk.tag", string="Tags")
    merge_history = fields.Boolean(string="Merge History", default=True)
    merge_target_type = fields.Selection(
        [("new", "New"), ("existing", "Existing")],
        string="Type",
        default="new",
        required=True,
    )
    target_ticket_id = fields.Many2one(
        "service.desk.ticket",
        string="Existing Ticket",
        domain="[('id', 'in', ticket_ids)]",
    )
    merge_type = fields.Selection(
        [
            ("close", "Close other Tickets"),
            ("cancel", "Cancel other Tickets"),
            ("done", "Done other Tickets"),
            ("remove", "Remove other Tickets"),
            ("nothing", "Do Nothing"),
        ],
        string="Merge Type",
        default="close",
        required=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get("active_ids", [])
        tickets = self.env["service.desk.ticket"].browse(active_ids)
        if len(tickets) < 2:
            raise UserError(_("Select at least two tickets to merge."))
        partners = tickets.mapped("partner_id")
        if len(partners) > 1:
            raise UserError(_("Partners must be the same."))
        primary = tickets[0]
        all_assigned = tickets.mapped("assigned_user_ids") | tickets.mapped("user_id")
        all_tags = tickets.mapped("tag_ids")
        all_alarms = tickets.mapped("alarm_ids")
        res.update({
            "ticket_ids": [(6, 0, tickets.ids)],
            "subject": primary.subject,
            "partner_id": partners.id,
            "team_id": primary.team_id.id,
            "team_head_id": primary.team_head_id.id,
            "user_id": primary.user_id.id,
            "ticket_type_id": primary.ticket_type_id.id,
            "priority_id": primary.priority_id.id,
            "assigned_user_ids": [(6, 0, all_assigned.ids)],
            "alarm_ids": [(6, 0, all_alarms.ids)],
            "tag_ids": [(6, 0, all_tags.ids)],
            "target_ticket_id": primary.id,
        })
        return res

    def _get_stage_for_merge_type(self):
        icp = self.env["ir.config_parameter"].sudo()
        if self.merge_type == "close":
            stage_id = int(icp.get_param("tv_service_desk.stage_closed_id", 0) or 0)
            stage = self.env["service.desk.stage"].browse(stage_id).exists()
            if not stage:
                stage = self.env["service.desk.stage"].search([("name", "=", "Closed")], limit=1)
            return stage
        if self.merge_type == "cancel":
            stage_id = int(icp.get_param("tv_service_desk.stage_cancel_id", 0) or 0)
            stage = self.env["service.desk.stage"].browse(stage_id).exists()
            if not stage:
                stage = self.env["service.desk.stage"].search([("name", "=", "Cancelled")], limit=1)
            return stage
        if self.merge_type == "done":
            stage_id = int(icp.get_param("tv_service_desk.stage_resolved_id", 0) or 0)
            stage = self.env["service.desk.stage"].browse(stage_id).exists()
            if not stage:
                stage = self.env["service.desk.stage"].search([("name", "=", "Done")], limit=1)
            return stage
        return False

    def action_merge(self):
        self.ensure_one()
        if self.merge_target_type == "existing":
            if not self.target_ticket_id:
                raise UserError(_("Select an existing ticket to merge into."))
            merged = self.target_ticket_id
            self._update_merged_ticket(merged)
        else:
            merged = self.env["service.desk.ticket"].create(self._prepare_merged_ticket_vals())
        self._merge_chatter_history(merged)
        self._apply_merge_type(merged)
        merged.message_post(
            body=_("Created by merging tickets: %s") % ", ".join(self.ticket_ids.mapped("name")),
            message_type="notification",
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "service.desk.ticket",
            "view_mode": "form",
            "res_id": merged.id,
        }

    def _prepare_merged_ticket_vals(self):
        self.ensure_one()
        descriptions = [
            ticket.description for ticket in self.ticket_ids if ticket.description
        ]
        return {
            "subject": self.subject,
            "description": "<hr/>".join(descriptions) if descriptions else False,
            "partner_id": self.partner_id.id,
            "team_id": self.team_id.id,
            "team_head_id": self.team_head_id.id,
            "user_id": self.user_id.id,
            "ticket_type_id": self.ticket_type_id.id,
            "priority_id": self.priority_id.id,
            "assigned_user_ids": [(6, 0, self.assigned_user_ids.ids)],
            "alarm_ids": [(6, 0, self.alarm_ids.ids)],
            "tag_ids": [(6, 0, self.tag_ids.ids)],
            "stage_id": self.ticket_ids[:1].stage_id.id,
        }

    def _update_merged_ticket(self, merged):
        self.ensure_one()
        merged.write({
            "subject": self.subject,
            "team_id": self.team_id.id,
            "team_head_id": self.team_head_id.id,
            "user_id": self.user_id.id,
            "ticket_type_id": self.ticket_type_id.id,
            "priority_id": self.priority_id.id,
            "assigned_user_ids": [(6, 0, self.assigned_user_ids.ids)],
            "alarm_ids": [(6, 0, self.alarm_ids.ids)],
            "tag_ids": [(6, 0, self.tag_ids.ids)],
        })

    def _merge_chatter_history(self, merged):
        if not self.merge_history:
            return
        for ticket in self.ticket_ids.filtered(lambda t: t.id != merged.id):
            for message in ticket.message_ids.sorted("date"):
                message.copy({"res_id": merged.id})

    def _apply_merge_type(self, merged):
        others = self.ticket_ids.filtered(lambda t: t.id != merged.id)
        if not others or self.merge_type == "nothing":
            return
        if self.merge_type == "remove":
            others.unlink()
            return
        stage = self._get_stage_for_merge_type()
        if not stage:
            raise UserError(_("No stage configured for the selected merge type."))
        for ticket in others:
            ticket.message_post(
                body=_("Merged into ticket %s") % merged.display_name,
                message_type="notification",
            )
            ticket.stage_id = stage
