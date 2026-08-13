from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ServiceDeskCustomTabWizard(models.TransientModel):
    _name = "service.desk.custom.tab.wizard"
    _description = "Add Custom Tab to Helpdesk Ticket"

    name = fields.Char(string="Name", required=True, help="Technical tab name (e.g. extra_tab)")
    label = fields.Char(string="Label", required=True, help="Tab label shown on the ticket form")
    group_ids = fields.Many2many(
        "res.groups",
        string="Groups",
        default=lambda self: self._default_group_ids(),
    )
    anchor_tab = fields.Selection(
        selection="_selection_anchor_tabs",
        string="Tab List",
        required=True,
        default="stage_change_history",
    )
    position = fields.Selection(
        [("after", "After"), ("before", "Before")],
        string="Position",
        default="after",
        required=True,
    )

    @api.model
    def _default_group_ids(self):
        # Empty = tab visible to all internal users on the ticket form.
        return []

    @api.model
    def _selection_anchor_tabs(self):
        return [
            ("description", "Description"),
            ("attachments", "Attachments"),
            ("timesheets", "Timesheets"),
            ("followup_history", "Followup History"),
            ("other_information", "Other Information"),
            ("stage_change_history", "Stage Change History"),
        ]

    @api.constrains("name")
    def _check_name(self):
        for wizard in self:
            technical_name = (wizard.name or "").strip()
            if not technical_name or not technical_name.replace("_", "").isalnum():
                raise ValidationError(
                    _("Tab name must be alphanumeric with underscores only (e.g. extra_tab).")
                )

    def action_create_tab(self):
        self.ensure_one()
        technical_name = self.name.strip()
        existing = self.env["service.desk.form.tab"].search([
            ("technical_name", "=", technical_name),
        ], limit=1)
        if existing:
            existing.write({
                "name": self.label,
                "anchor_tab": self.anchor_tab,
                "position": self.position,
                "group_ids": [(6, 0, self.group_ids.ids)],
            })
            existing._create_form_view_inherit()
            return {"type": "ir.actions.client", "tag": "reload"}
        tab = self.env["service.desk.form.tab"].create({
            "name": self.label,
            "technical_name": technical_name,
            "anchor_tab": self.anchor_tab,
            "position": self.position,
            "group_ids": [(6, 0, self.group_ids.ids)],
        })
        tab._create_form_view_inherit()
        return {"type": "ir.actions.client", "tag": "reload"}
