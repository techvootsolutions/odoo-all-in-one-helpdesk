from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ServiceDeskCustomFieldWizard(models.TransientModel):
    _name = "service.desk.custom.field.wizard"
    _description = "Create Custom Field on Helpdesk Ticket"

    ticket_id = fields.Many2one("service.desk.ticket")
    technical_name = fields.Char(string="Technical Field Name", required=True)
    label = fields.Char(string="Label", required=True)
    field_type = fields.Selection(
        [
            ("char", "char"),
            ("text", "text"),
            ("integer", "integer"),
            ("float", "float"),
            ("boolean", "boolean"),
            ("date", "date"),
            ("datetime", "datetime"),
            ("selection", "selection"),
        ],
        string="Type",
        default="char",
        required=True,
    )
    widget = fields.Char(string="Widget")
    tab_anchor = fields.Selection(
        selection="_selection_anchor_tabs",
        string="Tab List",
    )
    anchor_field = fields.Selection(
        selection="_selection_anchor_fields",
        string="Position Field",
        default="replied_status",
        required=True,
    )
    position = fields.Selection(
        [("after", "After"), ("before", "Before")],
        string="Position",
        default="after",
        required=True,
    )
    help_text = fields.Text(string="Help")
    is_required = fields.Boolean(string="Required")
    is_copied = fields.Boolean(string="Copied")
    tracking = fields.Boolean(string="Tracking")
    selection_options = fields.Text(
        string="Selection Options",
        help="One option per line (for selection type).",
    )
    group_ids = fields.Many2many(
        "res.groups",
        string="Group Name",
        default=lambda self: self._default_group_ids(),
    )

    @api.model
    def _default_group_ids(self):
        group = self.env.ref("tv_service_desk.group_service_desk_custom", raise_if_not_found=False)
        return [(6, 0, group.ids)] if group else []

    @api.model
    def _selection_anchor_tabs(self):
        return [
            ("description", "Description"),
            ("attachments", "Attachments"),
            ("timesheets", "Timesheets"),
            ("other_information", "Other Information"),
            ("stage_change_history", "Stage Change History"),
        ]

    @api.model
    def _selection_anchor_fields(self):
        return [
            ("replied_status", "Replied Status (Helpdesk Ticket)"),
            ("ticket_type_id", "Ticket Type (Helpdesk Ticket)"),
            ("team_id", "Team (Helpdesk Ticket)"),
            ("partner_id", "Partner (Helpdesk Ticket)"),
            ("subject", "Subject (Helpdesk Ticket)"),
            ("priority_id", "Priority (Helpdesk Ticket)"),
        ]

    @api.constrains("technical_name")
    def _check_technical_name(self):
        for wizard in self:
            name = wizard.technical_name or ""
            if not name.startswith("x_"):
                raise ValidationError(_("Technical field name must start with x_."))
            if not name.replace("_", "").isalnum():
                raise ValidationError(
                    _("Technical name must be alphanumeric with underscores only.")
                )

    def action_create_field(self):
        self.ensure_one()
        if self.env["service.desk.form.field"].search([
            ("technical_name", "=", self.technical_name),
        ], limit=1):
            raise ValidationError(_("A custom field with this technical name already exists."))
        field = self.env["service.desk.form.field"].create({
            "name": self.label,
            "technical_name": self.technical_name,
            "field_type": self.field_type,
            "selection_options": self.selection_options,
            "is_required": self.is_required,
            "anchor_field": self.anchor_field,
            "position": self.position,
            "tab_anchor": self.tab_anchor or False,
            "group_ids": [(6, 0, self.group_ids.ids)],
        })
        field._create_form_view_inherit(widget=self.widget or None)
        model_field = self.env["ir.model.fields"].search([
            ("model", "=", "service.desk.ticket"),
            ("name", "=", self.technical_name),
        ], limit=1)
        if model_field:
            write_vals = {
                "copied": self.is_copied,
                "help": self.help_text or False,
            }
            if "tracking" in model_field._fields:
                write_vals["tracking"] = self.tracking
            model_field.sudo().write(write_vals)
        return {"type": "ir.actions.client", "tag": "reload"}
