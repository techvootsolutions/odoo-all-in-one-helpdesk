from odoo import api, fields, models


class ServiceDeskTicketRating(models.Model):
    _name = "service.desk.ticket.rating"
    _description = "Service Desk Ticket Rating"
    _order = "create_date desc"

    ticket_id = fields.Many2one("service.desk.ticket", required=True, ondelete="cascade")
    partner_id = fields.Many2one("res.partner", string="Customer")
    user_id = fields.Many2one("res.users", string="Agent")
    team_id = fields.Many2one("service.desk.team", string="Team")
    rating = fields.Selection(
        [
            ("1", "1 Star"),
            ("2", "2 Stars"),
            ("3", "3 Stars"),
            ("4", "4 Stars"),
            ("5", "5 Stars"),
        ],
        required=True,
    )
    comment = fields.Text()
    company_id = fields.Many2one("res.company", related="ticket_id.company_id", store=True)

    @api.model_create_multi
    def create(self, vals_list):
        ratings = super().create(vals_list)
        for rating in ratings:
            ticket = rating.ticket_id
            ticket.write({
                "feedback_rating": rating.rating,
                "feedback_comment": rating.comment,
                "feedback_date": fields.Datetime.now(),
            })
        return ratings
