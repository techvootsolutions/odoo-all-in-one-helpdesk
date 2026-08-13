from odoo import _, fields, models
from odoo.exceptions import ValidationError


class ServiceDeskCreateInvoiceWizard(models.TransientModel):
    _name = "service.desk.create.invoice.wizard"
    _description = "Create Invoice from Ticket"

    ticket_id = fields.Many2one("service.desk.ticket")
    invoice_id = fields.Many2one("account.move")
    partner_id = fields.Many2one("res.partner", required=True)
    subject = fields.Char()
    product_ids = fields.Many2many("product.product", string="Products")

    def action_create(self):
        self.ensure_one()
        if self.ticket_id:
            if not self.product_ids:
                raise ValidationError(_("Please select product for create Invoice"))
            move_vals = self.ticket_id._prepare_invoice_move_defaults()
            move_vals["partner_id"] = self.partner_id.id
            move_vals["invoice_line_ids"] = [
                (0, 0, {
                    "product_id": product.id,
                    "name": product.display_name,
                    "quantity": 1,
                    "price_unit": product.lst_price,
                })
                for product in self.product_ids
            ]
            move = self.env["account.move"].create(move_vals)
            move.sd_ticket_ids = [(4, self.ticket_id.id)]
            return {
                "type": "ir.actions.act_window",
                "res_model": "account.move",
                "view_mode": "form",
                "res_id": move.id,
            }
        ticket = self.env["service.desk.ticket"].create({
            "subject": self.subject,
            "partner_id": self.partner_id.id,
            "product_ids": [(6, 0, self.product_ids.ids)],
        })
        self.invoice_id.sd_ticket_ids = [(4, ticket.id)]
        return {
            "type": "ir.actions.act_window",
            "res_model": "service.desk.ticket",
            "view_mode": "form",
            "res_id": ticket.id,
        }
