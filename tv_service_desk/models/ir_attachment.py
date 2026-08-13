from odoo import api, models


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.model_create_multi
    def create(self, vals_list):
        attachments = super().create(vals_list)
        for attachment in attachments:
            if attachment.res_model == "service.desk.ticket" and attachment.res_id:
                ticket = self.env["service.desk.ticket"].browse(attachment.res_id)
                if attachment not in ticket.attachment_ids:
                    ticket.attachment_ids = [(4, attachment.id)]
        return attachments
