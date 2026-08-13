from odoo import _, models


def _prepare_helpdesk_act_window(res_model, view_modes="form", **extra):
    modes = [mode.strip() for mode in view_modes.split(",") if mode.strip()]
    action = {
        "type": "ir.actions.act_window",
        "res_model": res_model,
        "view_mode": ",".join(modes),
        "views": [(False, mode) for mode in modes],
    }
    action.update(extra)
    return action


class ServiceDeskTicketBridgeMixin(models.AbstractModel):
    _name = "service.desk.ticket.bridge.mixin"
    _description = "Helpdesk Ticket Bridge Mixin"

    def get_helpdesk_ticket_widget_data(self):
        result = {}
        for record in self:
            result[record.id] = [
                {
                    "id": ticket.id,
                    "name": ticket.name,
                    "partner": ticket.partner_id.display_name or "",
                    "subject": ticket.subject or "",
                    "stage": ticket.stage_id.name or "",
                }
                for ticket in record.sd_ticket_ids
            ]
        return result

    def action_helpdesk_ticket_widget_open(self, ticket_id):
        self.ensure_one()
        ticket = self.env["service.desk.ticket"].browse(int(ticket_id)).exists()
        if not ticket or ticket not in self.sd_ticket_ids:
            return False
        return _prepare_helpdesk_act_window(
            "service.desk.ticket",
            name=_("Helpdesk Ticket"),
            res_id=ticket.id,
            target="current",
        )
