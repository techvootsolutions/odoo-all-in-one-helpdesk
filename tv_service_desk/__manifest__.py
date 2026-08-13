# -*- coding: utf-8 -*-
# Powered by Techvoot Solutions.
# © 2018 Techvoot Solutions. (<https://www.techvoot.com/>).
# See LICENSE file for full copyright & licensing details.

{
    "name": "All In One Helpdesk",
    "version": "19.0.1.0.0",
    "category": "Services/Helpdesk",
    "summary": """The 'All In One Helpdesk' Module Provides A Complete Customer Support And Ticket Management Solution In Odoo. Manage Helpdesk Tickets, SLA Policies, Support Teams, Customer Ratings, Timesheets, Auto Follow-Ups, Email Notifications, WhatsApp Integration, Knowledge Base, Service Contracts, Dashboard Analytics, Multi-Agent Assignment, Ticket Automation, And Portal Access From A Single Platform. Improve Customer Satisfaction, Streamline Support Operations, And Enhance Team Productivity With Advanced Helpdesk Features.
    helpdesk management | ticket management | customer support | service desk | support ticket | helpdesk automation | SLA management | ticket workflow | support team | customer service | ticket assignment | ticket dashboard | customer portal | support contract | service level agreement | ticket analytics | helpdesk reporting | whatsapp integration | email notifications | timesheet tracking | customer rating | knowledge base | support center | multi agent support | Odoo helpdesk""",
    "description": """
    All In One Helpdesk
    ==================

    A Comprehensive Helpdesk And Customer Support Management Solution For Odoo 19 Community Edition. Streamline Customer Support Operations With Advanced Ticket Management, SLA Tracking, Team Collaboration, Customer Communication, Reporting, And Automation Features.

    Key Features
    ------------
    * Ticket Management With Teams, Stages, Categories, Tags And Priorities
    * Automated Ticket Assignment And Workflow Management
    * Ticket Stage Automation Based On Customer And Staff Replies
    * Customer Portal For Ticket Tracking And Self-Service Access
    * Customer Satisfaction Rating And Feedback System
    * Support Contracts And Hour Package Management
    * Timesheet Integration And Time Tracking
    * Ticket Auto Follow-Up And Reminder Management
    * Email Notification And Template Configuration
    * WhatsApp Ticket Communication Integration
    * Dashboard Analytics And KPI Monitoring
    * Multi-User Ticket Collaboration
    * Attachment And Portal Access Management
    * SLA Monitoring And Escalation Tracking
    * AI-Powered Helpdesk Assistance
    * Advanced Reporting And Stage Analysis
    * CRM, Sales, Project And Invoicing Integration
    * Auto Followers And Communication Tracking
    * Ticket Merge, Assignment And Lifecycle Automation

    Benefits
    --------
    * Improve Customer Satisfaction
    * Increase Team Productivity
    * Reduce Support Response Time
    * Automate Daily Helpdesk Operations
    * Centralize Customer Communication
    * Gain Actionable Support Insights

    Perfect For
    -----------
    Customer Support Teams, Service Providers, IT Helpdesks, Internal Support Departments, Maintenance Teams, And Organizations Looking For A Complete Helpdesk Management Solution In Odoo.
    """,
    "author": "Techvoot Solutions",
    "website": "https://www.techvoot.com",
    "license": "OPL-1",
    "depends": [
        "base",
        "bus",
        "mail",
        "portal",
        "contacts",
        "crm",
        "sale_management",
        "purchase",
        "account",
        "project",
        "hr_timesheet",
        "sale_timesheet",
        "calendar",
        "repair",
    ],
    "data": [
        "security/service_desk_security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/mail_template_data.xml",
        "data/whatsapp_mail_template_data.xml",
        "data/ir_cron_data.xml",
        "data/default_data.xml",
        "data/auto_followup_data.xml",
        "data/alarm_data.xml",
        "data/stage_reference_update.xml",
        "data/ticket_subject_type_data.xml",
        "data/mail_activity_type_data.xml",
        "data/knowledge_data.xml",
        "views/service_desk_team_views.xml",
        "views/service_desk_stage_views.xml",
        "views/service_desk_category_views.xml",
        "views/service_desk_tag_views.xml",
        "views/service_desk_priority_views.xml",
        "views/service_desk_ticket_type_views.xml",
        "views/service_desk_sla_views.xml",
        "views/service_desk_support_contract_views.xml",
        "views/service_desk_customer_hour_package_views.xml",
        "views/service_desk_auto_followup_views.xml",
        "views/service_desk_sticky_note_views.xml",
        "views/mail_mail_views.xml",
        "views/service_desk_knowledge_views.xml",
        "views/service_desk_custom_field_views.xml",
        "views/service_desk_whatsapp_views.xml",
        "views/service_desk_ticket_subject_type_views.xml",
        "views/service_desk_ticket_views.xml",
        "views/service_desk_ticket_search_filter_views.xml",
        "views/service_desk_stage_change_views.xml",
        "views/service_desk_dashboard_views.xml",
        "views/service_desk_report_views.xml",
        "views/service_desk_alarm_views.xml",
        "views/res_config_settings_views.xml",
        "views/res_users_views.xml",
        "views/res_partner_views.xml",
        "views/crm_lead_views.xml",
        "views/sale_order_views.xml",
        "views/purchase_order_views.xml",
        "views/account_move_views.xml",
        "views/project_task_views.xml",
        "views/helpdesk_ticket_widget_views.xml",
        "views/repair_order_views.xml",
        "wizard/service_desk_reply_wizard_views.xml",
        "wizard/service_desk_merge_wizard_views.xml",
        "wizard/service_desk_mass_update_wizard_views.xml",
        "wizard/service_desk_create_lead_wizard_views.xml",
        "wizard/service_desk_create_sale_wizard_views.xml",
        "wizard/service_desk_create_purchase_wizard_views.xml",
        "wizard/service_desk_create_invoice_wizard_views.xml",
        "wizard/service_desk_create_task_wizard_views.xml",
        "wizard/service_desk_create_repair_wizard_views.xml",
        "wizard/service_desk_whatsapp_send_wizard_views.xml",
        "wizard/service_desk_end_ticket_wizard_views.xml",
        "wizard/service_desk_custom_tab_wizard_views.xml",
        "wizard/service_desk_custom_field_wizard_views.xml",
        "wizard/service_desk_sticky_note_wizard_views.xml",
        "views/service_desk_menus.xml",
        "report/ticket_report_templates.xml",
        "report/ticket_report.xml",
        "views/portal_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "tv_service_desk/static/src/scss/helpdesk_navbar.scss",
            "tv_service_desk/static/src/scss/helpdesk_ticket_widget.scss",
            "tv_service_desk/static/src/scss/ticket_kanban.scss",
            "tv_service_desk/static/src/js/helpdesk_ticket_widget.js",
            "tv_service_desk/static/src/xml/helpdesk_ticket_widget.xml",
            "tv_service_desk/static/src/scss/ticket_form.scss",
            "tv_service_desk/static/src/scss/team_form.scss",
            "tv_service_desk/static/src/js/ticket_message_patch.js",
            "tv_service_desk/static/src/scss/dashboard.scss",
            "tv_service_desk/static/src/scss/ticket_list.scss",
            "tv_service_desk/static/src/js/helpdesk_navbar.js",
            "tv_service_desk/static/src/js/helpdesk_messaging_menu.js",
            "tv_service_desk/static/src/xml/helpdesk_messaging_menu.xml",
            "tv_service_desk/static/src/js/timer_utils.js",
            "tv_service_desk/static/src/js/ticket_kanban_timer.js",
            "tv_service_desk/static/src/js/ticket_timer_systray.js",
            "tv_service_desk/static/src/js/ticket_form_view.js",
            "tv_service_desk/static/src/js/ticket_sticky_notes.js",
            "tv_service_desk/static/src/xml/ticket_sticky_notes.xml",
            "tv_service_desk/static/src/scss/ticket_sticky_notes.scss",
            "tv_service_desk/static/src/js/ticket_form_timer.js",
            "tv_service_desk/static/src/xml/ticket_timer_systray.xml",
            "tv_service_desk/static/src/js/dashboard.js",
            "tv_service_desk/static/src/js/ticket_list_controller.js",
            "tv_service_desk/static/src/xml/dashboard.xml",
            "tv_service_desk/static/src/xml/ticket_list_controller.xml",
            "tv_service_desk/static/src/scss/ticket_reminder_popup.scss",
            "tv_service_desk/static/src/js/ticket_reminder_popup.js",
            "tv_service_desk/static/src/js/ticket_reminder_webclient.js",
            "tv_service_desk/static/src/xml/ticket_reminder_popup.xml",
        ],
        "web.assets_backend_lazy": [
            "tv_service_desk/static/src/scss/ticket_graph.scss",
            "tv_service_desk/static/src/js/ticket_graph_patch.js",
        ],
    },
    "demo": [
        "data/demo_user_helpdesk_access.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    'images': ['static/description/banner.gif'],
}
