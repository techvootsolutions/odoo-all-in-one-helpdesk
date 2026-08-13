from odoo import fields, models


class ServiceDeskCreateLeadWizard(models.TransientModel):
    _name = "service.desk.create.lead.wizard"
    _description = "Create CRM Record from Ticket"

    ticket_id = fields.Many2one("service.desk.ticket")
    lead_id = fields.Many2one("crm.lead")
    record_type = fields.Selection(
        [("lead", "Lead"), ("opportunity", "Opportunity")],
        default="lead",
        required=True,
    )
    name = fields.Char(required=True)
    partner_id = fields.Many2one("res.partner")
    team_id = fields.Many2one("crm.team")
    description = fields.Text()
    subject = fields.Char()

    def action_create(self):
        self.ensure_one()
        if self.ticket_id:
            lead = self.env["crm.lead"].create({
                "name": self.name,
                "type": self.record_type,
                "partner_id": self.partner_id.id,
                "team_id": self.team_id.id,
                "description": self.description,
            })
            lead.sd_ticket_ids = [(4, self.ticket_id.id)]
            return {
                "type": "ir.actions.act_window",
                "res_model": "crm.lead",
                "view_mode": "form",
                "res_id": lead.id,
            }
        ticket = self.env["service.desk.ticket"].create({
            "subject": self.subject or self.name,
            "partner_id": self.partner_id.id,
            "description": self.description,
        })
        self.lead_id.sd_ticket_ids = [(4, ticket.id)]
        return {
            "type": "ir.actions.act_window",
            "res_model": "service.desk.ticket",
            "view_mode": "form",
            "res_id": ticket.id,
        }
