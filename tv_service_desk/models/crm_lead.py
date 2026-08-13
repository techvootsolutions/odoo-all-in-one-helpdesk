from odoo import api, fields, models

from .service_desk_ticket_bridge_mixin import _prepare_helpdesk_act_window


class CrmLead(models.Model):
    _inherit = ["crm.lead", "service.desk.ticket.bridge.mixin"]

    sd_ticket_ids = fields.Many2many(
        "service.desk.ticket",
        "service_desk_ticket_crm_lead_rel",
        "lead_id",
        "ticket_id",
        string="Service Desk Tickets",
    )
    sd_ticket_count = fields.Integer(compute="_compute_sd_ticket_count")

    @api.depends("sd_ticket_ids")
    def _compute_sd_ticket_count(self):
        for lead in self:
            lead.sd_ticket_count = len(lead.sd_ticket_ids)

    @api.model_create_multi
    def create(self, vals_list):
        leads = super().create(vals_list)
        ticket_id = self.env.context.get("sd_link_ticket_id")
        if ticket_id:
            ticket = self.env["service.desk.ticket"].browse(int(ticket_id)).exists()
            if ticket:
                for lead in leads:
                    lead.sd_ticket_ids = [(4, ticket.id)]
        return leads

    def action_create_service_desk_ticket(self):
        self.ensure_one()
        partner = self.partner_id
        return _prepare_helpdesk_act_window(
            "service.desk.ticket",
            target="new",
            name="Helpdesk Ticket",
            context={
                "default_subject": self.name,
                "default_partner_id": partner.id if partner else False,
                "default_person_name": self.contact_name or (partner.name if partner else False),
                "default_partner_email": self.email_from or (partner.email if partner else False),
                "default_partner_phone": self.phone or self.mobile or (partner.phone if partner else False),
                "default_user_id": self.user_id.id,
                "sd_link_lead_id": self.id,
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
