from odoo import fields, models


class ServiceDeskCreateRepairWizard(models.TransientModel):
    _name = "service.desk.create.repair.wizard"
    _description = "Create Repair Order from Ticket"

    ticket_id = fields.Many2one("service.desk.ticket", required=True)
    partner_id = fields.Many2one("res.partner", required=True)
    product_id = fields.Many2one("product.product", string="Product to Repair", required=True)
    location_id = fields.Many2one("stock.location", string="Source Location")
    description = fields.Text()

    def action_create_repair(self):
        self.ensure_one()
        ticket = self.ticket_id
        repair_vals = {
            "partner_id": self.partner_id.id,
            "product_id": self.product_id.id,
            "internal_notes": self.description or ticket.description,
            "company_id": ticket.company_id.id,
            "move_ids": ticket._prepare_repair_move_lines_from_products(),
        }
        if self.location_id:
            repair_vals["location_id"] = self.location_id.id
        repair = self.env["repair.order"].with_context(
            sd_link_ticket_id=ticket.id,
            sd_set_repair_product=True,
        ).create(repair_vals)
        ticket.message_post(
            body="Repair order <a href='#' data-oe-model='repair.order' data-oe-id='%s'>%s</a> created."
            % (repair.id, repair.name),
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "repair.order",
            "view_mode": "form",
            "views": [[False, "form"]],
            "res_id": repair.id,
        }
