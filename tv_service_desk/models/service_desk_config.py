from odoo import api, fields, models

DATE_FILTER_OPTIONS = [
    ("all", "All Dates"),
    ("today", "Today"),
    ("week", "This Week"),
    ("month", "This Month"),
    ("year", "This Year"),
    ("custom", "Custom"),
]


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    sd_auto_add_customer_follower = fields.Boolean(
        string="Auto add customer as follower when create ticket?",
        config_parameter="tv_service_desk.auto_add_customer_follower",
        default=True,
    )
    sd_ticket_reminder = fields.Boolean(
        string="Ticket Reminder?",
        config_parameter="tv_service_desk.ticket_reminder",
        default=True,
    )
    sd_allocation_mail_template_id = fields.Many2one(
        "mail.template",
        string="Ticket Allocation To User Mail Template",
        config_parameter="tv_service_desk.allocation_mail_template_id",
        domain="[('model', '=', 'service.desk.ticket')]",
    )
    sd_reply_mail_template_id = fields.Many2one(
        "mail.template",
        string="Ticket Reply Mail Template",
        config_parameter="tv_service_desk.reply_mail_template_id",
        domain="[('model', '=', 'service.desk.ticket')]",
    )
    sd_email_on_customer_view = fields.Boolean(
        string="Get email when customer view ticket?",
        config_parameter="tv_service_desk.email_on_customer_view",
        default=False,
    )
    sd_portal_view_access_token = fields.Boolean(
        string="Portal View Ticket with Access Token",
        config_parameter="tv_service_desk.portal_view_access_token",
        default=True,
    )
    sd_dashboard_show_extended_kpis = fields.Boolean(
        string="Show Extended Dashboard KPIs",
        config_parameter="tv_service_desk.dashboard_show_extended_kpis",
        default=False,
        help="When disabled, the dashboard shows only configured stage cards and tables.",
    )
    # Screenshot 11: Ticket Settings
    sd_category_enabled = fields.Boolean(
        string="Category",
        config_parameter="tv_service_desk.category_enabled",
        default=True,
    )
    sd_subcategory_enabled = fields.Boolean(
        string="Sub Category",
        config_parameter="tv_service_desk.subcategory_enabled",
        default=True,
    )
    sd_customer_rating_enabled = fields.Boolean(
        string="Customer Rating",
        config_parameter="tv_service_desk.customer_rating_enabled",
        default=True,
    )
    sd_auto_close_ticket = fields.Boolean(
        string="Auto Close Ticket",
        config_parameter="tv_service_desk.auto_close_ticket",
        default=False,
    )
    sd_no_of_days = fields.Integer(
        string="No of Days",
        config_parameter="tv_service_desk.no_of_days",
        default=1,
        help="Number of days after last staff reply to auto-close the ticket.",
    )
    sd_portal_attachment_size_kb = fields.Integer(
        string="Portal Attachment Size(KB)",
        config_parameter="tv_service_desk.portal_attachment_size_kb",
        default=50,
    )
    sd_default_team_id = fields.Many2one(
        "service.desk.team",
        string="Default Team",
        config_parameter="tv_service_desk.default_team_id",
    )
    sd_default_assign_user_id = fields.Many2one(
        "res.users",
        string="Default Assign User",
        config_parameter="tv_service_desk.default_assign_user_id",
    )
    # Stage mapping fields (Screenshot 11)
    sd_stage_draft_id = fields.Many2one(
        "service.desk.stage",
        string="Draft/New Stage",
        config_parameter="tv_service_desk.stage_draft_id",
    )
    sd_stage_reopened_id = fields.Many2one(
        "service.desk.stage",
        string="Re-Opened Stage",
        config_parameter="tv_service_desk.stage_reopened_id",
    )
    sd_stage_cancel_id = fields.Many2one(
        "service.desk.stage",
        string="Cancel Stage",
        config_parameter="tv_service_desk.stage_cancel_id",
    )
    sd_stage_resolved_id = fields.Many2one(
        "service.desk.stage",
        string="Resolved Stage",
        config_parameter="tv_service_desk.stage_resolved_id",
    )
    sd_stage_closed_id = fields.Many2one(
        "service.desk.stage",
        string="Closed Stage",
        config_parameter="tv_service_desk.stage_closed_id",
    )
    sd_stage_change_customer_replied = fields.Boolean(
        string="Stage change when customer replied?",
        config_parameter="tv_service_desk.stage_change_customer_replied",
        default=False,
    )
    sd_stage_change_staff_replied = fields.Boolean(
        string="Stage change when staff replied?",
        config_parameter="tv_service_desk.stage_change_staff_replied",
        default=False,
    )
    sd_customer_replied_stage_id = fields.Many2one(
        "service.desk.stage",
        string="Customer Replied Stage",
        config_parameter="tv_service_desk.customer_replied_stage_id",
    )
    sd_staff_replied_stage_id = fields.Many2one(
        "service.desk.stage",
        string="Staff Replied Stage",
        config_parameter="tv_service_desk.staff_replied_stage_id",
    )
    # Legacy fields kept for compatibility
    sd_auto_close_days = fields.Integer(
        string="Auto-close After (Days)",
        config_parameter="tv_service_desk.auto_close_days",
        default=0,
    )
    sd_auto_close_stage_id = fields.Many2one(
        "service.desk.stage",
        string="Auto-close Stage",
        config_parameter="tv_service_desk.auto_close_stage_id",
    )
    sd_portal_attachment_limit_mb = fields.Float(
        string="Portal Attachment Limit (MB)",
        config_parameter="tv_service_desk.portal_attachment_limit_mb",
        default=5.0,
    )
    sd_feedback_on_close = fields.Boolean(
        string="Request Feedback on Close",
        config_parameter="tv_service_desk.feedback_on_close",
        default=True,
    )
    sd_manage_products = fields.Boolean(
        string="Manage Products",
        config_parameter="tv_service_desk.manage_products",
        default=True,
    )
    sd_manual_timesheet = fields.Boolean(
        string="Manual Add Timesheet",
        config_parameter="tv_service_desk.manual_timesheet",
    )
    sd_default_timesheet_description = fields.Boolean(
        string="Default Description In Timesheet ?",
        config_parameter="tv_service_desk.default_timesheet_description",
        default=True,
    )
    sd_default_timesheet_project_id = fields.Many2one(
        "project.project",
        string="Default Project",
        config_parameter="tv_service_desk.default_timesheet_project_id",
    )
    sd_allow_parallel_timers = fields.Boolean(
        string="Multiple Ticket Allowed ?",
        config_parameter="tv_service_desk.allow_parallel_timers",
        default=True,
    )
    sd_allocated_hours_for_month = fields.Integer(
        string="Allocated Hours For Month",
        config_parameter="tv_service_desk.allocated_hours_for_month",
        default=20,
    )
    sd_auto_followup_stage_id = fields.Many2one(
        "service.desk.stage",
        string="Auto Followup Stage",
        config_parameter="tv_service_desk.auto_followup_stage_id",
    )
    sd_notify_on_create = fields.Boolean(
        string="Send Notification When Creating Ticket",
        config_parameter="tv_service_desk.notify_on_create",
        default=True,
    )
    sd_notify_on_assign = fields.Boolean(
        string="Send Notification When Ticket is Assigned",
        config_parameter="tv_service_desk.notify_on_assign",
        default=True,
    )
    sd_notify_on_done = fields.Boolean(
        string="Send Notification When Ticket is Completed",
        config_parameter="tv_service_desk.notify_on_done",
        default=True,
    )
    sd_notify_on_cancel = fields.Boolean(
        string="Send Notification When Ticket is Cancelled",
        config_parameter="tv_service_desk.notify_on_cancel",
        default=True,
    )
    sd_notify_on_stage_change = fields.Boolean(
        string="Send Notification When Ticket Stage is Changed",
        config_parameter="tv_service_desk.notify_on_stage_change",
        default=True,
    )
    sd_dashboard_filter_stage_ids = fields.Many2many(
        comodel_name="service.desk.stage",
        relation="sd_config_dashboard_filter_stage_rel",
        column1="config_id",
        column2="stage_id",
        string="Dashboard Filter Stages",
        help="Stages shown as KPI cards on the dashboard and ticket list.",
    )
    sd_dashboard_table_stage_ids = fields.Many2many(
        comodel_name="service.desk.stage",
        relation="sd_config_dashboard_table_stage_rel",
        column1="config_id",
        column2="stage_id",
        string="Dashboard Tables",
        help="Stages shown as separate ticket tables (pagers) on the dashboard.",
    )
    sd_default_date_filter = fields.Selection(
        selection=DATE_FILTER_OPTIONS,
        string="Default Date Filter",
        config_parameter="tv_service_desk.dashboard_default_date_filter",
        default="month",
    )
    sd_dashboard_pager_limit = fields.Integer(
        string="Dashboard Page Limit",
        config_parameter="tv_service_desk.dashboard_pager_limit",
        default=4,
        help="Number of tickets shown per table/pager on the dashboard.",
    )
    sd_display_multi_users = fields.Boolean(
        string="Display Multi Users",
        config_parameter="tv_service_desk.display_multi_users",
        default=True,
        help="Show the Collaborators field on tickets.",
    )
    sd_ai_enabled = fields.Boolean(
        string="Enable AI Features",
        config_parameter="tv_service_desk.ai_enabled",
    )
    sd_ai_api_url = fields.Char(
        string="AI API URL",
        config_parameter="tv_service_desk.ai_api_url",
    )
    sd_ai_api_key = fields.Char(
        string="AI API Key",
        config_parameter="tv_service_desk.ai_api_key",
    )
    sd_ai_model = fields.Char(
        string="AI Model",
        config_parameter="tv_service_desk.ai_model",
        default="gpt-4o-mini",
    )
    sd_whatsapp_product_details = fields.Boolean(
        string="Ticket Product details in Message?",
        config_parameter="tv_service_desk.whatsapp_product_details",
        default=True,
    )
    sd_whatsapp_display_chatter = fields.Boolean(
        string="Display in Chatter Message?",
        config_parameter="tv_service_desk.whatsapp_display_chatter",
        default=True,
    )
    sd_whatsapp_send_ticket_url = fields.Boolean(
        string="Send Ticket URL in Message?",
        config_parameter="tv_service_desk.whatsapp_send_ticket_url",
        default=True,
    )
    sd_whatsapp_signature = fields.Boolean(
        string="Signature?",
        config_parameter="tv_service_desk.whatsapp_signature",
        default=True,
    )
    sd_whatsapp_send_report_url = fields.Boolean(
        string="Send Report URL in Message?",
        config_parameter="tv_service_desk.whatsapp_send_report_url",
        default=True,
    )

    @api.model
    def get_config_mail_template(self, config_param_key, default_xmlid):
        """Return configured mail.template or fallback xml id."""
        icp = self.env["ir.config_parameter"].sudo()
        template_id = icp.get_param(config_param_key)
        if template_id and str(template_id).isdigit():
            template = self.env["mail.template"].browse(int(template_id)).exists()
            if template:
                return template
        return self.env.ref(default_xmlid, raise_if_not_found=False)

    @api.model
    def _parse_stage_ids_param(self, param_value):
        if not param_value:
            return []
        return [int(x) for x in param_value.split(",") if x.isdigit()]

    @api.model
    def _config_bool(self, key, default=True):
        value = self.env["ir.config_parameter"].sudo().get_param(key)
        if value is None:
            return default
        return str(value).lower() in ("1", "true", "yes")

    @api.model
    def get_values(self):
        res = super().get_values()
        icp = self.env["ir.config_parameter"].sudo()
        Stage = self.env["service.desk.stage"]
        all_stages = Stage.search([], order="sequence, id")

        filter_ids = self._parse_stage_ids_param(
            icp.get_param("tv_service_desk.dashboard_filter_stage_ids")
        )
        table_ids = self._parse_stage_ids_param(
            icp.get_param("tv_service_desk.dashboard_table_stage_ids")
        )
        if not filter_ids:
            filter_ids = all_stages.ids
        if not table_ids:
            table_ids = all_stages.ids

        res.update({
            "sd_dashboard_filter_stage_ids": [(6, 0, filter_ids)],
            "sd_dashboard_table_stage_ids": [(6, 0, table_ids)],
        })
        return res

    def set_values(self):
        super().set_values()
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param(
            "tv_service_desk.dashboard_filter_stage_ids",
            ",".join(str(sid) for sid in self.sd_dashboard_filter_stage_ids.ids),
        )
        icp.set_param(
            "tv_service_desk.dashboard_table_stage_ids",
            ",".join(str(sid) for sid in self.sd_dashboard_table_stage_ids.ids),
        )
        for name, field in self._fields.items():
            if field.type == "boolean" and getattr(field, "config_parameter", False):
                if field.config_parameter.startswith("tv_service_desk."):
                    # Store explicit True/False strings. Passing Python False to
                    # set_param deletes the key; default_get then falls back to
                    # field default=True and the checkbox re-checks itself.
                    icp.set_param(
                        field.config_parameter,
                        "True" if getattr(self, name) else "False",
                    )


    @api.model
    def get_dashboard_stage_ids(self, param_key):
        """Return configured stage ids; fallback to all stages when unset."""
        icp = self.env["ir.config_parameter"].sudo()
        stage_ids = self._parse_stage_ids_param(icp.get_param(param_key))
        if stage_ids:
            return stage_ids
        return self.env["service.desk.stage"].search([], order="sequence, id").ids

    @api.model
    def get_dashboard_ui_config(self):
        """Return dashboard UI configuration for the OWL client."""
        icp = self.env["ir.config_parameter"].sudo()
        date_labels = dict(DATE_FILTER_OPTIONS)

        visible_filter_codes = [
            "team_leader",
            "team",
            "assigned_user",
            "date_filter",
        ]
        date_options = [
            {"code": code, "name": label} for code, label in DATE_FILTER_OPTIONS
        ]
        default_date = icp.get_param("tv_service_desk.dashboard_default_date_filter", "month")
        if default_date not in date_labels:
            default_date = "month"

        filter_labels = {
            "team_leader": "Team Leader",
            "team": "Team",
            "assigned_user": "Assigned User",
            "date_filter": "Date Filter",
        }

        return {
            "visible_filter_codes": visible_filter_codes,
            "visible_filters": [
                {"code": code, "name": filter_labels[code]} for code in visible_filter_codes
            ],
            "date_options": date_options,
            "default_date_filter": default_date,
            "pager_limit": int(icp.get_param("tv_service_desk.dashboard_pager_limit", 4)),
            "show_whatsapp": self.env.user.has_group("tv_service_desk.group_service_desk_whatsapp"),
            "show_extended_kpis": self._config_bool(
                "tv_service_desk.dashboard_show_extended_kpis", default=False
            ),
        }

    @api.model
    def get_whatsapp_message_config(self):
        """Return helpdesk WhatsApp message configuration flags."""
        return {
            "product_details": self._config_bool("tv_service_desk.whatsapp_product_details"),
            "display_chatter": self._config_bool("tv_service_desk.whatsapp_display_chatter"),
            "send_ticket_url": self._config_bool("tv_service_desk.whatsapp_send_ticket_url"),
            "signature": self._config_bool("tv_service_desk.whatsapp_signature"),
            "send_report_url": self._config_bool("tv_service_desk.whatsapp_send_report_url"),
        }
