from odoo import api, fields, models

from .service_desk_ticket_bridge_mixin import _prepare_helpdesk_act_window


class RepairOrder(models.Model):
    _inherit = "repair.order"

    sd_ticket_ids = fields.Many2many(
        "service.desk.ticket",
        "service_desk_ticket_repair_order_rel",
        "repair_id",
        "ticket_id",
        string="Tickets",
    )
    sd_ticket_count = fields.Integer(compute="_compute_sd_ticket_count")

    @api.depends("sd_ticket_ids")
    def _compute_sd_ticket_count(self):
        for repair in self:
            repair.sd_ticket_count = len(repair.sd_ticket_ids)

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        ticket_id = self.env.context.get("sd_link_ticket_id")
        ticket = (
            self.env["service.desk.ticket"].browse(int(ticket_id)).exists()
            if ticket_id
            else self.env["service.desk.ticket"]
        )
        for order in orders:
            if ticket and ticket not in order.sd_ticket_ids:
                order.sd_ticket_ids = [(4, ticket.id)]
            if ticket and self.env.context.get("sd_set_repair_product") and order.product_id:
                ticket.repair_product_id = order.product_id.id
            if ticket and not order.move_ids:
                move_lines = ticket._prepare_repair_move_lines_from_products()
                if move_lines:
                    order.write({"move_ids": move_lines})
            if order.sd_ticket_ids:
                order.sd_ticket_ids.write({"repair_order_ids": [(4, order.id)]})
        return orders

    def action_create_service_desk_ticket(self):
        self.ensure_one()
        partner = self.partner_id
        products = self.product_id | self.move_ids.mapped("product_id")
        return _prepare_helpdesk_act_window(
            "service.desk.ticket",
            target="new",
            name="Helpdesk Ticket",
            context={
                "default_subject": self.name,
                "default_partner_id": partner.id if partner else False,
                "default_person_name": partner.name if partner else False,
                "default_partner_email": partner.email if partner else False,
                "default_partner_phone": partner.phone or partner.mobile if partner else False,
                "default_repair_product_id": self.product_id.id if self.product_id else False,
                "default_product_ids": [(6, 0, products.ids)],
                "default_user_id": self.user_id.id,
                "sd_link_repair_order_id": self.id,
            },
        )

    def action_view_service_desk_tickets(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Helpdesk Tickets",
            "res_model": "service.desk.ticket",
            "view_mode": "kanban,list,form",
            "domain": [("id", "in", self.sd_ticket_ids.ids)],
            "context": {"create": False},
        }
