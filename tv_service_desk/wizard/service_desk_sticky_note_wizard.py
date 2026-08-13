from odoo import api, fields, models

from odoo.addons.tv_service_desk.models.service_desk_sticky_note import DEFAULT_STICKY_NOTE_COLOR


class ServiceDeskStickyNoteWizard(models.TransientModel):
    _name = "service.desk.sticky.note.wizard"
    _description = "Sticky Note Wizard"

    ticket_id = fields.Many2one("service.desk.ticket", required=True, ondelete="cascade")
    note_id = fields.Many2one("service.desk.sticky.note", string="Note")
    name = fields.Char(string="Title", required=True)
    note = fields.Html(string="Note")
    color = fields.Char(string="Color", default=DEFAULT_STICKY_NOTE_COLOR)
    is_shared = fields.Boolean(string="Share Note", default=False)
    shared_user_ids = fields.Many2many("res.users", string="Shared Users")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        note = self.env["service.desk.sticky.note"].browse(
            self.env.context.get("default_note_id")
        ).exists()
        if note:
            res.update({
                "note_id": note.id,
                "ticket_id": note.ticket_id.id,
                "name": note.name,
                "note": note.note,
                "color": note.color,
                "is_shared": note.is_shared,
                "shared_user_ids": [(6, 0, note.shared_user_ids.ids)],
            })
        return res

    def action_save(self):
        self.ensure_one()
        Note = self.env["service.desk.sticky.note"]
        vals = {
            "name": self.name,
            "note": self.note,
            "color": Note._normalize_sticky_note_color(self.color),
            "is_shared": self.is_shared,
            "shared_user_ids": [(6, 0, self.shared_user_ids.ids)],
            "ticket_id": self.ticket_id.id,
        }
        if self.note_id:
            self.note_id.write(vals)
        else:
            vals["user_id"] = self.env.user.id
            self.env["service.desk.sticky.note"].create(vals)
        return {
            "type": "ir.actions.client",
            "tag": "soft_reload",
        }
