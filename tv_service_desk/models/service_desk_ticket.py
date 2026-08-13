from datetime import timedelta

from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import email_normalize


class ServiceDeskTicket(models.Model):
    _name = "service.desk.ticket"
    _description = "Service Desk Ticket"
    _inherit = ["portal.mixin", "mail.thread", "mail.activity.mixin", "service.desk.ticket.ai.mixin"]
    _order = "priority_id desc, create_date desc, id desc"

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    subject = fields.Char(required=True, tracking=True)
    description = fields.Html(sanitize_attributes=False)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
        tracking=True,
    )
    partner_id = fields.Many2one("res.partner", string="Partner", tracking=True)
    person_name = fields.Char(string="Person Name")
    partner_email = fields.Char(string="Email")
    partner_phone = fields.Char(string="Mobile")
    team_id = fields.Many2one("service.desk.team", string="Team", tracking=True)
    team_head_id = fields.Many2one(
        "res.users",
        string="Team Head",
        related="team_id.leader_id",
        store=True,
        readonly=True,
    )
    user_id = fields.Many2one("res.users", string="Assigned User", tracking=True)
    assigned_user_ids = fields.Many2many(
        "res.users",
        "service_desk_ticket_assigned_user_rel",
        "ticket_id",
        "user_id",
        string="Assign Multi Users",
    )
    stage_id = fields.Many2one(
        "service.desk.stage",
        string="Stage",
        tracking=True,
        domain="[('active', '=', True)]",
        group_expand="_read_group_stage_ids",
        default=lambda self: self._default_stage_id(),
    )
    category_id = fields.Many2one("service.desk.category", string="Category")
    subcategory_id = fields.Many2one(
        "service.desk.category",
        string="Sub Category",
        domain="[('parent_id', '=', category_id)]",
    )
    tag_ids = fields.Many2many("service.desk.tag", string="Tags")
    priority_id = fields.Many2one("service.desk.priority", string="Priority")
    ticket_type_id = fields.Many2one("service.desk.ticket.type", string="Ticket Type")
    subject_type_id = fields.Many2one(
        "service.desk.ticket.subject.type",
        string="Ticket Subject Type",
    )
    color = fields.Integer()
    product_ids = fields.Many2many("product.product", string="Products")
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "service_desk_ticket_attachment_rel",
        "ticket_id",
        "attachment_id",
        string="Attachments",
    )
    stage_color = fields.Integer(related="stage_id.color", store=True)
    calendar_date = fields.Datetime(compute="_compute_calendar_date", store=True)
    replied_status = fields.Selection(
        [
            ("new", "New"),
            ("customer_replied", "Customer Replied"),
            ("staff_replied", "Staff Replied"),
        ],
        string="Replied Status",
        default="new",
        tracking=True,
    )
    replied_date = fields.Datetime(string="Replied Date")
    close_date = fields.Datetime()
    closed_by_id = fields.Many2one("res.users", string="Closed By")
    closed_comment = fields.Text(string="Closed Comment")
    cancelled_date = fields.Datetime(string="Cancelled Date")
    cancelled_by_id = fields.Many2one("res.users", string="Cancelled By")
    cancelled_reason = fields.Text(string="Cancel Reason")
    last_update_date = fields.Datetime(
        string="Last Update Date",
        related="write_date",
        readonly=True,
    )
    reminder_due_date = fields.Datetime(string="Reminder Due Date")
    alarm_ids = fields.Many2many(
        "service.desk.alarm",
        "service_desk_ticket_alarm_rel",
        "ticket_id",
        "alarm_id",
        string="Ticket Reminders",
    )
    reminder_email_sent = fields.Boolean(copy=False)
    reminder_popup_shown = fields.Boolean(copy=False)
    reminder_popup_dismissed_user_ids = fields.Many2many(
        "res.users",
        "service_desk_ticket_reminder_dismissed_rel",
        "ticket_id",
        "user_id",
        string="Reminder Popup Dismissed By",
        copy=False,
    )
    auto_followup = fields.Boolean(string="Auto Follow-up")
    followup_template_id = fields.Many2one(
        "service.desk.auto.followup",
        string="Followup Template",
    )
    followup_history_ids = fields.One2many(
        "service.desk.ticket.followup.history",
        "ticket_id",
        string="Followup History",
    )
    followup_generated = fields.Boolean(copy=False)
    sticky_note_ids = fields.One2many(
        "service.desk.sticky.note",
        "ticket_id",
        string="Sticky Notes",
    )
    partner_opt_out_helpdesk_emails = fields.Boolean(
        string="Opt Out Helpdesk Emails",
        compute="_compute_partner_opt_out_helpdesk_emails",
    )
    real_duration = fields.Float(
        string="Real Duration",
        compute="_compute_real_duration",
        store=True,
    )
    real_duration_display = fields.Char(
        string="Real Duration",
        compute="_compute_real_duration_display",
    )
    current_user_timer_running = fields.Boolean(compute="_compute_timer_state")
    current_user_timer_start = fields.Datetime(compute="_compute_timer_state")
    active_timer_user_id = fields.Many2one("res.users", compute="_compute_timer_state", string="Active Timer User")
    active_timer_start = fields.Datetime(compute="_compute_timer_state")
    approved = fields.Boolean(string="Approved", default=False, copy=False)
    attachment_count = fields.Integer(compute="_compute_attachment_count")
    sla_reach_label = fields.Char(compute="_compute_sla_reach_label")
    helpdesk_role_label = fields.Char(compute="_compute_helpdesk_role_label")
    display_replied_label = fields.Char(compute="_compute_display_replied_label")
    sla_policy_id = fields.Many2one("service.desk.sla.policy", string="SLA Policy")
    sla_deadline = fields.Datetime(string="SLA Deadline", tracking=True)
    sla_status = fields.Selection(
        [
            ("none", "None"),
            ("ongoing", "Ongoing"),
            ("passed", "Passed"),
            ("failed", "Failed"),
            ("partially_passed", "Partially Passed"),
        ],
        string="SLA Status",
        compute="_compute_sla_status",
        store=True,
    )
    sla_reached_duration = fields.Float(
        string="SLA Reached Duration (Hours)",
        compute="_compute_sla_durations",
        store=True,
    )
    sla_late_duration = fields.Float(
        string="SLA Late Duration (Hours)",
        compute="_compute_sla_durations",
        store=True,
    )
    stage_log_ids = fields.One2many(
        "service.desk.stage.log",
        "ticket_id",
        string="Stage History",
    )
    timesheet_ids = fields.One2many(
        "account.analytic.line",
        "sd_ticket_id",
        string="Timesheets",
    )
    total_hours_spent = fields.Float(
        compute="_compute_total_hours_spent",
        store=True,
    )
    timer_user_id = fields.Many2one("res.users", string="Timer Running For")
    timer_start = fields.Datetime(string="Timer Started At")
    is_timer_running = fields.Boolean(compute="_compute_is_timer_running")
    feedback_rating = fields.Selection(
        [
            ("0", "No Rating"),
            ("1", "Poor"),
            ("2", "Fair"),
            ("3", "Good"),
            ("4", "Very Good"),
            ("5", "Excellent"),
        ],
        string="Customer Rating",
        copy=False,
    )
    feedback_comment = fields.Text(string="Customer Feedback", copy=False)
    feedback_date = fields.Datetime(copy=False)
    sd_rating_ids = fields.One2many(
        "service.desk.ticket.rating",
        "ticket_id",
        string="Rating History",
    )
    support_contract_id = fields.Many2one(
        "service.desk.support.contract",
        string="Support Contract",
        domain="[('partner_id', '=', partner_id), ('state', '=', 'active')]",
    )
    first_response_deadline = fields.Datetime(string="First Response Deadline")
    first_response_date = fields.Datetime(string="First Response At", readonly=True)
    first_response_status = fields.Selection(
        [
            ("no_sla", "No SLA"),
            ("ongoing", "Ongoing"),
            ("reached", "Reached"),
            ("failed", "Failed"),
        ],
        compute="_compute_first_response_status",
        store=True,
    )
    resolution_hours = fields.Float(compute="_compute_resolution_hours", store=True)
    source = fields.Selection(
        [
            ("manual", "Manual"),
            ("email", "Email"),
            ("portal", "Portal"),
            ("whatsapp", "WhatsApp"),
        ],
        default="manual",
    )
    knowledge_article_ids = fields.Many2many(
        "service.desk.knowledge.article",
        string="Suggested Articles",
    )
    custom_value_ids = fields.One2many(
        "service.desk.ticket.custom.value",
        "ticket_id",
        string="Custom Fields",
    )
    whatsapp_message_ids = fields.One2many(
        "service.desk.whatsapp.message",
        "ticket_id",
        string="WhatsApp Messages",
    )
    repair_product_id = fields.Many2one("product.product", string="Repair Product")
    repair_order_ids = fields.Many2many(
        "repair.order",
        "service_desk_ticket_repair_order_rel",
        "ticket_id",
        "repair_id",
        string="Repair Orders",
    )
    repair_count = fields.Integer(compute="_compute_repair_count")
    ai_category_suggestion_id = fields.Many2one("service.desk.category", string="AI Category Suggestion")
    ai_priority_suggestion_id = fields.Many2one("service.desk.priority", string="AI Priority Suggestion")
    ai_sentiment = fields.Selection(
        [
            ("neutral", "Neutral"),
            ("positive", "Positive"),
            ("concerned", "Concerned"),
            ("frustrated", "Frustrated"),
        ],
        string="AI Sentiment",
    )
    ai_summary = fields.Text(string="AI Summary")
    ai_reply_suggestion = fields.Text(string="AI Reply Suggestion")
    lead_count = fields.Integer(compute="_compute_bridge_counts")
    opportunity_count = fields.Integer(compute="_compute_bridge_counts")
    sale_count = fields.Integer(compute="_compute_bridge_counts")
    purchase_count = fields.Integer(compute="_compute_bridge_counts")
    invoice_count = fields.Integer(compute="_compute_bridge_counts")
    task_count = fields.Integer(compute="_compute_bridge_counts")
    is_unread = fields.Boolean(
        compute="_compute_is_unread",
        search="_search_is_unread",
    )
    sd_show_multi_users = fields.Boolean(compute="_compute_sd_ui_flags")
    sd_show_products = fields.Boolean(compute="_compute_sd_ui_flags")
    sd_show_reminders = fields.Boolean(compute="_compute_sd_ui_flags")
    sd_show_category = fields.Boolean(compute="_compute_sd_ui_flags")
    sd_show_subcategory = fields.Boolean(compute="_compute_sd_ui_flags")
    sd_show_customer_rating = fields.Boolean(compute="_compute_sd_ui_flags")
    lead_ids = fields.Many2many(
        "crm.lead",
        "service_desk_ticket_crm_lead_rel",
        "ticket_id",
        "lead_id",
        string="Leads/Opportunities",
    )
    sale_order_ids = fields.Many2many(
        "sale.order",
        "service_desk_ticket_sale_order_rel",
        "ticket_id",
        "order_id",
        string="Sale Orders",
    )
    purchase_order_ids = fields.Many2many(
        "purchase.order",
        "service_desk_ticket_purchase_order_rel",
        "ticket_id",
        "order_id",
        string="Purchase Orders",
    )
    invoice_ids = fields.Many2many(
        "account.move",
        "service_desk_ticket_account_move_rel",
        "ticket_id",
        "move_id",
        string="Invoices",
        domain="[('move_type', 'in', ('out_invoice', 'out_refund'))]",
    )
    has_running_timer = fields.Boolean(
        string="Running Timer",
        compute="_compute_has_running_timer",
        search="_search_has_running_timer",
    )
    task_ids = fields.Many2many("project.task", compute="_compute_bridge_records")
    is_team_leader_or_manager = fields.Boolean(
        compute="_compute_is_team_leader_or_manager",
        compute_sudo=True,
    )
    sd_show_assignment_fields = fields.Boolean(compute="_compute_sd_role_ui")
    sd_show_real_duration_field = fields.Boolean(compute="_compute_sd_role_ui")
    sd_show_customer_rating_tab = fields.Boolean(compute="_compute_sd_role_ui")
    sd_show_timesheets_tab = fields.Boolean(compute="_compute_sd_role_ui")
    sd_show_followup_tab = fields.Boolean(compute="_compute_sd_role_ui")
    sd_is_helpdesk_manager = fields.Boolean(compute="_compute_sd_role_ui")
    sd_show_repair_fields = fields.Boolean(compute="_compute_sd_role_ui")
    sd_is_support_user = fields.Boolean(compute="_compute_sd_role_ui")
    sd_show_sla_badge = fields.Boolean(compute="_compute_sd_role_ui")
    sd_show_sla_fields = fields.Boolean(compute="_compute_sd_role_ui")
    sd_show_routing_info = fields.Boolean(compute="_compute_sd_role_ui")
    sd_show_other_info_manager_fields = fields.Boolean(compute="_compute_sd_role_ui")
    sd_integration_fields_readonly = fields.Boolean(compute="_compute_sd_role_ui")
    sd_sla_fields_readonly = fields.Boolean(compute="_compute_sd_role_ui")
    sd_show_reopen_button = fields.Boolean(compute="_compute_sd_show_reopen_button")
    sd_create_assign_status = fields.Char(
        string="Assignment Status",
        readonly=True,
        copy=False,
    )
    sd_create_notify_summary = fields.Char(
        string="Notifications Sent",
        readonly=True,
        copy=False,
    )

    _NON_MANAGER_PROTECTED_FIELDS = frozenset({
        "sla_policy_id",
        "sla_deadline",
        "first_response_deadline",
        "approved",
        "alarm_ids",
        "reminder_due_date",
        "close_date",
        "closed_by_id",
        "closed_comment",
        "cancelled_date",
        "cancelled_by_id",
        "cancelled_reason",
        "support_contract_id",
    })
    _SUPPORT_USER_ASSIGNMENT_FIELDS = frozenset({
        "team_id",
        "user_id",
        "assigned_user_ids",
        "replied_status",
    })


    @api.depends("stage_id")
    def _compute_sd_show_reopen_button(self):
        for ticket in self:
            ticket.sd_show_reopen_button = ticket._is_closed_or_cancelled_stage()

    def _is_closed_or_cancelled_stage(self):
        self.ensure_one()
        stage = self.stage_id
        if not stage:
            return False
        closed_id = self._get_config_stage_id("tv_service_desk.stage_closed_id", "stage_done")
        cancel_id = self._get_config_stage_id("tv_service_desk.stage_cancel_id", "stage_cancelled")
        if closed_id and stage.id == closed_id:
            return True
        if cancel_id and stage.id == cancel_id:
            return True
        return stage.name in ("Closed", "Cancelled")

    @api.model
    def _default_stage_id(self):
        return self.env["service.desk.stage"].search(
            [("is_default", "=", True)],
            limit=1,
        ).id

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        return self.env["service.desk.stage"].search(
            [("active", "=", True)],
            order="sequence, id",
        )

    @api.model
    def _user_can_access_repair_orders(self):
        return self.env.user.has_group("stock.group_stock_user")

    @api.model
    def _user_can_write_repair_fields(self):
        user = self.env.user
        return (
            user.has_group("tv_service_desk.group_service_desk_repair")
            and user.has_group("stock.group_stock_user")
        )

    @api.model
    def _sanitize_ticket_vals_for_access(self, vals):
        """Drop integration fields the current user cannot write (form may still post them)."""
        vals = dict(vals)
        user = self.env.user
        if not self._user_can_write_repair_fields():
            vals.pop("repair_product_id", None)
            vals.pop("repair_order_ids", None)
        integration_fields = (
            ("lead_ids", "tv_service_desk.group_service_desk_crm"),
            ("invoice_ids", "tv_service_desk.group_service_desk_invoice"),
            ("purchase_order_ids", "tv_service_desk.group_service_desk_purchase"),
            ("sale_order_ids", "tv_service_desk.group_service_desk_sale"),
        )
        for field_name, group_xmlid in integration_fields:
            if field_name in vals and not user.has_group(group_xmlid):
                vals.pop(field_name, None)
        return vals

    @api.model
    def _user_can_read_crm_leads(self):
        return self.env.user.has_group("tv_service_desk.group_service_desk_crm")

    @api.model
    def _user_can_read_sale_orders(self):
        return self.env.user.has_group("tv_service_desk.group_service_desk_sale")

    @api.model
    def _user_can_read_purchase_orders(self):
        return self.env.user.has_group("tv_service_desk.group_service_desk_purchase")

    @api.model
    def _user_can_read_invoices(self):
        return self.env.user.has_group("tv_service_desk.group_service_desk_invoice")

    @api.model
    def _user_can_read_project_tasks(self):
        return self.env.user.has_group("tv_service_desk.group_service_desk_task")

    @api.model
    def _user_can_read_repair_orders(self):
        return self.env.user.has_group("stock.group_stock_user")

    @api.model
    def _helpdesk_blocked_read_fields(self):
        """Fields that must not be read when the user lacks the related app access."""
        blocked = set()
        if not self._user_can_read_crm_leads():
            blocked.update(["lead_ids", "lead_count", "opportunity_count"])
        if not self._user_can_read_sale_orders():
            blocked.update(["sale_order_ids", "sale_count"])
        if not self._user_can_read_purchase_orders():
            blocked.update(["purchase_order_ids", "purchase_count"])
        if not self._user_can_read_invoices():
            blocked.update(["invoice_ids", "invoice_count"])
        if not self._user_can_read_repair_orders():
            blocked.update(["repair_product_id", "repair_order_ids", "repair_count"])
        if not self._user_can_read_project_tasks():
            blocked.update(["task_ids", "task_count"])
        if not self._user_can_read_ticket_timesheets():
            blocked.update([
                "timesheet_ids",
                "total_hours_spent",
                "has_running_timer",
                "is_timer_running",
                "current_user_timer_running",
                "current_user_timer_start",
                "active_timer_user_id",
                "active_timer_start",
                "real_duration_display",
            ])
        if not self.env.user.has_group("tv_service_desk.group_service_desk_manager"):
            blocked.add("alarm_ids")
        return blocked

    def read(self, fields=None, load="_classic_read"):
        blocked = self._helpdesk_blocked_read_fields()
        if fields is None:
            fields = [name for name in self.fields_get() if name not in blocked]
        else:
            fields = [name for name in fields if name not in blocked]
        return super().read(fields=fields, load=load)

    def web_read(self, specification):
        blocked = self._helpdesk_blocked_read_fields()
        if blocked:
            specification = {
                name: spec for name, spec in specification.items() if name not in blocked
            }
        return super().web_read(specification)

    @api.model
    def _user_is_support_only(self):
        user = self.env.user
        return (
            user.has_group("tv_service_desk.group_service_desk_user")
            and not user.has_group("tv_service_desk.group_service_desk_team_leader")
            and not user.has_group("tv_service_desk.group_service_desk_manager")
        )

    @api.model
    def _strip_role_protected_vals(self, vals):
        user = self.env.user
        if user.has_group("tv_service_desk.group_service_desk_manager"):
            return vals
        vals = dict(vals)
        for field_name in self._NON_MANAGER_PROTECTED_FIELDS:
            vals.pop(field_name, None)
        if self._user_is_support_only():
            for field_name in self._SUPPORT_USER_ASSIGNMENT_FIELDS:
                vals.pop(field_name, None)
        return vals

    @api.model
    def _user_can_edit_ticket_stage(self):
        user = self.env.user
        is_manager = user.has_group("tv_service_desk.group_service_desk_manager")
        is_leader = user.has_group("tv_service_desk.group_service_desk_team_leader") and not is_manager
        return is_manager or is_leader

    @api.model
    def _user_can_read_ticket_timesheets(self):
        return self.env.user.has_group("hr_timesheet.group_hr_timesheet_user")

    @api.model
    def _user_has_ticket_timesheet_access(self):
        """Helpdesk timer needs both Helpdesk Timesheet and core Timesheets groups."""
        user = self.env.user
        return (
            user.has_group("tv_service_desk.group_service_desk_timesheet")
            and user.has_group("hr_timesheet.group_hr_timesheet_user")
        )

    @api.depends("timesheet_ids.unit_amount")
    def _compute_total_hours_spent(self):
        can_read = self._user_can_read_ticket_timesheets()
        for ticket in self:
            if not can_read:
                continue
            ticket.total_hours_spent = sum(ticket.timesheet_ids.mapped("unit_amount"))

    @api.depends("timesheet_ids.unit_amount", "total_hours_spent")
    @api.depends("partner_id", "partner_id.sd_opt_out_emails", "partner_id.commercial_partner_id.sd_opt_out_emails")
    def _compute_partner_opt_out_helpdesk_emails(self):
        for ticket in self:
            ticket.partner_opt_out_helpdesk_emails = ticket._is_helpdesk_email_opted_out()

    def _compute_real_duration(self):
        can_read = self._user_can_read_ticket_timesheets()
        for ticket in self:
            if not can_read:
                continue
            ticket.real_duration = ticket.total_hours_spent

    @staticmethod
    def _format_duration_hms(total_seconds):
        total_seconds = int(max(total_seconds, 0))
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return "%02d:%02d:%02d" % (hours, minutes, seconds)

    @api.depends(
        "timesheet_ids.unit_amount",
        "timesheet_ids.start_date",
        "timesheet_ids.end_date",
        "timesheet_ids.user_id",
    )
    def _compute_real_duration_display(self):
        now = fields.Datetime.now()
        can_read = self._user_can_read_ticket_timesheets()
        for ticket in self:
            if not can_read:
                ticket.real_duration_display = "00:00:00"
                continue
            total_seconds = 0.0
            for line in ticket.timesheet_ids:
                if line.start_date and not line.end_date:
                    total_seconds += (now - line.start_date).total_seconds()
                elif line.unit_amount:
                    total_seconds += line.unit_amount * 3600.0
            ticket.real_duration_display = ticket._format_duration_hms(total_seconds)

    @api.depends(
        "timesheet_ids.start_date",
        "timesheet_ids.end_date",
        "timesheet_ids.user_id",
    )
    def _compute_timer_state(self):
        user = self.env.user
        can_read = self._user_can_read_ticket_timesheets()
        for ticket in self:
            if not can_read:
                ticket.current_user_timer_running = False
                ticket.current_user_timer_start = False
                ticket.active_timer_user_id = False
                ticket.active_timer_start = False
                continue
            active_lines = ticket.timesheet_ids.filtered(
                lambda line: line.start_date and not line.end_date
            )
            user_line = active_lines.filtered(lambda line: line.user_id == user)[:1]
            display_line = user_line or active_lines[:1]
            ticket.current_user_timer_running = bool(user_line)
            ticket.current_user_timer_start = user_line.start_date if user_line else False
            ticket.active_timer_user_id = display_line.user_id if display_line else False
            ticket.active_timer_start = display_line.start_date if display_line else False

    def _compute_attachment_count(self):
        Attachment = self.env["ir.attachment"]
        for ticket in self:
            ticket.attachment_count = Attachment.search_count([
                ("res_model", "=", ticket._name),
                ("res_id", "=", ticket.id),
            ])

    @api.depends("sla_policy_id", "sla_policy_id.sla_days", "sla_deadline", "sla_status")
    def _compute_sla_reach_label(self):
        now = fields.Datetime.now()
        for ticket in self:
            policy = ticket.sla_policy_id
            if not policy:
                ticket.sla_reach_label = False
                continue
            days = policy.sla_days or 0
            if days == 1:
                ticket.sla_reach_label = _("Reach In 1 day")
            elif days > 1:
                ticket.sla_reach_label = _("Reach In %s days") % days
            elif ticket.sla_deadline and ticket.sla_status in ("ongoing", "partially_passed"):
                remaining = ticket.sla_deadline - now
                remaining_days = max(0, remaining.days)
                if remaining_days == 1:
                    ticket.sla_reach_label = _("Reach In 1 day")
                elif remaining_days > 1:
                    ticket.sla_reach_label = _("Reach In %s days") % remaining_days
                else:
                    remaining_hours = max(1, int(remaining.total_seconds() // 3600))
                    ticket.sla_reach_label = _("Reach In %s hours") % remaining_hours
            else:
                ticket.sla_reach_label = policy.name

    @api.depends_context("uid")
    def _compute_helpdesk_role_label(self):
        user = self.env.user
        if user.has_group("tv_service_desk.group_service_desk_manager"):
            label = _("Support Manager")
        elif user.has_group("tv_service_desk.group_service_desk_team_leader"):
            label = _("Team Leader")
        else:
            label = _("Support User")
        for ticket in self:
            ticket.helpdesk_role_label = label

    @api.depends_context("uid")
    def _compute_is_team_leader_or_manager(self):
        is_leader_or_manager = (
            self.env.user.has_group("tv_service_desk.group_service_desk_team_leader")
            or self.env.user.has_group("tv_service_desk.group_service_desk_manager")
        )
        for ticket in self:
            ticket.is_team_leader_or_manager = is_leader_or_manager

    @api.depends("sd_show_customer_rating")
    @api.depends_context("uid")
    def _compute_sd_role_ui(self):
        """Role-based ticket form layout (reference: Support User / Team Leader / Manager)."""
        user = self.env.user
        is_manager = user.has_group("tv_service_desk.group_service_desk_manager")
        is_leader = user.has_group("tv_service_desk.group_service_desk_team_leader") and not is_manager
        is_support = (
            user.has_group("tv_service_desk.group_service_desk_user")
            and not is_leader
            and not is_manager
        )
        has_timesheet = user.has_group("tv_service_desk.group_service_desk_timesheet")
        has_repair = user.has_group("tv_service_desk.group_service_desk_repair")
        for ticket in self:
            ticket.sd_is_support_user = is_support
            ticket.sd_is_helpdesk_manager = is_manager
            ticket.sd_show_assignment_fields = is_manager or is_leader or is_support
            ticket.sd_show_real_duration_field = is_manager or is_leader
            ticket.sd_show_customer_rating_tab = bool(
                ticket.sd_show_customer_rating and (is_manager or is_leader)
            )
            ticket.sd_show_timesheets_tab = bool(is_manager and has_timesheet)
            ticket.sd_show_followup_tab = is_manager or is_leader
            ticket.sd_show_repair_fields = bool(is_manager and has_repair)
            ticket.sd_show_sla_badge = is_manager or is_leader or is_support
            ticket.sd_show_sla_fields = is_manager or is_leader or is_support
            ticket.sd_show_routing_info = is_support
            ticket.sd_show_other_info_manager_fields = is_manager
            ticket.sd_integration_fields_readonly = is_support
            ticket.sd_sla_fields_readonly = not is_manager


    @api.depends("reminder_due_date", "create_date")
    def _compute_calendar_date(self):
        for ticket in self:
            ticket.calendar_date = ticket.reminder_due_date or ticket.create_date

    @api.depends("replied_status")
    def _compute_display_replied_label(self):
        labels = dict(self._fields["replied_status"].selection)
        for ticket in self:
            ticket.display_replied_label = labels.get(ticket.replied_status, "")

    @api.depends("timesheet_ids.start_date", "timesheet_ids.end_date", "timesheet_ids.user_id")
    def _compute_is_timer_running(self):
        user = self.env.user
        can_read = self._user_can_read_ticket_timesheets()
        for ticket in self:
            if not can_read:
                ticket.is_timer_running = False
                continue
            ticket.is_timer_running = bool(ticket._get_user_active_timer_line(user))

    @api.depends("first_response_deadline", "first_response_date")
    def _compute_first_response_status(self):
        now = fields.Datetime.now()
        for ticket in self:
            if not ticket.first_response_deadline:
                ticket.first_response_status = "no_sla"
            elif ticket.first_response_date:
                ticket.first_response_status = (
                    "reached" if ticket.first_response_date <= ticket.first_response_deadline else "failed"
                )
            elif now > ticket.first_response_deadline:
                ticket.first_response_status = "failed"
            else:
                ticket.first_response_status = "ongoing"

    @api.depends("create_date", "close_date")
    def _compute_resolution_hours(self):
        for ticket in self:
            if ticket.close_date and ticket.create_date:
                delta = ticket.close_date - ticket.create_date
                ticket.resolution_hours = delta.total_seconds() / 3600.0
            else:
                ticket.resolution_hours = 0.0

    def _compute_repair_count(self):
        can_read = self._user_can_access_repair_orders()
        for ticket in self:
            if not can_read:
                ticket.repair_count = 0
                continue
            ticket.repair_count = len(ticket.repair_order_ids)

    @api.depends("sla_deadline", "stage_id", "sla_policy_id", "approved")
    def _compute_sla_status(self):
        now = fields.Datetime.now()
        for ticket in self:
            if not ticket.sla_policy_id or not ticket.sla_deadline:
                ticket.sla_status = "none"
            elif ticket.stage_id == ticket.sla_policy_id.target_stage_id:
                ticket.sla_status = "passed"
            elif ticket.approved or ticket.stage_id.name == "In Progress":
                if not ticket.approved and now > ticket.sla_deadline:
                    ticket.sla_status = "failed"
                else:
                    ticket.sla_status = "passed"
            elif now > ticket.sla_deadline:
                ticket.sla_status = "failed"
            else:
                ticket.sla_status = "partially_passed"

    @api.depends("stage_id", "sla_deadline", "create_date", "stage_log_ids")
    def _compute_sla_durations(self):
        for ticket in self:
            ticket.sla_reached_duration = 0.0
            ticket.sla_late_duration = 0.0
            if not ticket.sla_policy_id or not ticket.sla_deadline:
                continue
            target_stage = ticket.sla_policy_id.target_stage_id
            stage_logs = ticket.stage_log_ids.filtered(
                lambda log: log.new_stage_id == target_stage
            )
            if stage_logs:
                first_reach_date = min(stage_logs.mapped("change_date"))
                create_dt = ticket.create_date or fields.Datetime.now()
                ticket.sla_reached_duration = (first_reach_date - create_dt).total_seconds() / 3600.0
                if first_reach_date > ticket.sla_deadline:
                    ticket.sla_late_duration = (first_reach_date - ticket.sla_deadline).total_seconds() / 3600.0
            else:
                now = fields.Datetime.now()
                if now > ticket.sla_deadline:
                    ticket.sla_late_duration = (now - ticket.sla_deadline).total_seconds() / 3600.0

    @api.depends_context("uid")
    def _compute_bridge_counts(self):
        can_crm = self._user_can_read_crm_leads()
        can_sale = self._user_can_read_sale_orders()
        can_purchase = self._user_can_read_purchase_orders()
        can_invoice = self._user_can_read_invoices()
        can_task = self._user_can_read_project_tasks()
        for ticket in self:
            if can_crm:
                ticket.lead_count = len(ticket.lead_ids.filtered(lambda lead: lead.type == "lead"))
                ticket.opportunity_count = len(
                    ticket.lead_ids.filtered(lambda lead: lead.type == "opportunity")
                )
            else:
                ticket.lead_count = 0
                ticket.opportunity_count = 0
            ticket.sale_count = len(ticket.sale_order_ids) if can_sale else 0
            ticket.purchase_count = len(ticket.purchase_order_ids) if can_purchase else 0
            ticket.invoice_count = len(ticket.invoice_ids) if can_invoice else 0
            ticket.task_count = len(ticket.task_ids) if can_task else 0

    def _compute_bridge_records(self):
        if not self._user_can_read_project_tasks():
            for ticket in self:
                ticket.task_ids = self.env["project.task"]
            return
        Task = self.env["project.task"]
        for ticket in self:
            ticket.task_ids = Task.search([("sd_ticket_id", "=", ticket.id)])

    @api.depends("timesheet_ids.start_date", "timesheet_ids.end_date", "timesheet_ids.user_id")
    def _compute_has_running_timer(self):
        user = self.env.user
        can_read = self._user_can_read_ticket_timesheets()
        for ticket in self:
            if not can_read:
                ticket.has_running_timer = False
                continue
            ticket.has_running_timer = bool(ticket.timesheet_ids.filtered(
                lambda line: line.user_id == user and line.start_date and not line.end_date
            ))

    @api.model
    def _search_has_running_timer(self, operator, value):
        if operator not in ("=", "!="):
            raise NotImplementedError("Unsupported operator")
        if not self._user_can_read_ticket_timesheets():
            if (operator == "=" and value) or (operator == "!=" and not value):
                return [("id", "=", 0)]
            return []
        running_lines = self.env["account.analytic.line"].search([
            ("user_id", "=", self.env.user.id),
            ("sd_ticket_id", "!=", False),
            ("start_date", "!=", False),
            ("end_date", "=", False),
        ])
        ticket_ids = running_lines.mapped("sd_ticket_id").ids
        if operator == "=":
            return [("id", "in", ticket_ids)] if value else [("id", "not in", ticket_ids)]
        return [("id", "not in", ticket_ids)] if value else [("id", "in", ticket_ids)]

    @api.depends("company_id")
    def _compute_sd_ui_flags(self):
        """Compute UI visibility flags from system settings.

        These are stored=True so they are available in list-view
        column_invisible expressions (non-stored compute fields are
        not accessible in the Odoo 19 list row eval context).

        Values are invalidated / recomputed automatically when:
          - a ticket is created (company_id is set)
          - ResConfigSettings.set_values() calls invalidate_model()
            after the user saves Service Desk settings.
        """
        Settings = self.env["res.config.settings"]
        show_multi = Settings._config_bool("tv_service_desk.display_multi_users")
        show_products = Settings._config_bool("tv_service_desk.manage_products")
        show_category = Settings._config_bool("tv_service_desk.category_enabled")
        show_subcategory = Settings._config_bool("tv_service_desk.subcategory_enabled")
        show_rating = Settings._config_bool("tv_service_desk.customer_rating_enabled")
        show_reminders = Settings._config_bool("tv_service_desk.ticket_reminder")
        for ticket in self:
            ticket.sd_show_multi_users = show_multi
            ticket.sd_show_products = show_products
            ticket.sd_show_category = show_category
            ticket.sd_show_subcategory = show_subcategory
            ticket.sd_show_customer_rating = show_rating
            ticket.sd_show_reminders = show_reminders

    @api.depends()
    def _compute_is_unread(self):
        viewed_ids = self._get_viewed_ticket_ids()
        for ticket in self:
            ticket.is_unread = ticket.id not in viewed_ids

    def _search_is_unread(self, operator, value):
        if operator not in ("=", "!="):
            raise NotImplementedError("Unsupported operator")
        viewed_ids = self._get_viewed_ticket_ids()
        if (operator == "=" and value) or (operator == "!=" and not value):
            return [("id", "not in", list(viewed_ids))]
        return [("id", "in", list(viewed_ids))]

    def _get_viewed_ticket_ids(self):
        param = self.env["ir.config_parameter"].sudo()
        key = f"tv_service_desk.viewed.{self.env.user.id}"
        raw = param.get_param(key, "")
        return {int(x) for x in raw.split(",") if x.isdigit()}

    def _mark_as_viewed(self):
        viewed = self._get_viewed_ticket_ids()
        viewed.update(self.ids)
        key = f"tv_service_desk.viewed.{self.env.user.id}"
        self.env["ir.config_parameter"].sudo().set_param(
            key,
            ",".join(str(i) for i in sorted(viewed)),
        )

    def _clear_viewed_for_all_users(self):
        """Remove tickets from every user's viewed list (e.g. after customer reply)."""
        if not self:
            return
        ticket_ids = set(self.ids)
        params = self.env["ir.config_parameter"].sudo().search([
            ("key", "like", "tv_service_desk.viewed.%"),
        ])
        for param in params:
            viewed = {int(x) for x in (param.value or "").split(",") if x.isdigit()}
            updated = viewed - ticket_ids
            if updated != viewed:
                param.value = ",".join(str(i) for i in sorted(updated))

    @api.constrains("category_id", "subcategory_id")
    def _check_subcategory(self):
        for ticket in self:
            if ticket.subcategory_id and ticket.subcategory_id.parent_id != ticket.category_id:
                raise ValidationError(_("Subcategory must belong to the selected category."))

    @api.model
    def _get_partner_mobile_number(self, partner=None, partner_phone=None):
        if partner_phone:
            return partner_phone
        if not partner:
            return False
        mobile = partner.mobile if "mobile" in partner._fields else False
        return mobile or partner.phone

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id:
            self.person_name = self.partner_id.name
            self.partner_email = self.partner_id.email
            self.partner_phone = self._get_partner_mobile_number(partner=self.partner_id)
            if not self.support_contract_id:
                contract = self.env["service.desk.support.contract"].search([
                    ("partner_id", "=", self.partner_id.id),
                    ("state", "=", "active"),
                ], limit=1, order="date_end desc")
                if contract:
                    self.support_contract_id = contract

    @api.onchange("team_id")
    def _onchange_team_id(self):
        if self.team_id and not self.user_id:
            assignee_id = self.team_id._get_next_assignee(self.partner_id, ticket=self)
            if assignee_id:
                self.user_id = assignee_id

    @api.onchange("partner_id", "ticket_type_id", "team_id", "priority_id", "category_id", "support_contract_id")
    def _onchange_sla_policy_trigger(self):
        self._apply_sla_policy()

    @api.onchange("stage_id")
    def _onchange_stage_id_sync(self):
        if not self.stage_id:
            return
        replied_status = self._get_replied_status_for_stage_id(self.stage_id.id)
        if replied_status:
            self.replied_status = replied_status

    @api.onchange("replied_status")
    def _onchange_replied_status_sync(self):
        if not self.replied_status:
            return
        stage_id = self._get_stage_id_for_replied_status(self.replied_status)
        if stage_id:
            self.stage_id = stage_id
        if self.replied_status in ("customer_replied", "staff_replied"):
            self.replied_date = fields.Datetime.now()

    @api.model
    def _get_replied_stage_settings(self):
        return {
            "customer_enabled": self._get_config_bool(
                "tv_service_desk.stage_change_customer_replied"
            ),
            "staff_enabled": self._get_config_bool(
                "tv_service_desk.stage_change_staff_replied"
            ),
            "customer_stage_id": self._get_config_stage_id(
                "tv_service_desk.customer_replied_stage_id",
                "stage_in_progress",
            ),
            "staff_stage_id": self._get_config_stage_id(
                "tv_service_desk.staff_replied_stage_id",
                "stage_in_progress",
            ),
        }

    @api.model
    def _get_stage_id_for_replied_status(self, replied_status, settings=None):
        settings = settings or self._get_replied_stage_settings()
        if replied_status == "customer_replied":
            if settings["customer_enabled"] and settings["customer_stage_id"]:
                return settings["customer_stage_id"]
        elif replied_status == "staff_replied":
            if settings["staff_enabled"] and settings["staff_stage_id"]:
                return settings["staff_stage_id"]
        return False

    @api.model
    def _get_replied_status_for_stage_id(self, stage_id, settings=None):
        settings = settings or self._get_replied_stage_settings()
        if settings["customer_enabled"] and settings["customer_stage_id"] == stage_id:
            return "customer_replied"
        if settings["staff_enabled"] and settings["staff_stage_id"] == stage_id:
            return "staff_replied"
        return False

    @api.model
    def _apply_replied_stage_sync_to_vals(self, vals):
        if self.env.context.get("sd_skip_replied_stage_sync"):
            return vals
        settings = self._get_replied_stage_settings()
        if "replied_status" in vals and "stage_id" not in vals:
            stage_id = self._get_stage_id_for_replied_status(
                vals["replied_status"], settings=settings
            )
            if stage_id:
                vals["stage_id"] = stage_id
        elif "stage_id" in vals and "replied_status" not in vals:
            stage_id = vals["stage_id"]
            if stage_id:
                replied_status = self._get_replied_status_for_stage_id(
                    stage_id, settings=settings
                )
                if replied_status:
                    vals["replied_status"] = replied_status
        return vals

    def _is_customer_message_author(self, partner):
        self.ensure_one()
        if not partner:
            return False
        if self.partner_id:
            ticket_partner = self.partner_id.commercial_partner_id
            author_partner = partner.commercial_partner_id
            if partner == self.partner_id or author_partner == ticket_partner:
                return True
        user = partner.user_ids[:1]
        return bool(user and user.share)

    def _is_staff_message_author(self, partner):
        self.ensure_one()
        if self._is_customer_message_author(partner):
            return False
        if partner:
            user = partner.user_ids[:1]
            if user:
                return not user.share
            return False
        return bool(
            self.env.user.has_group("base.group_user") and not self.env.user.share
        )

    def _set_replied_status(self, replied_status, extra_vals=None):
        self.ensure_one()
        if replied_status not in ("customer_replied", "staff_replied"):
            return
        vals = {
            "replied_status": replied_status,
            "replied_date": fields.Datetime.now(),
        }
        if extra_vals:
            vals.update(extra_vals)
        self.write(vals)
        if replied_status == "customer_replied":
            self._clear_viewed_for_all_users()

    @api.model
    def _apply_ticket_create_defaults(self, vals):
        """Set team on create; assignment is handled by team auto-assign rules."""
        user = self.env.user
        if not user.has_group("base.group_user"):
            return vals
        company_id = vals.get("company_id") or self.env.company.id
        if not vals.get("team_id"):
            user_team = self.env["service.desk.team"].search(
                [
                    ("member_ids", "in", user.id),
                    "|",
                    ("company_id", "=", False),
                    ("company_id", "=", company_id),
                ],
                limit=1,
            )
            if user_team:
                vals["team_id"] = user_team.id
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]

        for i, vals in enumerate(vals_list):
            vals_list[i] = self._sanitize_ticket_vals_for_access(vals)
            vals_list[i] = self._strip_role_protected_vals(vals_list[i])
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = sequence.next_by_code("service.desk.ticket") or _("New")
            self._apply_ticket_create_defaults(vals)
            if not vals.get("team_id"):
                default_team = self.env["service.desk.team"].search(
                    [("is_default", "=", True), ("company_id", "=", vals.get("company_id", self.env.company.id))],
                    limit=1,
                )
                if default_team:
                    vals["team_id"] = default_team.id
            self._apply_replied_stage_sync_to_vals(vals)

        tickets = super().create(vals_list)
        link_lead_id = self.env.context.get("sd_link_lead_id")
        if link_lead_id:
            lead = self.env["crm.lead"].browse(int(link_lead_id)).exists()
            if lead:
                tickets.write({"lead_ids": [(4, lead.id)]})
        link_sale_order_id = self.env.context.get("sd_link_sale_order_id")
        if link_sale_order_id:
            order = self.env["sale.order"].browse(int(link_sale_order_id)).exists()
            if order:
                tickets.write({"sale_order_ids": [(4, order.id)]})
        link_purchase_order_id = self.env.context.get("sd_link_purchase_order_id")
        if link_purchase_order_id:
            purchase = self.env["purchase.order"].browse(int(link_purchase_order_id)).exists()
            if purchase:
                tickets.write({"purchase_order_ids": [(4, purchase.id)]})
        link_invoice_id = self.env.context.get("sd_link_invoice_id")
        if link_invoice_id:
            invoice = self.env["account.move"].browse(int(link_invoice_id)).exists()
            if invoice:
                tickets.write({"invoice_ids": [(4, invoice.id)]})
        link_repair_order_id = self.env.context.get("sd_link_repair_order_id")
        if link_repair_order_id and tickets and self._user_can_write_repair_fields():
            repair = self.env["repair.order"].browse(int(link_repair_order_id)).exists()
            if repair:
                tickets.write({"repair_order_ids": [(4, repair.id)]})
        tickets._mark_as_viewed()
        for ticket in tickets:
            ticket._apply_ticket_type_followup_defaults()
            ticket._finalize_new_ticket()
            ticket._run_ai_analysis()
            ticket._notify_on_create()
            ticket._send_helpdesk_inbox_notification("create")
            ticket._record_create_routing_info()
            if self._get_config_bool("tv_service_desk.auto_add_customer_follower", True) and ticket.partner_id:
                ticket.message_subscribe(partner_ids=ticket.partner_id.ids)
        tickets_with_alarms = tickets.filtered("alarm_ids")
        tickets_with_alarms._sync_reminder_due_date_from_alarms()
        tickets_with_alarms._push_due_popup_reminders()
        tickets._sync_assigned_users_to_timesheet()
        return tickets

    @api.model
    def _get_alarm_timedelta(self, alarm):
        if alarm.reminder_unit == "minute":
            return timedelta(minutes=alarm.reminder_before)
        if alarm.reminder_unit == "hour":
            return timedelta(hours=alarm.reminder_before)
        if alarm.reminder_unit == "day":
            return timedelta(days=alarm.reminder_before)
        return timedelta()

    def _compute_reminder_due_date_from_alarms(self, alarms=None):
        self.ensure_one()
        alarms = alarms if alarms is not None else self.alarm_ids
        if not alarms:
            return False
        max_delta = max(self._get_alarm_timedelta(alarm) for alarm in alarms)
        return fields.Datetime.now() + max_delta

    def _sync_reminder_due_date_from_alarms(self):
        for ticket in self:
            due_date = (
                ticket._compute_reminder_due_date_from_alarms()
                if ticket.alarm_ids
                else False
            )
            ticket.with_context(sd_skip_alarm_sync=True).write({
                "reminder_due_date": due_date,
                "reminder_email_sent": False,
                "reminder_popup_shown": False,
                "reminder_popup_dismissed_user_ids": [(5, 0, 0)],
            })

    @api.onchange("alarm_ids")
    def _onchange_alarm_ids(self):
        if self.alarm_ids:
            self.reminder_due_date = self._compute_reminder_due_date_from_alarms()
        else:
            self.reminder_due_date = False

    def write(self, vals):
        if self.env.context.get("sd_skip_alarm_sync"):
            return super().write(vals)

        vals = self._sanitize_ticket_vals_for_access(vals)
        vals = self._strip_role_protected_vals(vals)
        if (
            "stage_id" in vals
            and not self._user_can_edit_ticket_stage()
            and not self.env.context.get("sd_allow_stage_write")
            and "replied_status" not in vals
        ):
            vals.pop("stage_id")
        vals = self._apply_replied_stage_sync_to_vals(vals)
        if (
            "replied_status" in vals
            and vals["replied_status"] in ("customer_replied", "staff_replied")
            and "replied_date" not in vals
        ):
            vals["replied_date"] = fields.Datetime.now()

        alarm_ids_changed = "alarm_ids" in vals
        reminder_manual = "reminder_due_date" in vals
        if "reminder_due_date" in vals:
            vals = dict(vals, **{
                "reminder_email_sent": False,
                "reminder_popup_shown": False,
                "reminder_popup_dismissed_user_ids": [(5, 0, 0)],
            })
        stage_changed = "stage_id" in vals
        old_stages = {t.id: t.stage_id for t in self} if stage_changed else {}
        old_user_ids = {t.id: t.user_id.id for t in self} if "user_id" in vals else {}
        res = super().write(vals)
        if stage_changed:
            stage_closed_id = self._get_config_stage_id("tv_service_desk.stage_closed_id", "stage_done")
            stage_cancel_id = self._get_config_stage_id("tv_service_desk.stage_cancel_id", "stage_cancelled")
            stage_reopened_id = self._get_config_stage_id("tv_service_desk.stage_reopened_id", "stage_reopened")

            for ticket in self:
                ticket._log_stage_change(old_stages.get(ticket.id), ticket.stage_id)

                followup_stage_id = self._get_config_stage_id(
                    "tv_service_desk.auto_followup_stage_id", "stage_waiting"
                )
                if followup_stage_id and ticket.stage_id.id == followup_stage_id:
                    ticket._maybe_trigger_auto_followup()

                is_closed = ticket.stage_id.id == stage_closed_id or (not stage_closed_id and ticket.stage_id.is_closed and ticket.stage_id.name != 'Cancelled')
                is_cancelled = ticket.stage_id.id == stage_cancel_id or (not stage_cancel_id and ticket.stage_id.name == 'Cancelled')
                is_reopened = ticket.stage_id.id == stage_reopened_id or (not stage_reopened_id and ticket.stage_id.name == 'Reopened')

                old_stage = old_stages.get(ticket.id)
                if old_stage and old_stage != ticket.stage_id and not is_closed and not is_cancelled:
                    ticket._send_helpdesk_inbox_notification(
                        "stage",
                        old_stage=old_stage,
                        new_stage=ticket.stage_id,
                    )

                if is_closed:
                    ticket._handle_ticket_closed()
                    ticket._send_helpdesk_inbox_notification("done")
                elif is_cancelled:
                    if not ticket.cancelled_date:
                        ticket.sudo().write({
                            'cancelled_date': fields.Datetime.now(),
                            'cancelled_by_id': self.env.user.id,
                        })
                    cancel_template = self.env.ref("tv_service_desk.mail_template_ticket_cancelled", raise_if_not_found=False)
                    if cancel_template and ticket.partner_id and not ticket._is_helpdesk_email_opted_out():
                        cancel_template.send_mail(ticket.id, force_send=False)
                    ticket._send_helpdesk_inbox_notification("cancel")
                elif is_reopened:
                    ticket.sudo().write({
                        'close_date': False,
                        'closed_by_id': False,
                        'closed_comment': False,
                        'cancelled_date': False,
                        'cancelled_by_id': False,
                        'cancelled_reason': False,
                    })
                    reopen_template = self.env.ref("tv_service_desk.mail_template_ticket_reopened", raise_if_not_found=False)
                    if reopen_template and ticket.partner_id and not ticket._is_helpdesk_email_opted_out():
                        reopen_template.send_mail(ticket.id, force_send=False)

        if "user_id" in vals:
            self._notify_whatsapp_assigned()
            self._notify_user_assigned(old_user_ids)
            for ticket in self.filtered("user_id"):
                old_uid = old_user_ids.get(ticket.id)
                if ticket.user_id.id != old_uid:
                    ticket._send_helpdesk_inbox_notification("assign")
        if "ticket_type_id" in vals:
            for ticket in self:
                ticket._apply_ticket_type_followup_defaults()
        if any(f in vals for f in ["partner_id", "ticket_type_id", "team_id", "priority_id", "category_id", "support_contract_id"]):
            for ticket in self:
                ticket._apply_sla_policy()
        if alarm_ids_changed and not reminder_manual:
            self._sync_reminder_due_date_from_alarms()
        if alarm_ids_changed or reminder_manual:
            self._push_due_popup_reminders()
        if "user_id" in vals or "assigned_user_ids" in vals:
            self._sync_assigned_users_to_timesheet()
        return res

    def _get_config_bool(self, key, default=False):
        return self.env["ir.config_parameter"].sudo().get_param(key, str(default)).lower() in ("1", "true", "yes")

    @api.model
    def _get_configured_mail_template(self, config_param_key, default_xmlid):
        return self.env["res.config.settings"].get_config_mail_template(
            config_param_key, default_xmlid
        )

    def _get_config_int(self, key, default=0):
        try:
            return int(self.env["ir.config_parameter"].sudo().get_param(key, default))
        except (TypeError, ValueError):
            return default

    def _get_config_stage_id(self, key, fallback_xmlid=None):
        return self.env["service.desk.stage"].get_config_stage_id(key, fallback_xmlid)

    def _apply_sla_policy(self):
        for ticket in self:
            ticket._write_sla_and_assignment_vals(ticket._prepare_sla_vals())

    def _prepare_sla_vals(self):
        self.ensure_one()
        policy = self._find_matching_sla_policy()
        if not policy:
            return {
                "sla_policy_id": False,
                "sla_deadline": False,
                "first_response_deadline": False,
            }
        return {
            "sla_policy_id": policy.id,
            "sla_deadline": policy._compute_deadline(self),
            "first_response_deadline": policy._compute_first_response_deadline(self),
        }

    def _prepare_auto_assign_vals(self):
        self.ensure_one()
        if not self.team_id or self.user_id:
            return {}
        assignee_id = self.team_id._get_next_assignee(self.partner_id, ticket=self)
        if assignee_id:
            return {"user_id": assignee_id}
        return {}

    def _write_sla_and_assignment_vals(self, vals):
        self.ensure_one()
        if vals:
            self.sudo().write(vals)

    def _finalize_new_ticket(self):
        for ticket in self:
            vals = {}
            vals.update(ticket._prepare_sla_vals())
            vals.update(ticket._prepare_auto_assign_vals())
            ticket._write_sla_and_assignment_vals(vals)

    def _sla_policy_match_score(self, policy):
        self.ensure_one()
        if not policy.matches_ticket(self):
            return -1
        score = 0
        if policy.team_id and policy.team_id == self.team_id:
            score += 100
        elif self.team_id and self.team_id in policy.team_ids:
            score += 80
        elif not policy.team_id and not policy.team_ids:
            score += 40
        if policy.priority_id and policy.priority_id == self.priority_id:
            score += 20
        if policy.ticket_type_id and policy.ticket_type_id == self.ticket_type_id:
            score += 20
        if policy.category_id and policy.category_id == self.category_id:
            score += 20
        if policy.time_hours:
            score += 5
        return score

    def _find_matching_sla_policy(self):
        self.ensure_one()
        Policy = self.env["service.desk.sla.policy"]
        domain = [("company_id", "in", [False, self.company_id.id]), ("active", "=", True)]
        policies = Policy.search(domain)
        if not policies:
            return Policy

        if self.team_id and self.team_id.sla_policy_ids:
            team_policies = self.team_id.sla_policy_ids.filtered(
                lambda policy: policy.active and policy.matches_ticket(self) and policy.time_hours > 0
            )
            if team_policies:
                return max(team_policies, key=lambda policy: self._sla_policy_match_score(policy))

        ranked = sorted(
            ((self._sla_policy_match_score(policy), policy) for policy in policies),
            key=lambda item: (-item[0], item[1].id),
        )
        for score, policy in ranked:
            if score >= 0 and policy.time_hours > 0:
                return policy
        return Policy

    def _maybe_auto_assign(self):
        for ticket in self.filtered(lambda t: t.team_id and not t.user_id):
            vals = ticket._prepare_auto_assign_vals()
            if vals:
                ticket._write_sla_and_assignment_vals(vals)

    def _get_create_assign_status_message(self):
        self.ensure_one()
        team = self.team_id
        if not team:
            return _("No team configured on this ticket.")
        if not team._uses_auto_assign():
            if self.user_id:
                return _("Auto-assign is disabled. Assigned to %s.") % self.user_id.name
            return _("Auto-assign is disabled. Team Leader or Manager will assign manually.")
        if self.user_id:
            return _("Auto-assigned to %s.") % self.user_id.name
        return _("Auto-assign is enabled but no team member was available.")

    def _get_create_notify_summary_message(self):
        self.ensure_one()
        parts = []
        notify_users = self._get_helpdesk_notification_recipients("create")
        if self.team_head_id:
            if self.team_head_id in notify_users:
                parts.append(_("Team Leader %s was notified.") % self.team_head_id.name)
            else:
                parts.append(
                    _("Team Leader %s was not notified (preference disabled).")
                    % self.team_head_id.name
                )
        assignees = self._get_assignment_notify_users(exclude_creator=True)
        if assignees:
            parts.append(_("Assignee email sent to %s.") % ", ".join(assignees.mapped("name")))
        elif self.user_id:
            parts.append(_("No assignee email was sent."))
        if not parts:
            return _("No internal notifications were sent.")
        return " ".join(parts)

    def _record_create_routing_info(self):
        for ticket in self:
            ticket.sudo().write({
                "sd_create_assign_status": ticket._get_create_assign_status_message(),
                "sd_create_notify_summary": ticket._get_create_notify_summary_message(),
            })

    def _sync_assigned_users_to_timesheet(self):
        for ticket in self:
            try:
                ticket_sudo = ticket.sudo()
                assigned_users = ticket_sudo.user_id | ticket_sudo.assigned_user_ids
                if not assigned_users:
                    continue

                existing_user_ids = ticket_sudo.timesheet_ids.mapped("user_id")
                project_id = ticket_sudo._get_default_timesheet_project_id()
                if not project_id:
                    project_id = self.env["project.project"].sudo().search([], limit=1).id
                if not project_id:
                    continue

                vals_list = []
                for user in assigned_users:
                    if user not in existing_user_ids:
                        employee = user.employee_id or self.env["hr.employee"].sudo().search([("user_id", "=", user.id)], limit=1)
                        if not employee:
                            try:
                                employee = self.env["hr.employee"].sudo().create({
                                    "name": user.name,
                                    "user_id": user.id,
                                    "work_email": user.email,
                                })
                            except Exception:
                                employee = False

                        description = "/"
                        if ticket_sudo._get_config_bool("tv_service_desk.default_timesheet_description", default=True):
                            description = "%s-%s" % (employee.name if employee else user.name, ticket_sudo.name)

                        package = False
                        if ticket_sudo.partner_id:
                            package = self.env["service.desk.customer.hour.package"].sudo()._get_open_package(
                                ticket_sudo.partner_id
                            )

                        vals_list.append({
                            "name": description,
                            "sd_ticket_id": ticket_sudo.id,
                            "sd_hour_package_id": package.id if package else False,
                            "user_id": user.id,
                            "employee_id": employee.id if employee else False,
                            "project_id": project_id,
                            "date": fields.Date.context_today(ticket_sudo),
                            "unit_amount": 0.0,
                        })
                if vals_list:
                    self.env["account.analytic.line"].sudo().create(vals_list)
            except Exception:
                pass

    def _is_helpdesk_email_opted_out(self):
        self.ensure_one()
        if not self.partner_id:
            return False
        return self.partner_id._sd_is_helpdesk_email_opted_out()

    def _get_whatsapp_config(self):
        self.ensure_one()
        return self.env["service.desk.whatsapp.config"].sudo().search(
            [("company_id", "=", self.company_id.id), ("active", "=", True)],
            limit=1,
        )

    def _get_assignment_notify_users(self, exclude_creator=False):
        self.ensure_one()
        users = self.assigned_user_ids | self.user_id
        if exclude_creator and self.create_uid:
            users = users.filtered(lambda user: user.id != self.create_uid.id)
        return users.filtered(lambda user: user.email_formatted and not user.share)

    def _notify_on_create(self):
        if not self._can_send_helpdesk_email():
            return
        template = self.env.ref("tv_service_desk.mail_template_ticket_created_customer", raise_if_not_found=False)
        for ticket in self.filtered(lambda t: t.partner_id and not t._is_helpdesk_email_opted_out()):
            if template:
                template.send_mail(ticket.id, force_send=False)
        assign_template = self._get_configured_mail_template(
            "tv_service_desk.allocation_mail_template_id",
            "tv_service_desk.mail_template_ticket_assigned",
        )
        for ticket in self:
            assignees = ticket._get_assignment_notify_users(exclude_creator=True)
            if assign_template and assignees:
                assign_template.send_mail(
                    ticket.id,
                    force_send=False,
                    email_values={
                        "email_to": ",".join(assignees.mapped("email_formatted")),
                    },
                )

    def _log_stage_change(self, old_stage, new_stage):
        self.ensure_one()
        if not new_stage or old_stage == new_stage:
            return
        duration = 0.0
        last_log = self.stage_log_ids[:1]
        if last_log:
            duration = (fields.Datetime.now() - last_log.change_date).total_seconds() / 3600.0
        self.env["service.desk.stage.log"].sudo().create({
            "ticket_id": self.id,
            "old_stage_id": old_stage.id if old_stage else False,
            "new_stage_id": new_stage.id,
            "duration_hours": duration,
        })
        if new_stage.mail_template_id and self.partner_id and not self._is_helpdesk_email_opted_out():
            new_stage.mail_template_id.send_mail(self.id, force_send=False)

    def _notify_whatsapp_assigned(self):
        for ticket in self.filtered(lambda t: t.user_id and t.partner_id):
            config = ticket._get_whatsapp_config()
            if config and config.notify_on_assign:
                config._send_whatsapp_message(
                    ticket.partner_id,
                    _("Ticket %s has been assigned to %s.") % (ticket.name, ticket.user_id.name),
                )

    def _handle_ticket_closed(self):
        self.ensure_one()
        if not self.close_date:
            self.sudo().write({
                'close_date': fields.Datetime.now(),
                'closed_by_id': self.env.user.id,
            })
        config = self._get_whatsapp_config()
        if config and config.notify_on_close and self.partner_id:
            config._send_whatsapp_message(
                self.partner_id,
                _("Ticket %s has been closed.") % self.name,
            )
        if self._get_config_bool("tv_service_desk.feedback_on_close", True):
            template = self.env.ref(
                "tv_service_desk.mail_template_ticket_feedback_request",
                raise_if_not_found=False,
            )
            if template and self.partner_id and not self._is_helpdesk_email_opted_out():
                template.send_mail(self.id, force_send=False)

    def _notify_user_assigned(self, old_user_ids):
        assign_template = self._get_configured_mail_template(
            "tv_service_desk.allocation_mail_template_id",
            "tv_service_desk.mail_template_ticket_assigned",
        )
        for ticket in self.filtered("user_id"):
            old_uid = old_user_ids.get(ticket.id)
            if assign_template and ticket.user_id.id != old_uid:
                assign_template.send_mail(ticket.id, force_send=False)

    def _get_helpdesk_group_users(self, group):
        """Return internal users belonging to a security group (Odoo 19 compatible)."""
        if not group:
            return self.env["res.users"]
        return self.env["res.users"].search([
            ("all_group_ids", "in", group.ids),
            ("share", "=", False),
        ])

    def _get_helpdesk_notification_recipients(self, event):
        config_keys = {
            "create": "tv_service_desk.notify_on_create",
            "assign": "tv_service_desk.notify_on_assign",
            "done": "tv_service_desk.notify_on_done",
            "cancel": "tv_service_desk.notify_on_cancel",
            "stage": "tv_service_desk.notify_on_stage_change",
        }
        if not self._get_config_bool(config_keys[event], True):
            return self.env["res.users"]
        users = self.env["res.users"]
        manager_group = self.env.ref("tv_service_desk.group_service_desk_manager", raise_if_not_found=False)
        manager_users = self._get_helpdesk_group_users(manager_group)
        if event == "create":
            assignees = self.user_id | self.assigned_user_ids
            watchers = self.team_head_id | manager_users
            if self.team_id:
                watchers |= self.team_id.member_ids
            if self.create_uid:
                watchers = watchers.filtered(lambda user: user.id != self.create_uid.id)
            users = assignees | watchers
        elif event == "assign":
            users = self.user_id
        elif event in ("done", "cancel"):
            users = self.user_id | self.assigned_user_ids | self.team_head_id
        elif event == "stage":
            users = self.team_head_id | manager_users
            users = users.filtered(lambda user: user.id != self.env.user.id)
        return users.filtered(
            lambda user: user._wants_helpdesk_notification(event)
            and user.partner_id
            and not user.share
        )

    def _send_helpdesk_inbox_notification(self, event, old_stage=None, new_stage=None):
        self.ensure_one()
        titles = {
            "create": _("New Ticket Created"),
            "assign": _("Ticket Assigned"),
            "done": _("Ticket Done"),
            "cancel": _("Ticket Cancelled"),
            "stage": _("Ticket Stage Changed"),
        }
        users = self._get_helpdesk_notification_recipients(event)
        partner_ids = users.mapped("partner_id").ids
        if not partner_ids:
            return
        title = titles[event]
        if event == "stage" and old_stage and new_stage:
            body = Markup(
                "<p><strong>%s</strong></p><p>%s → %s</p>"
            ) % (
                escape(self.display_name),
                escape(old_stage.display_name),
                escape(new_stage.display_name),
            )
        else:
            body = Markup("<p>%s</p>") % escape(self.display_name)
        self.message_notify(
            subject=title,
            body=body,
            partner_ids=partner_ids,
            model=self._name,
            res_id=self.id,
            model_description=self.env["ir.model"]._get(self._name).display_name,
            notify_author_mention=True,
        )

    @api.model
    def _can_send_helpdesk_email(self):
        return bool(self.env["ir.mail_server"].sudo().search([], limit=1))

    def action_cancel_ticket(self):
        self.ensure_one()
        if self.stage_id and self.stage_id.is_closed:
            raise UserError(_("This ticket is already closed or cancelled."))
        cancel_stage_id = self._get_config_stage_id("tv_service_desk.stage_cancel_id", "stage_cancelled")
        cancel_stage = (
            self.env["service.desk.stage"].browse(cancel_stage_id).exists()
            if cancel_stage_id
            else self.env["service.desk.stage"].search([("name", "=", "Cancelled")], limit=1)
        )
        if not cancel_stage:
            raise UserError(_("Cancelled stage is not configured."))
        self.with_context(sd_allow_stage_write=True).write({"stage_id": cancel_stage.id})
        return True

    def _notify_customer_portal_view(self):
        """Notify assigned staff when a customer opens the ticket on the portal."""
        self.ensure_one()
        if not self._get_config_bool("tv_service_desk.email_on_customer_view"):
            return
        recipients = (self.user_id | self.assigned_user_ids).filtered(lambda user: user.partner_id)
        if not recipients:
            return
        body = _("Customer %(customer)s viewed ticket %(ticket)s on the portal.") % {
            "customer": self.partner_id.display_name or _("Customer"),
            "ticket": self.name,
        }
        self.message_post(
            body=body,
            message_type="notification",
            subtype_xmlid="mail.mt_note",
            partner_ids=recipients.mapped("partner_id").ids,
            email_layout_xmlid="mail.mail_notification_light",
        )

    def _message_post_after_hook(self, message, msg_vals):
        res = super()._message_post_after_hook(message, msg_vals)
        if message.message_type not in ("comment", "email", "email_outgoing"):
            return res
        if message.subtype_id and message.subtype_id.internal:
            return res

        author = message.author_id or self.env.user.partner_id
        for ticket in self:
            extra_vals = {}
            if message.attachment_ids:
                extra_vals["attachment_ids"] = [
                    (4, attachment.id) for attachment in message.attachment_ids
                ]
            if ticket._is_customer_message_author(author):
                ticket._set_replied_status("customer_replied", extra_vals=extra_vals or None)
            elif ticket._is_staff_message_author(author):
                if not ticket.first_response_date:
                    extra_vals["first_response_date"] = fields.Datetime.now()
                ticket._set_replied_status("staff_replied", extra_vals=extra_vals or None)
            elif extra_vals:
                ticket.write(extra_vals)
        return res

    def action_mark_viewed(self):
        self._mark_as_viewed()

    def _prepare_crm_record_name(self):
        self.ensure_one()
        partner_name = self.partner_id.display_name if self.partner_id else self.subject
        return _("%s's opportunity") % (partner_name or _("Customer"))

    def _get_crm_create_context(self, record_type):
        self.ensure_one()
        partner = self.partner_id
        return {
            "default_type": record_type,
            "default_name": self._prepare_crm_record_name(),
            "default_partner_id": partner.id if partner else False,
            "default_contact_name": self.person_name or (partner.name if partner else False),
            "default_email_from": self.partner_email or (partner.email if partner else False),
            "default_phone": self.partner_phone or (partner.phone if partner else False),
            "default_mobile": self.partner_phone or (partner.mobile if partner else False),
            "default_user_id": self.user_id.id,
            "default_team_id": self.team_id.crm_team_id.id if getattr(self.team_id, "crm_team_id", False) else False,
            "sd_link_ticket_id": self.id,
        }

    def action_open_create_lead_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Lead"),
            "res_model": "crm.lead",
            "view_mode": "form",
            "target": "new",
            "context": self._get_crm_create_context("lead"),
        }

    def action_open_create_opportunity_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Opportunity"),
            "res_model": "crm.lead",
            "view_mode": "form",
            "target": "new",
            "context": self._get_crm_create_context("opportunity"),
        }

    def _prepare_sale_order_lines_from_products(self):
        self.ensure_one()
        return [
            (0, 0, {"product_id": product.id, "product_uom_qty": 1.0})
            for product in self.product_ids
        ]

    def _get_repair_part_products(self):
        self.ensure_one()
        products = self.product_ids
        if self.repair_product_id:
            products |= self.repair_product_id
        return products

    def _prepare_repair_move_lines_from_products(self):
        self.ensure_one()
        return [
            (0, 0, {
                "product_id": product.id,
                "product_uom_qty": 1.0,
                "repair_line_type": "add",
            })
            for product in self._get_repair_part_products()
        ]

    def action_open_create_sale_wizard(self):
        self.ensure_one()
        if not self.product_ids:
            raise ValidationError(_("Please select product for create Sale Order"))
        return {
            "type": "ir.actions.act_window",
            "name": _("Sale Order"),
            "res_model": "sale.order",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_partner_id": self.partner_id.id if self.partner_id else False,
                "default_order_line": self._prepare_sale_order_lines_from_products(),
                "default_user_id": self.user_id.id,
                "sd_link_ticket_id": self.id,
            },
        }

    def _prepare_purchase_order_lines_from_products(self):
        self.ensure_one()
        return [
            (0, 0, {"product_id": product.id, "product_qty": 1.0})
            for product in self.product_ids
        ]

    def action_open_create_purchase_wizard(self):
        self.ensure_one()
        if not self.product_ids:
            raise ValidationError(_("Please select product for create Purchase Order"))
        return {
            "type": "ir.actions.act_window",
            "name": _("Purchase Order"),
            "res_model": "purchase.order",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_partner_id": self.partner_id.id if self.partner_id else False,
                "default_order_line": self._prepare_purchase_order_lines_from_products(),
                "default_user_id": self.user_id.id,
                "sd_link_ticket_id": self.id,
            },
        }

    def _prepare_invoice_lines_from_products(self):
        self.ensure_one()
        lines = []
        for product in self.product_ids:
            line_vals = {
                "product_id": product.id,
                "quantity": 1,
                "price_unit": product.lst_price,
            }
            if hasattr(product, "get_product_multiline_description_sale"):
                line_vals["name"] = product.get_product_multiline_description_sale()
            else:
                line_vals["name"] = product.display_name
            lines.append((0, 0, line_vals))
        return lines

    def _prepare_invoice_move_defaults(self):
        """Return account.move header defaults required before line onchanges run."""
        self.ensure_one()
        company = self.company_id or self.env.company
        partner = self.partner_id
        currency = (
            partner.currency_id
            or partner.property_product_pricelist.currency_id
            if partner
            else False
        ) or company.currency_id
        journal = self.env["account.journal"].search(
            [("company_id", "=", company.id), ("type", "=", "sale")],
            limit=1,
        )
        return {
            "move_type": "out_invoice",
            "partner_id": partner.id if partner else False,
            "company_id": company.id,
            "currency_id": currency.id,
            "journal_id": journal.id if journal else False,
            "invoice_user_id": self.user_id.id,
            "invoice_line_ids": self._prepare_invoice_lines_from_products(),
        }

    def action_open_create_invoice_wizard(self):
        self.ensure_one()
        if not self.product_ids:
            raise ValidationError(_("Please select product for create Invoice"))
        defaults = self._prepare_invoice_move_defaults()
        context = {"sd_link_ticket_id": self.id}
        for key, value in defaults.items():
            context[f"default_{key}"] = value
        return {
            "type": "ir.actions.act_window",
            "name": _("Customer Invoice"),
            "res_model": "account.move",
            "view_mode": "form",
            "target": "new",
            "context": context,
        }

    def action_open_create_task_wizard(self):
        self.ensure_one()
        assignees = self.user_id | self.assigned_user_ids
        return {
            "type": "ir.actions.act_window",
            "name": _("Task"),
            "res_model": "project.task",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_name": self.name,
                "default_project_id": self._get_default_timesheet_project_id(),
                "default_partner_id": self.partner_id.id,
                "default_user_ids": [(6, 0, assignees.ids)],
                "default_description": self.description,
                "default_date_deadline": self.reminder_due_date,
                "sd_link_ticket_id": self.id,
                "sd_copy_ticket_attachments": True,
            },
        }

    def _open_bridge_wizard(self, model, extra_context=None):
        self.ensure_one()
        ctx = {
            "default_ticket_id": self.id,
            "default_partner_id": self.partner_id.id,
            "default_product_ids": [(6, 0, self.product_ids.ids)],
        }
        if extra_context:
            ctx.update(extra_context)
        return {
            "type": "ir.actions.act_window",
            "res_model": model,
            "view_mode": "form",
            "target": "new",
            "context": ctx,
        }

    def action_approve_ticket(self):
        self.ensure_one()
        vals = {"approved": True}
        current_stage = self.stage_id.name
        if current_stage == "New":
            in_progress = self.env["service.desk.stage"].search([("name", "=", "In Progress")], limit=1)
            if in_progress:
                vals["stage_id"] = in_progress.id
        elif current_stage == "In Progress":
            done_stage = self.env["service.desk.stage"].search([("name", "=", "Done")], limit=1)
            if done_stage:
                vals["stage_id"] = done_stage.id
        self.write(vals)

    def action_reopen_ticket(self):
        self.ensure_one()
        if not self._is_closed_or_cancelled_stage():
            raise UserError(_("Only closed or cancelled tickets can be reopened."))
        reopened = self.env["service.desk.stage"].search([("name", "=", "Reopened")], limit=1)
        if not reopened:
            raise UserError(_("Reopened stage is not configured."))
        self.with_context(sd_allow_stage_write=True).write(
            {"stage_id": reopened.id, "close_date": False}
        )

    def action_preview_ticket(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": self.get_portal_url(),
            "target": "new",
        }

    def _get_user_active_timer_line(self, user=None):
        self.ensure_one()
        if not self._user_has_ticket_timesheet_access():
            return self.env["account.analytic.line"]
        user = user or self.env.user
        return self.timesheet_ids.filtered(
            lambda line: line.user_id == user and line.start_date and not line.end_date
        )[:1]

    @api.model
    def _get_default_timesheet_project_id(self):
        project_id = int(
            self.env["ir.config_parameter"].sudo().get_param(
                "tv_service_desk.default_timesheet_project_id", 0
            )
        )
        return project_id or False

    def _get_default_timesheet_description(self):
        self.ensure_one()
        if not self._get_config_bool("tv_service_desk.default_timesheet_description", default=True):
            return "/"
        employee = self.env.user.employee_id
        return "%s-%s" % (employee.name or self.env.user.name, self.name)

    def _prepare_timer_line_vals(self):
        self.ensure_one()
        employee = self.env.user.employee_id
        package = False
        if self.partner_id:
            package = self.env["service.desk.customer.hour.package"]._get_open_package(
                self.partner_id
            )
        return {
            "name": self._get_default_timesheet_description(),
            "sd_ticket_id": self.id,
            "sd_hour_package_id": package.id if package else False,
            "user_id": self.env.user.id,
            "employee_id": employee.id if employee else False,
            "start_date": fields.Datetime.now(),
            "project_id": self._get_default_timesheet_project_id(),
            "date": fields.Date.context_today(self),
            "unit_amount": 0.0,
        }

    @api.model
    def get_user_active_timer_info(self):
        if not self._user_has_ticket_timesheet_access():
            return False
        line = self.env["account.analytic.line"].search([
            ("user_id", "=", self.env.user.id),
            ("sd_ticket_id", "!=", False),
            ("start_date", "!=", False),
            ("end_date", "=", False),
        ], limit=1)
        if not line:
            return False
        return {
            "ticket_id": line.sd_ticket_id.id,
            "ticket_name": line.sd_ticket_id.name,
            "ticket_subject": line.sd_ticket_id.subject or line.sd_ticket_id.name,
            "start": fields.Datetime.to_string(line.start_date),
        }

    def action_start_ticket(self):
        self.ensure_one()
        if not self.approved:
            raise UserError(_("Please approve the ticket before starting it."))
        if self._user_has_ticket_timesheet_access():
            self.action_start_timer()
        in_progress = self.env["service.desk.stage"].search([("name", "=", "In Progress")], limit=1)
        if in_progress:
            self.write({"stage_id": in_progress.id})

    def action_end_ticket(self):
        self.ensure_one()
        line = self._get_user_active_timer_line()
        if not line:
            raise UserError(_("No running timer found for your user on this ticket."))
        return {
            "type": "ir.actions.act_window",
            "name": _("End Ticket"),
            "res_model": "service.desk.end.ticket.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_ticket_id": self.id,
                "default_timesheet_line_id": line.id,
            },
        }

    def _get_whatsapp_message_config(self):
        return self.env["res.config.settings"].get_whatsapp_message_config()

    def _whatsapp_config_send_ticket_url(self):
        return self._get_whatsapp_message_config().get("send_ticket_url")

    def _whatsapp_config_send_report_url(self):
        return self._get_whatsapp_message_config().get("send_report_url")

    def _whatsapp_config_signature(self):
        return self._get_whatsapp_message_config().get("signature")

    def _whatsapp_config_product_details(self):
        return self._get_whatsapp_message_config().get("product_details")

    def _get_partner_mobile(self):
        self.ensure_one()
        return self._get_partner_mobile_number(
            partner=self.partner_id,
            partner_phone=self.partner_phone,
        )

    def _ensure_whatsapp_mobile(self):
        self.ensure_one()
        if not self._get_partner_mobile():
            raise UserError(_("Partner Mobile Number Not Exist !"))

    def _get_whatsapp_access_token(self):
        self.ensure_one()
        if not self.access_token:
            self._portal_ensure_token()
        return self.access_token

    def get_whatsapp_download_url(self):
        self.ensure_one()
        token = self._get_whatsapp_access_token()
        return "%s/download/ht/%s?access_token=%s" % (self.get_base_url(), self.id, token)

    def get_portal_pdf_download_url(self):
        """Return portal-safe PDF download URL (includes access token when available)."""
        self.ensure_one()
        if not self.access_token:
            self.sudo()._portal_ensure_token()
        return "/download/ht/%s?access_token=%s" % (self.id, self.access_token)

    def get_whatsapp_history_url(self):
        self.ensure_one()
        token = self._get_whatsapp_access_token()
        return "%s/my/sh_tickets/%s?access_token=%s" % (self.get_base_url(), self.id, token)

    def _get_whatsapp_message_subject(self):
        self.ensure_one()
        company_name = self.company_id.name or ""
        return "%s (Ref %s)" % (company_name, self.name)

    def _build_whatsapp_message_lines(self, use_whatsapp_format=False):
        self.ensure_one()
        config = self._get_whatsapp_message_config()
        partner_name = self.partner_id.name or "Customer"
        ticket_name = self.name
        company_name = self.company_id.name or ""
        signature = self.env.user.sd_whatsapp_signature or ""
        lines = []

        lines.append("Dear %s ," % partner_name)
        lines.append("")
        if use_whatsapp_format:
            lines.append("Here is the your Ticket * %s *" % ticket_name)
        else:
            lines.append("Here is the your Ticket %s" % ticket_name)
        lines.append("")

        if config.get("product_details") and self.product_ids:
            for product in self.product_ids:
                lines.append(product.display_name)
            lines.append("")

        if use_whatsapp_format:
            lines.append("from * %s *" % company_name)
        else:
            lines.append("From %s" % company_name)
        lines.append("")

        if config.get("send_ticket_url"):
            download_url = self.get_whatsapp_download_url()
            if use_whatsapp_format:
                lines.append("*Click here to download Ticket Document* :- %s" % download_url)
            else:
                lines.append("Click here to download Ticket Document :- %s" % download_url)
            lines.append("")

        if config.get("send_report_url"):
            history_url = self.get_whatsapp_history_url()
            if use_whatsapp_format:
                lines.append("*Click here to See Ticket History* :- %s" % history_url)
            else:
                lines.append("Click here to See Ticket History :- %s" % history_url)
            lines.append("")

        if config.get("signature") and signature:
            if use_whatsapp_format:
                lines.append("* %s" % signature)
            else:
                lines.append(signature)

        while lines and lines[-1] == "":
            lines.pop()
        return lines

    def _build_whatsapp_message_plain(self):
        self.ensure_one()
        return "\n".join(self._build_whatsapp_message_lines(use_whatsapp_format=False))

    def _build_whatsapp_message_html(self):
        self.ensure_one()
        lines = self._build_whatsapp_message_lines(use_whatsapp_format=True)
        return "<p>%s</p>" % "<br/>".join(lines)

    def _format_whatsapp_url_text(self, plain_body):
        self.ensure_one()
        return plain_body.replace("\n", "%0A")

    def action_send_by_whatsapp(self):
        self.ensure_one()
        self._ensure_whatsapp_mobile()
        return {
            "type": "ir.actions.act_window",
            "name": _("Send Message"),
            "res_model": "service.desk.whatsapp.send.wizard",
            "view_mode": "form",
            "views": [[False, "form"]],
            "target": "new",
            "context": {"default_ticket_id": self.id},
        }

    def action_view_attachments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Attachments"),
            "res_model": "ir.attachment",
            "view_mode": "list,form",
            "domain": [("res_model", "=", self._name), ("res_id", "=", self.id)],
            "context": {
                "default_res_model": self._name,
                "default_res_id": self.id,
            },
        }

    def action_open_reply_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Reply"),
            "res_model": "service.desk.reply.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_ticket_id": self.id},
        }

    def action_start_timer(self):
        self.ensure_one()
        if not self._user_has_ticket_timesheet_access():
            raise UserError(_("You do not have permission to use ticket timers."))
        if self._get_user_active_timer_line():
            raise UserError(_("Timer is already running on this ticket."))
        allow_parallel = self._get_config_bool("tv_service_desk.allow_parallel_timers", default=True)
        if not allow_parallel:
            other_line = self.env["account.analytic.line"].search([
                ("user_id", "=", self.env.user.id),
                ("sd_ticket_id", "!=", False),
                ("start_date", "!=", False),
                ("end_date", "=", False),
                ("sd_ticket_id", "!=", self.id),
            ], limit=1)
            if other_line:
                raise UserError(_("You can not start 2 tickets at same time !"))
        line = self.env["account.analytic.line"].create(self._prepare_timer_line_vals())
        self.write({
            "timer_user_id": self.env.user.id,
            "timer_start": line.start_date,
        })
        return True

    def action_stop_timer(self):
        self.ensure_one()
        if not self._user_has_ticket_timesheet_access():
            return False
        line = self._get_user_active_timer_line()
        if not line:
            raise UserError(_("No running timer found for your user on this ticket."))
        now = fields.Datetime.now()
        elapsed = (now - line.start_date).total_seconds() / 3600.0
        line.write({
            "end_date": now,
            "unit_amount": round(elapsed, 2),
        })
        if self.timer_user_id == self.env.user:
            self.write({"timer_user_id": False, "timer_start": False})
        return True

    def action_print_ticket(self):
        return self.env.ref("tv_service_desk.action_report_service_desk_ticket").report_action(self)

    @api.model
    def _get_dashboard_stage_ids(self, param_key):
        return self.env["res.config.settings"].get_dashboard_stage_ids(param_key)

    @api.model
    def _get_dashboard_pager_limit(self):
        return self._get_config_int("tv_service_desk.dashboard_pager_limit", 4)

    @api.model
    def _get_stage_color_map(self):
        return [
            "#F06050", "#F4A460", "#F7CD1F", "#6CC1ED", "#814968",
            "#EB7E7F", "#2C8397", "#475577", "#D6145F", "#30C381", "#9365B8", "#948686",
        ]

    @api.model
    def build_dashboard_base_domain(self, filters=None):
        """Public RPC entry point for dashboard filter domain building."""
        return self._build_dashboard_base_domain(filters)

    @api.model
    def _build_dashboard_base_domain(self, filters=None):
        """Build ticket domain from dashboard advanced filters."""
        from datetime import datetime, time, timedelta

        filters = filters or {}
        domain = []

        filter_type = filters.get("filter_type") or "all"
        date_start = filters.get("date_start")
        date_end = filters.get("date_end")

        if filter_type == "custom" and date_start and date_end:
            start_date = fields.Date.to_date(date_start)
            end_date = fields.Date.to_date(date_end)
            start_dt = fields.Datetime.to_string(datetime.combine(start_date, time.min))
            end_dt = fields.Datetime.to_string(datetime.combine(end_date, time.max))
            domain.append(("create_date", ">=", start_dt))
            domain.append(("create_date", "<=", end_dt))
        elif filter_type == "today":
            today = fields.Date.context_today(self)
            domain.append(("create_date", ">=", fields.Datetime.to_string(datetime.combine(today, time.min))))
            domain.append(("create_date", "<=", fields.Datetime.to_string(datetime.combine(today, time.max))))
        elif filter_type == "week":
            today = fields.Date.context_today(self)
            start_of_week = today - timedelta(days=today.weekday())
            domain.append(("create_date", ">=", fields.Datetime.to_string(datetime.combine(start_of_week, time.min))))
        elif filter_type == "month":
            today = fields.Date.context_today(self)
            start_of_month = today.replace(day=1)
            domain.append(("create_date", ">=", fields.Datetime.to_string(datetime.combine(start_of_month, time.min))))
        elif filter_type == "year":
            today = fields.Date.context_today(self)
            start_of_year = today.replace(month=1, day=1)
            domain.append(("create_date", ">=", fields.Datetime.to_string(datetime.combine(start_of_year, time.min))))

        team_leader_id = filters.get("team_leader_id")
        if team_leader_id:
            domain.append(("team_id.leader_id", "=", int(team_leader_id)))

        team_id = filters.get("team_id")
        if team_id:
            domain.append(("team_id", "=", int(team_id)))

        assigned_user_id = filters.get("assigned_user_id")
        if assigned_user_id:
            domain.append(("user_id", "=", int(assigned_user_id)))

        if filters.get("my_tickets"):
            domain.extend([
                "|",
                ("user_id", "=", self.env.user.id),
                ("assigned_user_ids", "in", [self.env.user.id]),
            ])
        return domain

    @api.model
    def get_dashboard_filter_options(self):
        """Return dropdown data and UI config for the dashboard filter panel."""
        Team = self.env["service.desk.team"]
        teams = Team.search([("active", "=", True)], order="name")
        team_leaders = teams.mapped("leader_id").filtered(lambda user: user.active)
        assigned_users = self.env["res.users"].search([
            ("share", "=", False),
            ("active", "=", True),
        ], order="name")

        return {
            "team_leaders": [
                {"id": user.id, "name": user.name} for user in team_leaders
            ],
            "teams": [
                {"id": team.id, "name": team.name} for team in teams
            ],
            "assigned_users": [
                {"id": user.id, "name": user.name} for user in assigned_users
            ],
            "config": self.env["res.config.settings"].get_dashboard_ui_config(),
        }

    @api.model
    def _serialize_ticket_row(self, ticket):
        return {
            'id': ticket.id,
            'name': ticket.name,
            'subject': ticket.subject or '',
            'partner_name': ticket.partner_id.name or 'Public Customer',
            'mobile': ticket._get_partner_mobile() or '',
            'priority': ticket.priority_id.name or 'Normal',
            'priority_weight': ticket.priority_id.weight or 2,
            'user_name': ticket.user_id.name or 'Unassigned',
            'stage_name': ticket.stage_id.name or '',
            'sla_status': ticket.sla_status or 'none',
            'create_date': ticket.create_date.strftime('%Y-%m-%d %H:%M') if ticket.create_date else '',
        }

    @api.model
    def _parse_feedback_ratings(self, tickets):
        ratings = []
        for ticket in tickets:
            value = ticket.feedback_rating
            if not value or value == "0":
                continue
            try:
                ratings.append(int(value))
            except (TypeError, ValueError):
                continue
        return ratings

    @api.model
    def _get_dashboard_tracking_values(self, message):
        """mail.tracking.value is restricted to Settings users; sudo for dashboard feed."""
        return message.sudo().tracking_value_ids

    @api.model
    def get_dashboard_data(self, filters=None, table_offsets=None):
        """Return KPI counts, stage tables and activities based on dashboard filters."""
        filters = filters or {}
        if filters.get("my_tickets") is None:
            filters = dict(filters, my_tickets=False)
        domain = self._build_dashboard_base_domain(filters)
        pager_limit = self._get_dashboard_pager_limit()
        table_offsets = table_offsets or {}
        colors = self._get_stage_color_map()

        filter_stage_ids = self._get_dashboard_stage_ids("tv_service_desk.dashboard_filter_stage_ids")
        table_stage_ids = self._get_dashboard_stage_ids("tv_service_desk.dashboard_table_stage_ids")
        filter_stages = self.env["service.desk.stage"].browse(filter_stage_ids).exists()
        table_stages = self.env["service.desk.stage"].browse(table_stage_ids).exists()

        # KPI Counts
        total_tickets = self.search_count(domain)
        
        open_tickets = self.search_count(domain + [
            ('stage_id.is_closed', '=', False),
            ('stage_id.name', 'in', ['New', 'Open'])
        ])
        
        in_progress_tickets = self.search_count(domain + [
            ('stage_id.is_closed', '=', False),
            ('stage_id.name', 'ilike', 'Progress')
        ])
        
        waiting_customer_tickets = self.search_count(domain + [
            ('stage_id.name', 'ilike', 'Waiting')
        ])
        
        resolved_tickets = self.search_count(domain + [
            ('stage_id.name', 'ilike', 'Resolved')
        ])
        
        closed_tickets = self.search_count(domain + [
            ('stage_id.is_closed', '=', True)
        ])
        
        my_tickets_count = self.search_count(domain + [
            '|',
            ('user_id', '=', self.env.user.id),
            ('assigned_user_ids', 'in', [self.env.user.id]),
        ])
        
        sla_breached = self.search_count(domain + [
            ('sla_status', '=', 'failed')
        ])
        
        rated_tickets = self.search(domain + [
            ('feedback_rating', '!=', False),
            ('feedback_rating', '!=', '0')
        ])
        ratings = self._parse_feedback_ratings(rated_tickets)
        avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else 0.0
        
        active_contracts = 0
        low_balance_contracts = 0
        if self.env.user.has_group("tv_service_desk.group_service_desk_manager"):
            Contract = self.env["service.desk.support.contract"]
            active_contracts = Contract.search_count([("state", "=", "active")])
            low_balance_contracts = Contract.search_count([
                ("state", "=", "active"),
                ("remaining_hours", "<=", 2),
            ])
        
        # Configured filter stage KPI cards
        filter_stage_kpis = []
        for stage in filter_stages:
            color_index = stage.color if stage.color is not None else 0
            filter_stage_kpis.append({
                'id': stage.id,
                'name': stage.name,
                'count': self.search_count(domain + [('stage_id', '=', stage.id)]),
                'color': colors[color_index % len(colors)],
                'is_closed': stage.is_closed,
            })

        # Configured stage tables with pager
        stage_tables = []
        for stage in table_stages:
            stage_domain = domain + [('stage_id', '=', stage.id)]
            total_count = self.search_count(stage_domain)
            offset = int(table_offsets.get(str(stage.id), 0))
            if offset >= total_count and total_count:
                offset = max(0, total_count - pager_limit)
            tickets = self.search(
                stage_domain,
                order='create_date desc',
                limit=pager_limit,
                offset=offset,
            )
            stage_tables.append({
                'stage_id': stage.id,
                'stage_name': stage.name,
                'total': total_count,
                'offset': offset,
                'limit': pager_limit,
                'has_prev': offset > 0,
                'has_next': offset + pager_limit < total_count,
                'tickets': [self._serialize_ticket_row(t) for t in tickets],
            })

        # Recent Tickets (fallback summary table)
        recent_tickets_records = self.search(domain, order='create_date desc', limit=pager_limit)
        recent_tickets = [self._serialize_ticket_row(t) for t in recent_tickets_records]
            
        # 6. Recent Activities (Latest 10)
        recent_activities = []
        matching_ticket_ids = self.search(domain, order='write_date desc', limit=100).ids
        if matching_ticket_ids:
            messages = self.env['mail.message'].search([
                ('model', '=', 'service.desk.ticket'),
                ('res_id', 'in', matching_ticket_ids)
            ], order='id desc', limit=30)
            
            for msg in messages:
                tracking_values = self._get_dashboard_tracking_values(msg)
                stage_track = tracking_values.filtered(lambda t: t.field_id.name == 'stage_id')
                user_track = tracking_values.filtered(lambda t: t.field_id.name == 'user_id')
                ticket_name = msg.record_name or f'Ticket #{msg.res_id}'
                
                if stage_track:
                    new_stage_name = stage_track[0].new_value_char or ""
                    is_close = any(x in new_stage_name.lower() for x in ['resolved', 'closed', 'cancelled'])
                    desc = "Ticket Closed" if is_close else f"Stage Changed to {new_stage_name}"
                    recent_activities.append({
                        'id': f"stage_{msg.id}",
                        'user': msg.author_id.name or msg.create_uid.name or 'System',
                        'date': msg.date.strftime('%Y-%m-%d %H:%M') if msg.date else '',
                        'ticket_name': ticket_name,
                        'ticket_id': msg.res_id,
                        'description': desc,
                        'type': 'closed' if is_close else 'stage_change'
                    })
                elif user_track:
                    new_user_name = user_track[0].new_value_char or "Unassigned"
                    recent_activities.append({
                        'id': f"user_{msg.id}",
                        'user': msg.author_id.name or msg.create_uid.name or 'System',
                        'date': msg.date.strftime('%Y-%m-%d %H:%M') if msg.date else '',
                        'ticket_name': ticket_name,
                        'ticket_id': msg.res_id,
                        'description': f"Ticket Assigned to {new_user_name}",
                        'type': 'assign'
                    })
                elif msg.subtype_id and 'create' in msg.subtype_id.name.lower():
                    recent_activities.append({
                        'id': f"create_{msg.id}",
                        'user': msg.author_id.name or msg.create_uid.name or 'System',
                        'date': msg.date.strftime('%Y-%m-%d %H:%M') if msg.date else '',
                        'ticket_name': ticket_name,
                        'ticket_id': msg.res_id,
                        'description': "Ticket Created",
                        'type': 'create'
                    })
            
            # SLA breached
            sla_failed_tickets = self.search(domain + [('sla_status', '=', 'failed')], order='sla_deadline desc', limit=10)
            for ticket in sla_failed_tickets:
                recent_activities.append({
                    'id': f"sla_{ticket.id}",
                    'user': 'System',
                    'date': ticket.sla_deadline.strftime('%Y-%m-%d %H:%M') if ticket.sla_deadline else ticket.write_date.strftime('%Y-%m-%d %H:%M'),
                    'ticket_name': ticket.name,
                    'ticket_id': ticket.id,
                    'description': 'SLA Breached',
                    'type': 'sla_breached'
                })
                
            recent_activities = sorted(recent_activities, key=lambda x: x['date'], reverse=True)[:10]

        return {
            'total_tickets': total_tickets,
            'open_tickets': open_tickets,
            'in_progress_tickets': in_progress_tickets,
            'waiting_customer_tickets': waiting_customer_tickets,
            'resolved_tickets': resolved_tickets,
            'closed_tickets': closed_tickets,
            'my_tickets': my_tickets_count,
            'avg_rating': avg_rating,
            'sla_breached': sla_breached,
            'active_contracts': active_contracts,
            'low_balance_contracts': low_balance_contracts,
            'pager_limit': pager_limit,
            'filter_stage_kpis': filter_stage_kpis,
            'stage_tables': stage_tables,
            'recent_tickets': recent_tickets,
            'recent_activities': recent_activities,
        }

    @api.model
    def get_ticket_status_counts(self):
        """Return per-stage and summary counts for the ticket list status cards."""
        Stage = self.env["service.desk.stage"]
        filter_stage_ids = self._get_dashboard_stage_ids("tv_service_desk.dashboard_filter_stage_ids")
        stages = Stage.browse(filter_stage_ids).exists()
        stage_data = self._read_group([], ["stage_id"], ["__count"])
        stage_counts = {stage.id: count for stage, count in stage_data if stage}

        odoo_colors = self._get_stage_color_map()
        stage_cards = []
        for stage in stages:
            color_index = stage.color if stage.color is not None else 0
            stage_cards.append({
                "id": stage.id,
                "name": stage.name,
                "count": stage_counts.get(stage.id, 0),
                "is_closed": stage.is_closed,
                "color": odoo_colors[color_index % len(odoo_colors)],
            })

        uid = self.env.user.id
        return {
            "total": self.search_count([]),
            "open": self.search_count([("stage_id.is_closed", "=", False)]),
            "my_tickets": self.search_count([
                "|", ("user_id", "=", uid), ("assigned_user_ids", "in", [uid]),
            ]),
            "sla_failed": self.search_count([("sla_status", "=", "failed")]),
            "stages": stage_cards,
        }

    @api.model
    def _cron_auto_close_tickets(self):
        icp = self.env["ir.config_parameter"].sudo()
        auto_close = icp.get_param("tv_service_desk.auto_close_ticket", "False")
        if str(auto_close).lower() not in ("1", "true", "yes"):
            return
        try:
            days = int(icp.get_param("tv_service_desk.no_of_days", 1))
        except (ValueError, TypeError):
            days = 1
        if days <= 0:
            return
        # Use Closed stage from stage mapping config
        stage_id = self._get_config_stage_id("tv_service_desk.stage_closed_id", "stage_done")
        if not stage_id:
            stage_id = self._get_config_stage_id("tv_service_desk.auto_close_stage_id", "stage_done")
        if not stage_id:
            close_stage = self.env["service.desk.stage"].search([("is_closed", "=", True)], limit=1)
        else:
            close_stage = self.env["service.desk.stage"].browse(stage_id)
        if not close_stage.exists():
            return
        threshold = fields.Datetime.now() - timedelta(days=days)
        tickets = self.search([
            ("stage_id.is_closed", "=", False),
            ("replied_status", "=", "staff_replied"),
            ("replied_date", "<=", threshold),
        ])
        tickets.write({"stage_id": close_stage.id})

    @api.model
    def _cron_ticket_reminders(self):
        if not self._get_config_bool("tv_service_desk.ticket_reminder", default=True):
            return
        self._cron_ticket_email_reminders()
        self._cron_ticket_popup_reminders()

    @api.model
    def _cron_ticket_email_reminders(self):
        now = fields.Datetime.now()
        tickets = self.search([
            ("alarm_ids", "!=", False),
            ("reminder_due_date", "!=", False),
            ("reminder_email_sent", "=", False),
            ("stage_id.is_closed", "=", False),
        ])
        email_template = self.env.ref("tv_service_desk.mail_template_ticket_reminder", raise_if_not_found=False)
        for ticket in tickets:
            due_date = ticket.reminder_due_date
            for alarm in ticket.alarm_ids.filtered(lambda a: a.type == "email"):
                delta = ticket._get_alarm_timedelta(alarm)
                if delta and now >= (due_date - delta):
                    if email_template and (ticket.user_id or ticket.assigned_user_ids):
                        email_template.send_mail(ticket.id, force_send=False)
                        ticket.reminder_email_sent = True
                        break

    def _has_popup_alarm(self):
        self.ensure_one()
        return bool(self.alarm_ids.filtered(lambda alarm: alarm.type == "popup"))

    def _is_popup_reminder_due(self, now=None):
        self.ensure_one()
        if not self.reminder_due_date or not self._has_popup_alarm():
            return False
        now = now or fields.Datetime.now()
        return now >= self.reminder_due_date

    def _get_reminder_popup_recipients(self):
        self.ensure_one()
        users = self.env["res.users"]
        if self.user_id:
            users |= self.user_id
        users |= self.assigned_user_ids
        if self.team_head_id:
            users |= self.team_head_id
        if self.team_id:
            users |= self.team_id.member_ids
        manager_group = self.env.ref(
            "tv_service_desk.group_service_desk_manager",
            raise_if_not_found=False,
        )
        if manager_group:
            users |= manager_group.user_ids
        return users.filtered(
            lambda user: user.has_group("tv_service_desk.group_service_desk_user")
        )

    def _prepare_reminder_popup_data(self):
        self.ensure_one()
        assigned_to = (
            self.user_id.name
            or ", ".join(self.assigned_user_ids.mapped("name"))
            or ""
        )
        return {
            "id": self.id,
            "name": self.name,
            "create_date": str(self.create_date) if self.create_date else "",
            "due_date": str(self.reminder_due_date) if self.reminder_due_date else "",
            "ticket_type": self.ticket_type_id.name or "",
            "category": self.category_id.name or "",
            "sub_category": self.subcategory_id.name or "",
            "team": self.team_id.name or "",
            "team_head": self.team_head_id.name or "",
            "assigned_to": assigned_to,
            "partner": self.partner_id.display_name or "",
            "person_name": self.person_name or "",
        }

    def _push_due_popup_reminders(self):
        now = fields.Datetime.now()
        for ticket in self.filtered(lambda t: t._is_popup_reminder_due(now)):
            popup_data = ticket._prepare_reminder_popup_data()
            for user in ticket._get_reminder_popup_recipients():
                if user not in ticket.reminder_popup_dismissed_user_ids:
                    user._bus_send("tv_service_desk.ticket_reminder", popup_data)

    @api.model
    def _cron_ticket_popup_reminders(self):
        now = fields.Datetime.now()
        tickets = self.search([
            ("alarm_ids.type", "=", "popup"),
            ("reminder_due_date", "!=", False),
            ("reminder_due_date", "<=", now),
            ("stage_id.is_closed", "=", False),
        ])
        tickets._push_due_popup_reminders()

    @api.model
    def get_ticket_reminder_popups(self):
        """Return due popup reminders for the current user."""
        if not self.env.user.has_group("tv_service_desk.group_service_desk_user"):
            return []
        now = fields.Datetime.now()
        user = self.env.user
        tickets = self.search([
            ("alarm_ids.type", "=", "popup"),
            ("reminder_due_date", "!=", False),
            ("reminder_due_date", "<=", now),
            ("stage_id.is_closed", "=", False),
            ("reminder_popup_dismissed_user_ids", "not in", user.id),
        ])
        return [
            ticket._prepare_reminder_popup_data()
            for ticket in tickets
            if ticket._is_popup_reminder_due(now)
        ]

    def action_mark_reminder_popup_shown(self):
        user = self.env.user
        self.write({
            "reminder_popup_shown": True,
            "reminder_popup_dismissed_user_ids": [(4, user.id)],
        })
        return True

    def action_open_from_reminder_popup(self):
        self.ensure_one()
        self.action_mark_reminder_popup_shown()
        return {
            "type": "ir.actions.act_window",
            "res_model": "service.desk.ticket",
            "res_id": self.id,
            "views": [[False, "form"]],
            "target": "current",
        }

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        custom_values = dict(custom_values or {})
        custom_values.setdefault("source", "email")
        if msg_dict.get("subject"):
            custom_values.setdefault("subject", msg_dict["subject"])
        if msg_dict.get("body"):
            custom_values.setdefault("description", msg_dict["body"])
        email_from = msg_dict.get("email_from")
        if email_from:
            normalized = email_normalize(email_from)
            partner = self.env["res.partner"].search([("email", "=ilike", normalized)], limit=1)
            if partner:
                custom_values.setdefault("partner_id", partner.id)
            custom_values.setdefault("partner_email", normalized)
        ticket = super().message_new(msg_dict, custom_values=custom_values)
        ticket._run_ai_analysis()
        return ticket

    def message_update(self, msg_dict, update_vals=None):
        return super().message_update(msg_dict, update_vals=update_vals)

    def _run_ai_analysis(self):
        for ticket in self:
            text = "%s %s" % (ticket.subject or "", ticket.description or "")
            cat_id = ticket._ai_keyword_category(text)
            if cat_id:
                ticket.ai_category_suggestion_id = cat_id
                if not ticket.category_id:
                    ticket.category_id = cat_id
            pri_id = ticket._ai_keyword_priority(text)
            if pri_id:
                ticket.ai_priority_suggestion_id = pri_id
                if not ticket.priority_id:
                    ticket.priority_id = pri_id
            ticket.ai_sentiment = ticket._ai_sentiment_score(text)
            ticket.knowledge_article_ids = [(6, 0, ticket._ai_suggest_articles(text).ids)]
            ticket.ai_reply_suggestion = ticket._ai_suggest_reply(ticket)

    def action_ai_refresh_suggestions(self):
        self._run_ai_analysis()
        for ticket in self:
            messages = ticket.message_ids.filtered(lambda m: m.message_type == "comment")
            ticket.ai_summary = ticket._ai_summarize_messages(messages)
        return True

    def action_ai_apply_suggestions(self):
        for ticket in self:
            if ticket.ai_category_suggestion_id and not ticket.category_id:
                ticket.category_id = ticket.ai_category_suggestion_id
            if ticket.ai_priority_suggestion_id and not ticket.priority_id:
                ticket.priority_id = ticket.ai_priority_suggestion_id

    def action_open_create_repair_wizard(self):
        self.ensure_one()
        product = self.repair_product_id or self.product_ids[:1]
        if not product:
            raise ValidationError(_("Please select product for create Repair Order"))
        return {
            "type": "ir.actions.act_window",
            "name": _("Repair Order"),
            "res_model": "repair.order",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_partner_id": self.partner_id.id,
                "default_product_id": product.id,
                "default_company_id": self.company_id.id,
                "default_internal_notes": self.description,
                "default_sd_ticket_ids": [(6, 0, self.ids)],
                "default_move_ids": self._prepare_repair_move_lines_from_products(),
                "sd_link_ticket_id": self.id,
                "sd_set_repair_product": True,
            },
        }

    def action_view_repairs(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Repair Orders"),
            "res_model": "repair.order",
            "view_mode": "list,form,kanban",
            "domain": [("id", "in", self.repair_order_ids.ids)],
            "context": {"create": False},
        }

    def action_open_add_custom_field_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Create Custom Fields"),
            "res_model": "service.desk.custom.field.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_ticket_id": self.id},
        }

    def action_open_add_custom_tab_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Helpdesk Ticket Custom Tab"),
            "res_model": "service.desk.custom.tab.wizard",
            "view_mode": "form",
            "target": "new",
        }

    def action_send_whatsapp_update(self):
        self.ensure_one()
        config = self._get_whatsapp_config()
        if config and self.partner_id:
            body = _("Update on ticket %s: %s") % (self.name, self.stage_id.name)
            config._send_whatsapp_message(self.partner_id, body)
            self.message_post(body=_("WhatsApp update queued: %s") % body, subtype_xmlid="mail.mt_note")
        return True

    @api.model
    def _cron_sla_monitor(self):
        self.env["service.desk.support.contract"]._check_low_balance()

    def _compute_access_url(self):
        super()._compute_access_url()
        for ticket in self:
            ticket.access_url = f"/my/service-desk/{ticket.id}"

    def get_portal_url(self, suffix=None, report_type=None, download=None, query_string=None, anchor=None):
        self.ensure_one()
        if self._get_config_bool("tv_service_desk.portal_view_access_token", default=True):
            return super().get_portal_url(
                suffix=suffix,
                report_type=report_type,
                download=download,
                query_string=query_string,
                anchor=anchor,
            )
        url = self.access_url + (suffix or "")
        params = []
        if report_type:
            params.append("report_type=%s" % report_type)
        if download:
            params.append("download=true")
        if query_string:
            params.append(query_string.lstrip("&"))
        if params:
            url += "?" + "&".join(params)
        if anchor:
            url += "#%s" % anchor
        return url

    # Smart button actions
    def action_view_leads(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Leads"),
            "res_model": "crm.lead",
            "view_mode": "list,kanban,form",
            "domain": [("sd_ticket_ids", "in", self.ids), ("type", "=", "lead")],
            "context": {"default_type": "lead", "search_default_type": "lead"},
        }

    def action_view_opportunities(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Opportunities"),
            "res_model": "crm.lead",
            "view_mode": "kanban,list,form",
            "domain": [("sd_ticket_ids", "in", self.ids), ("type", "=", "opportunity")],
            "context": {"default_type": "opportunity"},
        }

    def action_view_sales(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Sales"),
            "res_model": "sale.order",
            "view_mode": "list,form,kanban",
            "domain": [("id", "in", self.sale_order_ids.ids)],
            "context": {"create": False},
        }

    def action_view_purchases(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Purchases"),
            "res_model": "purchase.order",
            "view_mode": "list,form,kanban",
            "domain": [("id", "in", self.purchase_order_ids.ids)],
            "context": {"create": False},
        }

    def action_view_invoices(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Invoices"),
            "res_model": "account.move",
            "view_mode": "list,form,kanban",
            "domain": [
                ("id", "in", self.invoice_ids.ids),
                ("move_type", "in", ("out_invoice", "out_refund")),
            ],
            "context": {"create": False, "default_move_type": "out_invoice"},
        }

    def action_view_tasks(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Tasks"),
            "res_model": "project.task",
            "view_mode": "kanban,list,form",
            "domain": [("sd_ticket_id", "in", self.ids)],
            "context": {"create": False},
        }

    def _action_view_records(self, model, domain):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Related Records"),
            "res_model": model,
            "view_mode": "list,form,kanban",
            "domain": domain,
        }

    @api.onchange("ticket_type_id")
    def _onchange_ticket_type_followup(self):
        if self.ticket_type_id and self.ticket_type_id.follow_up:
            if self.ticket_type_id.auto_followup_trigger:
                self.auto_followup = True
                self.followup_template_id = self.ticket_type_id.followup_template_id
        else:
            self.auto_followup = False
            self.followup_template_id = False

    def _apply_ticket_type_followup_defaults(self):
        for ticket in self:
            ticket_type = ticket.ticket_type_id
            if not ticket_type or not ticket_type.follow_up:
                continue
            if ticket_type.auto_followup_trigger:
                ticket.auto_followup = True
                if ticket_type.followup_template_id:
                    ticket.followup_template_id = ticket_type.followup_template_id

    def _get_auto_followup_stage_id(self):
        return self._get_config_stage_id(
            "tv_service_desk.auto_followup_stage_id", "stage_waiting"
        )

    def _maybe_trigger_auto_followup(self):
        self.ensure_one()
        if self.followup_generated:
            return
        if not self.auto_followup or not self.followup_template_id:
            return
        if self.stage_id.id != self._get_auto_followup_stage_id():
            return
        self._generate_followup_history()
        self.followup_generated = True

    def _generate_followup_history(self):
        self.ensure_one()
        template = self.followup_template_id
        if not template or not template.line_ids:
            return
        History = self.env["service.desk.ticket.followup.history"]
        base_date = fields.Date.context_today(self)
        lines = template.line_ids.sorted("sequence")
        vals_list = []
        if lines:
            vals_list.append({
                "ticket_id": self.id,
                "schedule_date": base_date,
                "mail_template_id": lines[0].mail_template_id.id,
                "status": "pending",
            })
        cumulative = 0
        for line in lines:
            cumulative += line.interval
            vals_list.append({
                "ticket_id": self.id,
                "schedule_date": base_date + timedelta(days=cumulative),
                "mail_template_id": line.mail_template_id.id,
                "status": "pending",
            })
        History.create(vals_list)

    @api.model
    def _run_auto_followup(self):
        today = fields.Date.context_today(self)
        histories = self.env["service.desk.ticket.followup.history"].search([
            ("status", "=", "pending"),
            ("schedule_date", "<=", today),
            ("ticket_id.auto_followup", "=", True),
            ("ticket_id.active", "=", True),
        ])
        histories._send_followup_email()

    def action_open_new_sticky_note_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("New Note"),
            "res_model": "service.desk.sticky.note.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_ticket_id": self.id},
        }
