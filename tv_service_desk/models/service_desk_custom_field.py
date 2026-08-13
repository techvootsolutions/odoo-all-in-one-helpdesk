from markupsafe import escape
import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


def _groups_attr_from_record(record):
    if not record.group_ids:
        return ""
    xmlids = []
    for group in record.group_ids:
        data = record.env["ir.model.data"].search([
            ("model", "=", "res.groups"),
            ("res_id", "=", group.id),
        ], limit=1)
        if data:
            xmlids.append("%s.%s" % (data.module, data.name))
    return (' groups="%s"' % ",".join(xmlids)) if xmlids else ""


def _ticket_form_view(env):
    return env.ref("tv_service_desk.view_service_desk_ticket_form")


def _build_tab_inherit_arch(tab):
    groups_attr = _groups_attr_from_record(tab)
    label = escape(tab.name or tab.technical_name)
    return (
        '<xpath expr="//page[@name=\'%s\']" position="%s">'
        '<page string="%s" name="%s"%s><group/></page>'
        "</xpath>"
    ) % (
        tab.anchor_tab,
        tab.position or "after",
        label,
        tab.technical_name,
        groups_attr,
    )


class ServiceDeskFormTab(models.Model):
    _name = "service.desk.form.tab"
    _description = "Service Desk Custom Form Tab"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    technical_name = fields.Char(
        help="Technical notebook page name used in the ticket form view.",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company")
    team_ids = fields.Many2many("service.desk.team", string="Teams")
    anchor_tab = fields.Char(string="Anchor Tab")
    position = fields.Selection(
        [("after", "After"), ("before", "Before")],
        default="after",
    )
    group_ids = fields.Many2many(
        "res.groups",
        string="Visible to Groups",
        help="Leave empty for all internal users.",
    )
    view_id = fields.Many2one("ir.ui.view", string="View Inherit", ondelete="set null")
    field_ids = fields.One2many("service.desk.form.field", "tab_id", string="Fields")

    def write(self, vals):
        res = super().write(vals)
        if any(key in vals for key in ("name", "technical_name", "anchor_tab", "position", "group_ids", "active")):
            for tab in self.filtered("view_id"):
                tab._create_form_view_inherit()
        return res

    @api.model
    def _sync_all_ticket_form_tab_views(self):
        for tab in self.with_context(active_test=False).search([]):
            tab._create_form_view_inherit()

    def _create_form_view_inherit(self):
        self.ensure_one()
        if not self.anchor_tab or str(self.anchor_tab).lower() == "false":
            if self.view_id:
                self.view_id.sudo().write({"active": False})
            return False
        arch = _build_tab_inherit_arch(self)
        view_vals = {
            "name": "service.desk.ticket.form.tab.%s" % self.technical_name,
            "model": "service.desk.ticket",
            "inherit_id": _ticket_form_view(self.env).id,
            "arch": arch,
            "mode": "extension",
            "active": True,
        }
        View = self.env["ir.ui.view"].sudo()
        if self.view_id:
            self.view_id.write({"arch": arch, "active": True})
            view = self.view_id
        else:
            view = View.create(view_vals)
            self.view_id = view.id
        self.env.registry.clear_cache()
        return view

    def unlink(self):
        views = self.mapped("view_id")
        res = super().unlink()
        views.sudo().unlink()
        self.env.registry.clear_cache()
        return res


class ServiceDeskFormField(models.Model):
    _name = "service.desk.form.field"
    _description = "Service Desk Custom Form Field"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    technical_name = fields.Char(
        required=True,
        help="Unique key used to store the value (letters, numbers, underscore).",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    tab_id = fields.Many2one("service.desk.form.tab", ondelete="cascade")
    field_type = fields.Selection(
        [
            ("char", "Text"),
            ("text", "Multiline Text"),
            ("integer", "Integer"),
            ("float", "Float"),
            ("boolean", "Checkbox"),
            ("date", "Date"),
            ("datetime", "Date & Time"),
            ("selection", "Selection"),
        ],
        default="char",
        required=True,
    )
    selection_options = fields.Text(
        help="One option per line (for Selection fields).",
    )
    is_required = fields.Boolean(string="Required")
    is_visible_portal = fields.Boolean(string="Visible on Portal")
    group_ids = fields.Many2many(
        "res.groups",
        string="Visible to Groups",
        help="Leave empty for all internal users.",
    )
    company_id = fields.Many2one("res.company")
    anchor_field = fields.Char(string="Anchor Field")
    position = fields.Selection(
        [("after", "After"), ("before", "Before")],
        default="after",
    )
    tab_anchor = fields.Char(string="Tab Anchor")
    view_id = fields.Many2one("ir.ui.view", string="View Inherit", ondelete="set null")

    @api.constrains("technical_name")
    def _check_technical_name(self):
        for field in self:
            if not field.technical_name.replace("_", "").isalnum():
                raise ValidationError(_("Technical name must be alphanumeric with underscores only."))

    def _register_on_ticket_model(self):
        self.ensure_one()
        if self.env["ir.model.fields"].search([
            ("model", "=", "service.desk.ticket"),
            ("name", "=", self.technical_name),
        ], limit=1):
            return
        ticket_model = self.env["ir.model"].search(
            [("model", "=", "service.desk.ticket")], limit=1
        )
        if not ticket_model:
            raise ValidationError(_("Helpdesk ticket model was not found."))
        field_vals = {
            "name": self.technical_name,
            "field_description": self.name,
            "model_id": ticket_model.id,
            "ttype": self.field_type,
            "required": self.is_required,
            "copied": True,
            "state": "manual",
        }
        if self.field_type == "selection" and self.selection_options:
            options = []
            for line in self.selection_options.splitlines():
                option = line.strip()
                if option:
                    options.append((option, option))
            if options:
                field_vals["selection"] = str(options)
        self.env["ir.model.fields"].sudo().create(field_vals)
        self.env.registry.clear_cache()

    @api.model
    def _remove_ticket_model_field(self, technical_name):
        """Drop a manual ticket field and its database column."""
        if not technical_name:
            return
        model_field = self.env["ir.model.fields"].sudo().search([
            ("model", "=", "service.desk.ticket"),
            ("name", "=", technical_name),
            ("state", "=", "manual"),
        ], limit=1)
        if not model_field:
            return
        if model_field.required:
            model_field.write({"required": False})
        model_field.unlink()
        self.env.registry.clear_cache()

    def _remove_field_view_inherit(self):
        self.ensure_one()
        View = self.env["ir.ui.view"].sudo()
        if self.view_id:
            self.view_id.unlink()
            self.view_id = False
        View.search([
            ("model", "=", "service.desk.ticket"),
            ("name", "=", "service.desk.ticket.form.field.%s" % self.technical_name),
        ]).unlink()
        self.env.registry.clear_cache()

    @api.model
    def _cleanup_stale_ticket_field_view_inherits(self):
        """Disable/delete form inherits that still reference removed x_ fields."""
        View = self.env["ir.ui.view"].sudo()
        model_fields = set(self.env["service.desk.ticket"]._fields.keys())
        for view in View.with_context(active_test=False).search([
            ("model", "=", "service.desk.ticket"),
            ("mode", "=", "extension"),
        ]):
            arch = view.arch or ""
            orphan_fields = [
                name for name in re.findall(r'<field[^>]*\sname="([^"]+)"', arch)
                if name.startswith("x_") and name not in model_fields
            ]
            if not orphan_fields:
                continue
            if view.name.startswith("service.desk.ticket.form.field."):
                view.unlink()
            else:
                view.write({"active": False})

    @api.model
    def _cleanup_orphan_custom_field_artifacts(self):
        """Remove ticket field views/columns left after incomplete deletes."""
        configured = set(
            self.with_context(active_test=False).search([]).mapped("technical_name")
        )
        View = self.env["ir.ui.view"].sudo()
        for view in View.search([
            ("model", "=", "service.desk.ticket"),
            ("name", "=like", "service.desk.ticket.form.field.%"),
        ]):
            technical_name = view.name.replace("service.desk.ticket.form.field.", "", 1)
            if technical_name not in configured:
                view.unlink()
        for model_field in self.env["ir.model.fields"].sudo().search([
            ("model", "=", "service.desk.ticket"),
            ("name", "=like", "x_%"),
            ("state", "=", "manual"),
        ]):
            if model_field.name not in configured:
                self._remove_ticket_model_field(model_field.name)
        self._cleanup_stale_ticket_field_view_inherits()
        self.env.registry.clear_cache()

    def write(self, vals):
        res = super().write(vals)
        if "active" in vals:
            for field in self:
                if field.view_id:
                    field.view_id.sudo().write({"active": field.active})
        return res

    def unlink(self):
        technical_names = self.mapped("technical_name")
        for field in self:
            field._remove_field_view_inherit()
        res = super().unlink()
        for technical_name in technical_names:
            self._remove_ticket_model_field(technical_name)
        return res

    def _create_form_view_inherit(self, widget=None):
        self.ensure_one()
        self._register_on_ticket_model()
        field_label = escape(self.name or self.technical_name)
        attrs = ' string="%s"' % field_label
        if self.is_required:
            attrs += ' required="1"'
        if widget:
            attrs += ' widget="%s"' % escape(widget)
        groups_attr = _groups_attr_from_record(self)
        if self.tab_anchor and str(self.tab_anchor).lower() != "false":
            arch = (
                '<xpath expr="//page[@name=\'%s\']" position="inside">'
                '<field name="%s"%s%s/>'
                "</xpath>"
            ) % (self.tab_anchor, self.technical_name, attrs, groups_attr)
        else:
            arch = (
                '<xpath expr="//field[@name=\'%s\']" position="%s">'
                '<field name="%s"%s%s/>'
                "</xpath>"
            ) % (
                self.anchor_field or "replied_status",
                self.position or "after",
                self.technical_name,
                attrs,
                groups_attr,
            )
        View = self.env["ir.ui.view"].sudo()
        view_vals = {
            "name": "service.desk.ticket.form.field.%s" % self.technical_name,
            "model": "service.desk.ticket",
            "inherit_id": _ticket_form_view(self.env).id,
            "arch": arch,
            "mode": "extension",
            "active": True,
        }
        if self.view_id:
            self.view_id.write({"arch": arch, "active": True})
            view = self.view_id
        else:
            view = View.create(view_vals)
            self.view_id = view.id
        self.env.registry.clear_cache()
        return view


class ServiceDeskTicketCustomValue(models.Model):
    _name = "service.desk.ticket.custom.value"
    _description = "Ticket Custom Field Value"
    _order = "field_id"

    ticket_id = fields.Many2one("service.desk.ticket", required=True, ondelete="cascade")
    field_id = fields.Many2one("service.desk.form.field", required=True, ondelete="cascade")
    value_char = fields.Char()
    value_text = fields.Text()
    value_integer = fields.Integer()
    value_float = fields.Float()
    value_boolean = fields.Boolean()
    value_date = fields.Date()
    value_datetime = fields.Datetime()
    value_selection = fields.Char()

    _sql_constraints = [
        ("ticket_field_unique", "unique(ticket_id, field_id)", "Each custom field can only be set once per ticket."),
    ]

    def get_display_value(self):
        self.ensure_one()
        field = self.field_id
        mapping = {
            "char": self.value_char,
            "text": self.value_text,
            "integer": self.value_integer,
            "float": self.value_float,
            "boolean": self.value_boolean,
            "date": self.value_date,
            "datetime": self.value_datetime,
            "selection": self.value_selection,
        }
        return mapping.get(field.field_type, "")
