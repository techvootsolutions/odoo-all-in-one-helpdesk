from odoo import _, fields, models
from odoo.exceptions import ValidationError


class ServiceDeskCreateSaleWizard(models.TransientModel):
    _name = "service.desk.create.sale.wizard"
    _description = "Create Sale Order from Ticket"

    ticket_id = fields.Many2one("service.desk.ticket")
    sale_order_id = fields.Many2one("sale.order")
    partner_id = fields.Many2one("res.partner", required=True)
    subject = fields.Char()
    product_ids = fields.Many2many("product.product", string="Products")

    def action_create(self):
        self.ensure_one()
        if self.ticket_id:
            if not self.product_ids:
                raise ValidationError(_("Please select product for create Sale Order"))
            order = self.env["sale.order"].create({
                "partner_id": self.partner_id.id,
                "order_line": [
                    (0, 0, {"product_id": product.id, "product_uom_qty": 1})
                    for product in self.product_ids
                ],
            })
            order.sd_ticket_ids = [(4, self.ticket_id.id)]
            return {
                "type": "ir.actions.act_window",
                "res_model": "sale.order",
                "view_mode": "form",
                "res_id": order.id,
            }
        ticket = self.env["service.desk.ticket"].create({
            "subject": self.subject,
            "partner_id": self.partner_id.id,
            "product_ids": [(6, 0, self.product_ids.ids)],
        })
        self.sale_order_id.sd_ticket_ids = [(4, ticket.id)]
        return {
            "type": "ir.actions.act_window",
            "res_model": "service.desk.ticket",
            "view_mode": "form",
            "res_id": ticket.id,
        }
