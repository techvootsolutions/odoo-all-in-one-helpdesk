from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

STICKY_NOTE_COLOR_PALETTE = (
    "#F06050",
    "#F4A460",
    "#F7CD1F",
    "#6CC1ED",
    "#814968",
    "#EB7E7F",
    "#2C8397",
    "#475577",
    "#D6145F",
    "#30C381",
    "#9365B8",
    "#8B8B8B",
)
DEFAULT_STICKY_NOTE_COLOR = "#F7CD1F"


class ServiceDeskStickyNote(models.Model):
    _name = "service.desk.sticky.note"
    _description = "Sticky Note"
    _order = "sequence, id desc"

    name = fields.Char(string="Title", required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    user_id = fields.Many2one(
        "res.users",
        string="User",
        required=True,
        default=lambda self: self.env.user,
    )
    ticket_id = fields.Many2one("service.desk.ticket", string="Ticket", ondelete="cascade")
    model_id = fields.Many2one("ir.model", string="Model", ondelete="cascade")
    res_id = fields.Integer(string="Record ID")
    note = fields.Html(string="Note")
    color = fields.Char(string="Color", default=DEFAULT_STICKY_NOTE_COLOR)
    is_shared = fields.Boolean(string="Share Note", default=False)
    shared_user_ids = fields.Many2many(
        "res.users",
        "service_desk_sticky_note_shared_user_rel",
        "note_id",
        "user_id",
        string="Shared Users",
    )
    audio_attachment_id = fields.Many2one(
        "ir.attachment",
        string="Audio Note",
        ondelete="set null",
    )
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
    )
    ticket_name = fields.Char(related="ticket_id.name", string="Ticket Reference")

    @api.model
    def _normalize_sticky_note_color(self, value):
        """Odoo 19 color widget stores hex strings; legacy data may use palette indexes."""
        if value in (None, False, ""):
            return DEFAULT_STICKY_NOTE_COLOR
        if isinstance(value, int):
            return STICKY_NOTE_COLOR_PALETTE[value % len(STICKY_NOTE_COLOR_PALETTE)]
        if isinstance(value, str):
            color = value.strip()
            if color.isdigit():
                return STICKY_NOTE_COLOR_PALETTE[int(color) % len(STICKY_NOTE_COLOR_PALETTE)]
            if color.startswith("#"):
                return color
        return DEFAULT_STICKY_NOTE_COLOR

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "color" in vals:
                vals["color"] = self._normalize_sticky_note_color(vals["color"])
            if vals.get("ticket_id") and not vals.get("res_id"):
                vals["res_id"] = vals["ticket_id"]
            if vals.get("ticket_id") and not vals.get("model_id"):
                model = self.env["ir.model"]._get("service.desk.ticket")
                vals["model_id"] = model.id
        return super().create(vals_list)

    def write(self, vals):
        if "color" in vals:
            vals["color"] = self._normalize_sticky_note_color(vals["color"])
        if vals.get("ticket_id"):
            vals.setdefault("res_id", vals["ticket_id"])
            if not vals.get("model_id"):
                model = self.env["ir.model"]._get("service.desk.ticket")
                vals["model_id"] = model.id
        return super().write(vals)

    def _check_delete_access(self):
        manager_group = self.env.ref(
            "tv_service_desk.group_service_desk_sticky_note_manager",
            raise_if_not_found=False,
        )
        is_manager = bool(manager_group and manager_group in self.env.user.group_ids)
        for note in self:
            if note.user_id != self.env.user and not is_manager:
                raise AccessError(_("You are not allowed to delete this note."))

    def unlink(self):
        self._check_delete_access()
        return super().unlink()

    def action_archive_note(self):
        self.write({"active": False})
        return True

    def action_open_document(self):
        self.ensure_one()
        if not self.ticket_id:
            raise UserError(_("This note is not linked to a ticket."))
        return {
            "type": "ir.actions.act_window",
            "name": self.ticket_id.name,
            "res_model": "service.desk.ticket",
            "res_id": self.ticket_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_edit_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Update"),
            "res_model": "service.desk.sticky.note.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_ticket_id": self.ticket_id.id,
                "default_note_id": self.id,
                "default_name": self.name,
                "default_note": self.note,
                "default_color": self.color,
                "default_is_shared": self.is_shared,
                "default_shared_user_ids": [(6, 0, self.shared_user_ids.ids)],
            },
        }

    @api.model
    def get_ticket_sticky_notes(self, ticket_id):
        ticket = self.env["service.desk.ticket"].browse(ticket_id).exists()
        if not ticket:
            return []
        user = self.env.user
        manager_group = self.env.ref(
            "tv_service_desk.group_service_desk_sticky_note_manager",
            raise_if_not_found=False,
        )
        is_manager = bool(manager_group and manager_group in user.group_ids)
        domain = [
            ("ticket_id", "=", ticket.id),
            ("active", "=", True),
            "|",
            ("user_id", "=", user.id),
            ("is_shared", "=", True),
        ]
        if is_manager:
            domain = [("ticket_id", "=", ticket.id), ("active", "=", True)]
        notes = self.search(domain, order="sequence, id")
        return [note._prepare_sticky_note_data() for note in notes]

    def _prepare_sticky_note_data(self):
        self.ensure_one()
        audio_url = False
        if self.audio_attachment_id:
            audio_url = "/web/content/%s?download=true" % self.audio_attachment_id.id
        return {
            "id": self.id,
            "name": self.name,
            "note": self.note or "",
            "color": self.color,
            "user_id": self.user_id.id,
            "user_name": self.user_id.name,
            "is_shared": self.is_shared,
            "has_audio": bool(self.audio_attachment_id),
            "audio_url": audio_url,
            "can_edit": self.user_id == self.env.user,
            "can_delete": self._can_delete(),
            "create_date": fields.Datetime.to_string(self.create_date),
        }

    def _can_delete(self):
        manager_group = self.env.ref(
            "tv_service_desk.group_service_desk_sticky_note_manager",
            raise_if_not_found=False,
        )
        is_manager = bool(manager_group and manager_group in self.env.user.group_ids)
        return self.user_id == self.env.user or is_manager

    @api.model
    def save_audio_note(self, note_id, audio_base64, filename="audio_note.webm"):
        note = self.browse(note_id).exists()
        if not note:
            raise UserError(_("Sticky note not found."))
        if note.user_id != self.env.user:
            raise AccessError(_("You are not allowed to update this note."))
        if note.audio_attachment_id:
            note.audio_attachment_id.unlink()
        attachment = self.env["ir.attachment"].create({
            "name": filename,
            "type": "binary",
            "datas": audio_base64,
            "res_model": self._name,
            "res_id": note.id,
            "mimetype": "audio/webm",
        })
        note.audio_attachment_id = attachment.id
        return True

    @api.model
    def delete_audio_note(self, note_id):
        note = self.browse(note_id).exists()
        if not note:
            raise UserError(_("Sticky note not found."))
        if note.user_id != self.env.user:
            raise AccessError(_("You are not allowed to update this note."))
        if note.audio_attachment_id:
            note.audio_attachment_id.unlink()
            note.audio_attachment_id = False
        return True
