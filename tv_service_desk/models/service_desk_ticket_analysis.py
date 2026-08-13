from odoo import fields, models, tools


class ServiceDeskTicketAnalysis(models.Model):
    _name = "service.desk.ticket.analysis"
    _description = "Service Desk Ticket Analysis"
    _auto = False
    _rec_name = "ticket_id"
    _order = "create_date desc"

    ticket_id = fields.Many2one("service.desk.ticket", readonly=True)
    name = fields.Char(readonly=True)
    subject = fields.Char(readonly=True)
    partner_id = fields.Many2one("res.partner", readonly=True)
    team_id = fields.Many2one("service.desk.team", readonly=True)
    user_id = fields.Many2one("res.users", readonly=True)
    stage_id = fields.Many2one("service.desk.stage", readonly=True)
    category_id = fields.Many2one("service.desk.category", readonly=True)
    priority_id = fields.Many2one("service.desk.priority", readonly=True)
    company_id = fields.Many2one("res.company", readonly=True)
    create_date = fields.Datetime(readonly=True)
    close_date = fields.Datetime(readonly=True)
    sla_status = fields.Selection(
        [
            ("none", "None"),
            ("ongoing", "Ongoing"),
            ("passed", "Passed"),
            ("failed", "Failed"),
            ("partially_passed", "Partially Passed"),
        ],
        readonly=True,
    )
    sla_reached_duration = fields.Float(string="SLA Reached Duration (Hours)", readonly=True)
    sla_late_duration = fields.Float(string="SLA Late Duration (Hours)", readonly=True)
    feedback_rating = fields.Selection(
        [
            ("0", "No Rating"),
            ("1", "Poor"),
            ("2", "Fair"),
            ("3", "Good"),
            ("4", "Very Good"),
            ("5", "Excellent"),
        ],
        readonly=True,
    )
    total_hours_spent = fields.Float(readonly=True)
    support_contract_id = fields.Many2one("service.desk.support.contract", readonly=True)
    nbr = fields.Integer(string="# Tickets", readonly=True)

    def _ticket_column_exists(self, column_name):
        self.env.cr.execute(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'service_desk_ticket' AND column_name = %s
            """,
            (column_name,),
        )
        return bool(self.env.cr.fetchone())

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        if self._ticket_column_exists("support_contract_id"):
            contract_sql = "t.support_contract_id"
        else:
            contract_sql = "NULL::integer AS support_contract_id"
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    t.id AS id,
                    t.id AS ticket_id,
                    t.name,
                    t.subject,
                    t.partner_id,
                    t.team_id,
                    t.user_id,
                    t.stage_id,
                    t.category_id,
                    t.priority_id,
                    t.company_id,
                    t.create_date,
                    t.close_date,
                    t.sla_status,
                    t.sla_reached_duration,
                    t.sla_late_duration,
                    t.feedback_rating,
                    t.total_hours_spent,
                    %s,
                    1 AS nbr
                FROM service_desk_ticket t
                WHERE t.active = true
            )
            """
            % (self._table, contract_sql)
        )
