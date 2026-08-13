from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ServiceDeskMassUpdateWizard(models.TransientModel):
    _name = "service.desk.mass.update.wizard"
    _description = "Mass Update Service Desk Tickets"

    ticket_ids = fields.Many2many("service.desk.ticket", required=True)
    update_team = fields.Boolean(string="Team")
    team_id = fields.Many2one("service.desk.team", string="Team")
    update_assign_to = fields.Boolean(string="Assign To")
    user_id = fields.Many2one("res.users", string="Assign To")
    update_assign_multi = fields.Boolean(string="Assign Multi User")
    multi_user_action = fields.Selection(
        [
            ("add", "Add"),
            ("replace", "Replace"),
        ],
        string="Ticket Type Update",
        default="add",
    )
    assigned_user_ids = fields.Many2many(
        "res.users",
        "service_desk_mass_update_user_rel",
        "wizard_id",
        "user_id",
        string="Assign Multi Users",
    )
    update_stage = fields.Boolean(string="Stage")
    stage_id = fields.Many2one("service.desk.stage", string="Stages")
    update_follower = fields.Boolean(string="Add/Remove")
    follower_partner_ids = fields.Many2many(
        "res.partner",
        "service_desk_mass_update_follower_rel",
        "wizard_id",
        "partner_id",
        string="Followers",
    )
    follower_action = fields.Selection(
        [
            ("add", "Add"),
            ("remove", "Remove"),
        ],
        string="Ticket Type Update",
        default="add",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if not self.env.user.sd_allow_mass_update:
            raise UserError(_("You are not allowed to perform mass ticket updates."))
        res["ticket_ids"] = [(6, 0, self.env.context.get("active_ids", []))]
        return res

    def action_apply(self):
        self.ensure_one()
        if not self.ticket_ids:
            raise UserError(_("No tickets selected."))
        if not any(
            (
                self.update_team,
                self.update_assign_to,
                self.update_assign_multi,
                self.update_stage,
                self.update_follower,
            )
        ):
            raise UserError(_("Select at least one field to update."))
        if self.update_team and not self.team_id:
            raise UserError(_("Select a team to update."))
        if self.update_assign_to and not self.user_id:
            raise UserError(_("Select a user to assign."))
        if self.update_assign_multi and not self.assigned_user_ids:
            raise UserError(_("Select users for multi-user assignment."))
        if self.update_stage and not self.stage_id:
            raise UserError(_("Select a stage to update."))
        if self.update_follower and not self.follower_partner_ids:
            raise UserError(_("Select followers to add or remove."))

        for ticket in self.ticket_ids:
            vals = {}
            if self.update_team:
                vals["team_id"] = self.team_id.id
            if self.update_assign_to:
                vals["user_id"] = self.user_id.id
            if self.update_stage:
                vals["stage_id"] = self.stage_id.id
            if vals:
                ticket.write(vals)

            if self.update_assign_multi:
                if self.multi_user_action == "replace":
                    ticket.assigned_user_ids = [(6, 0, self.assigned_user_ids.ids)]
                else:
                    ticket.assigned_user_ids = [
                        (4, user.id) for user in self.assigned_user_ids
                    ]

            if self.update_follower:
                partner_ids = self.follower_partner_ids.ids
                if self.follower_action == "remove":
                    ticket.message_unsubscribe(partner_ids=partner_ids)
                else:
                    ticket.message_subscribe(partner_ids=partner_ids)

        return {"type": "ir.actions.act_window_close"}
