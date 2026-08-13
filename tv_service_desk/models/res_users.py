from odoo import api, fields, models, tools
from odoo.tools import frozendict

from .helpdesk_timezone import DEPRECATED_TIMEZONE_MAP, normalize_timezone


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def _normalize_timezone(self, tz):
        return normalize_timezone(tz)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("tz"):
                vals["tz"] = self._normalize_timezone(vals["tz"])
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("tz"):
            vals["tz"] = self._normalize_timezone(vals["tz"])
        return super().write(vals)

    @api.model
    @tools.ormcache("self.env.uid")
    def context_get(self):
        context = super().context_get()
        if not context:
            return context
        tz = context.get("tz")
        normalized = self._normalize_timezone(tz)
        if normalized != tz:
            return frozendict({**dict(context), "tz": normalized})
        return context

    @api.model
    def _migrate_deprecated_timezones(self):
        for deprecated, replacement in DEPRECATED_TIMEZONE_MAP.items():
            users = self.sudo().search([("tz", "=", deprecated)])
            if users:
                users.write({"tz": replacement})

    sd_helpdesk_role = fields.Selection(
        [
            ("user", "User"),
            ("team_leader", "Team Leader"),
            ("manager", "Manager"),
        ],
        string="Helpdesk",
        compute="_compute_sd_helpdesk_role",
        inverse="_inverse_sd_helpdesk_role",
    )
    sd_allow_mass_update = fields.Boolean(
        string="Mass Ticket Update",
        compute="_compute_sd_allow_mass_update",
        inverse="_inverse_sd_allow_mass_update",
    )
    sd_crm_helpdesk = fields.Boolean(
        string="CRM Helpdesk Ticket",
        compute="_compute_sd_crm_helpdesk",
        inverse="_inverse_sd_crm_helpdesk",
    )
    sd_sale_helpdesk = fields.Boolean(
        string="Sale Helpdesk Ticket",
        compute="_compute_sd_sale_helpdesk",
        inverse="_inverse_sd_sale_helpdesk",
    )
    sd_purchase_helpdesk = fields.Boolean(
        string="Purchase Helpdesk Ticket",
        compute="_compute_sd_purchase_helpdesk",
        inverse="_inverse_sd_purchase_helpdesk",
    )
    sd_invoice_helpdesk = fields.Boolean(
        string="Invoice Helpdesk Ticket",
        compute="_compute_sd_invoice_helpdesk",
        inverse="_inverse_sd_invoice_helpdesk",
    )
    sd_helpdesk_task = fields.Boolean(
        string="Helpdesk Task",
        compute="_compute_sd_helpdesk_task",
        inverse="_inverse_sd_helpdesk_task",
    )
    sd_helpdesk_timesheet = fields.Boolean(
        string="Helpdesk Ticket Timesheet",
        compute="_compute_sd_helpdesk_timesheet",
        inverse="_inverse_sd_helpdesk_timesheet",
    )
    sd_repair_helpdesk = fields.Boolean(
        string="Repair Helpdesk Ticket",
        compute="_compute_sd_repair_helpdesk",
        inverse="_inverse_sd_repair_helpdesk",
    )
    sd_custom_field_tab = fields.Boolean(
        string="Helpdesk custom Field and tab",
        compute="_compute_sd_custom_field_tab",
        inverse="_inverse_sd_custom_field_tab",
    )
    sd_whatsapp_feature = fields.Boolean(
        string="Helpdesk Whatsapp Feature",
        compute="_compute_sd_whatsapp_feature",
        inverse="_inverse_sd_whatsapp_feature",
    )
    sd_sla_policy = fields.Boolean(
        string="Helpdesk SLA Policy",
        compute="_compute_sd_sla_policy",
        inverse="_inverse_sd_sla_policy",
    )
    sd_whatsapp_signature = fields.Char(string="Signature")
    sd_rating_avg = fields.Float(compute="_compute_sd_rating_avg", digits=(3, 2))
    sd_rating_count = fields.Integer(compute="_compute_sd_rating_avg")
    sd_ticket_alarm = fields.Boolean(
        string="Helpdesk Ticket Alarm",
        compute="_compute_sd_ticket_alarm",
        inverse="_inverse_sd_ticket_alarm",
    )
    sd_sticky_notes_role = fields.Selection(
        [
            ("user", "User"),
            ("manager", "Manager"),
        ],
        string="Sticky Notes",
        compute="_compute_sd_sticky_notes_role",
        inverse="_inverse_sd_sticky_notes_role",
    )
    portal_access = fields.Selection([
        ('manager', 'Portal Manager'),
        ('support', 'Portal Support User')
    ], string="Portal Access", compute="_compute_portal_access", inverse="_inverse_portal_access")
    sd_new_ticket_notification = fields.Boolean(
        string="New Ticket Notification?",
        default=True,
    )
    sd_ticket_assigned_notification = fields.Boolean(
        string="Ticket Assigned Notification?",
        default=True,
    )
    sd_ticket_done_notification = fields.Boolean(
        string="Ticket Done Notification?",
        default=True,
    )
    sd_ticket_cancel_notification = fields.Boolean(
        string="Ticket Cancel Notification?",
        default=True,
    )
    sd_ticket_stage_notification = fields.Boolean(
        string="Ticket Stage Change Notification?",
        default=True,
    )

    @api.depends("group_ids")
    def _compute_portal_access(self):
        group_manager = self.env.ref("tv_service_desk.group_portal_manager", raise_if_not_found=False)
        group_support = self.env.ref("tv_service_desk.group_portal_support", raise_if_not_found=False)
        for user in self:
            if group_manager and group_manager in user.group_ids:
                user.portal_access = 'manager'
            elif group_support and group_support in user.group_ids:
                user.portal_access = 'support'
            else:
                user.portal_access = False

    def _inverse_portal_access(self):
        group_manager = self.env.ref("tv_service_desk.group_portal_manager", raise_if_not_found=False)
        group_support = self.env.ref("tv_service_desk.group_portal_support", raise_if_not_found=False)
        if not group_manager or not group_support:
            return
        for user in self:
            if user.portal_access == 'manager':
                user.write({
                    'group_ids': [
                        (4, group_manager.id),
                        (3, group_support.id)
                    ]
                })
            elif user.portal_access == 'support':
                user.write({
                    'group_ids': [
                        (4, group_support.id),
                        (3, group_manager.id)
                    ]
                })
            else:
                user.write({
                    'group_ids': [
                        (3, group_manager.id),
                        (3, group_support.id)
                    ]
                })

    def _compute_sd_rating_avg(self):
        Rating = self.env["service.desk.ticket.rating"]
        for user in self:
            ratings = Rating.search([("user_id", "=", user.id)])
            user.sd_rating_count = len(ratings)
            user.sd_rating_avg = (
                sum(int(r.rating) for r in ratings) / len(ratings) if ratings else 0.0
            )

    @api.depends("group_ids")
    def _compute_sd_allow_mass_update(self):
        group = self.env.ref("tv_service_desk.group_service_desk_mass_update", raise_if_not_found=False)
        for user in self:
            user.sd_allow_mass_update = bool(group and group in user.group_ids)

    def _inverse_sd_allow_mass_update(self):
        group = self.env.ref("tv_service_desk.group_service_desk_mass_update", raise_if_not_found=False)
        if not group:
            return
        for user in self:
            if user.sd_allow_mass_update:
                user.group_ids = [(4, group.id)]
            else:
                user.group_ids = [(3, group.id)]

    @api.depends("group_ids")
    def _compute_sd_whatsapp_feature(self):
        group = self.env.ref("tv_service_desk.group_service_desk_whatsapp", raise_if_not_found=False)
        for user in self:
            user.sd_whatsapp_feature = bool(group and group in user.group_ids)

    def _inverse_sd_whatsapp_feature(self):
        group = self.env.ref("tv_service_desk.group_service_desk_whatsapp", raise_if_not_found=False)
        if not group:
            return
        for user in self:
            if user.sd_whatsapp_feature:
                user.group_ids = [(4, group.id)]
            else:
                user.group_ids = [(3, group.id)]

    @api.depends("group_ids")
    def _compute_sd_sla_policy(self):
        group = self.env.ref("tv_service_desk.group_service_desk_sla_policy", raise_if_not_found=False)
        for user in self:
            user.sd_sla_policy = bool(group and group in user.group_ids)

    def _inverse_sd_sla_policy(self):
        group = self.env.ref("tv_service_desk.group_service_desk_sla_policy", raise_if_not_found=False)
        if not group:
            return
        for user in self:
            if user.sd_sla_policy:
                user.group_ids = [(4, group.id)]
            else:
                user.group_ids = [(3, group.id)]

    @api.depends("group_ids")
    def _compute_sd_ticket_alarm(self):
        group = self.env.ref("tv_service_desk.group_service_desk_ticket_alarm", raise_if_not_found=False)
        for user in self:
            user.sd_ticket_alarm = bool(group and group in user.group_ids)

    def _inverse_sd_ticket_alarm(self):
        group = self.env.ref("tv_service_desk.group_service_desk_ticket_alarm", raise_if_not_found=False)
        if not group:
            return
        for user in self:
            if user.sd_ticket_alarm:
                user.group_ids = [(4, group.id)]
            else:
                user.group_ids = [(3, group.id)]

    def _get_helpdesk_role_groups(self):
        return {
            "user": self.env.ref("tv_service_desk.group_service_desk_user", raise_if_not_found=False),
            "team_leader": self.env.ref("tv_service_desk.group_service_desk_team_leader", raise_if_not_found=False),
            "manager": self.env.ref("tv_service_desk.group_service_desk_manager", raise_if_not_found=False),
        }

    @api.depends("group_ids")
    def _compute_sd_helpdesk_role(self):
        groups = self._get_helpdesk_role_groups()
        for user in self:
            if groups["manager"] and groups["manager"] in user.group_ids:
                user.sd_helpdesk_role = "manager"
            elif groups["team_leader"] and groups["team_leader"] in user.group_ids:
                user.sd_helpdesk_role = "team_leader"
            elif groups["user"] and groups["user"] in user.group_ids:
                user.sd_helpdesk_role = "user"
            else:
                user.sd_helpdesk_role = False

    def _ensure_internal_user_access(self):
        """Internal users must keep base.group_user or backend login fails."""
        base_user = self.env.ref("base.group_user", raise_if_not_found=False)
        if not base_user:
            return
        for user in self.filtered(lambda u: not u.share):
            if base_user not in user.group_ids:
                user.write({"group_ids": [(4, base_user.id)]})

    def _inverse_sd_helpdesk_role(self):
        groups = self._get_helpdesk_role_groups()
        if not all(groups.values()):
            return
        for user in self:
            role = user.sd_helpdesk_role
            cmds = []
            if role == "manager":
                cmds = [(4, groups["manager"].id)]
            elif role == "team_leader":
                cmds = [(4, groups["team_leader"].id), (3, groups["manager"].id)]
            elif role == "user":
                cmds = [
                    (4, groups["user"].id),
                    (3, groups["team_leader"].id),
                    (3, groups["manager"].id),
                ]
            else:
                cmds = [
                    (3, groups["user"].id),
                    (3, groups["team_leader"].id),
                    (3, groups["manager"].id),
                ]
            if cmds:
                user.write({"group_ids": cmds})
        self._ensure_internal_user_access()

    def _compute_sd_integration_group(self, group_xmlid, field_name):
        group = self.env.ref(group_xmlid, raise_if_not_found=False)
        for user in self:
            user[field_name] = bool(group and group in user.group_ids)

    def _inverse_sd_integration_group(self, group_xmlid, field_name):
        group = self.env.ref(group_xmlid, raise_if_not_found=False)
        if not group:
            return
        for user in self:
            if user[field_name]:
                user.group_ids = [(4, group.id)]
            else:
                user.group_ids = [(3, group.id)]

    @api.depends("group_ids")
    def _compute_sd_crm_helpdesk(self):
        self._compute_sd_integration_group("tv_service_desk.group_service_desk_crm", "sd_crm_helpdesk")

    def _inverse_sd_crm_helpdesk(self):
        self._inverse_sd_integration_group("tv_service_desk.group_service_desk_crm", "sd_crm_helpdesk")

    @api.depends("group_ids")
    def _compute_sd_sale_helpdesk(self):
        self._compute_sd_integration_group("tv_service_desk.group_service_desk_sale", "sd_sale_helpdesk")

    def _inverse_sd_sale_helpdesk(self):
        self._inverse_sd_integration_group("tv_service_desk.group_service_desk_sale", "sd_sale_helpdesk")

    @api.depends("group_ids")
    def _compute_sd_purchase_helpdesk(self):
        self._compute_sd_integration_group("tv_service_desk.group_service_desk_purchase", "sd_purchase_helpdesk")

    def _inverse_sd_purchase_helpdesk(self):
        self._inverse_sd_integration_group("tv_service_desk.group_service_desk_purchase", "sd_purchase_helpdesk")

    @api.depends("group_ids")
    def _compute_sd_invoice_helpdesk(self):
        self._compute_sd_integration_group("tv_service_desk.group_service_desk_invoice", "sd_invoice_helpdesk")

    def _inverse_sd_invoice_helpdesk(self):
        self._inverse_sd_integration_group("tv_service_desk.group_service_desk_invoice", "sd_invoice_helpdesk")

    @api.depends("group_ids")
    def _compute_sd_helpdesk_task(self):
        self._compute_sd_integration_group("tv_service_desk.group_service_desk_task", "sd_helpdesk_task")

    def _inverse_sd_helpdesk_task(self):
        self._inverse_sd_integration_group("tv_service_desk.group_service_desk_task", "sd_helpdesk_task")

    @api.depends("group_ids")
    def _compute_sd_helpdesk_timesheet(self):
        self._compute_sd_integration_group("tv_service_desk.group_service_desk_timesheet", "sd_helpdesk_timesheet")

    def _inverse_sd_helpdesk_timesheet(self):
        self._inverse_sd_integration_group("tv_service_desk.group_service_desk_timesheet", "sd_helpdesk_timesheet")

    @api.depends("group_ids")
    def _compute_sd_repair_helpdesk(self):
        self._compute_sd_integration_group("tv_service_desk.group_service_desk_repair", "sd_repair_helpdesk")

    def _inverse_sd_repair_helpdesk(self):
        self._inverse_sd_integration_group("tv_service_desk.group_service_desk_repair", "sd_repair_helpdesk")

    @api.depends("group_ids")
    def _compute_sd_custom_field_tab(self):
        self._compute_sd_integration_group("tv_service_desk.group_service_desk_custom", "sd_custom_field_tab")

    def _inverse_sd_custom_field_tab(self):
        self._inverse_sd_integration_group("tv_service_desk.group_service_desk_custom", "sd_custom_field_tab")

    def _get_sticky_note_role_groups(self):
        return {
            "user": self.env.ref("tv_service_desk.group_service_desk_sticky_note_user", raise_if_not_found=False),
            "manager": self.env.ref("tv_service_desk.group_service_desk_sticky_note_manager", raise_if_not_found=False),
        }

    @api.depends("group_ids")
    def _compute_sd_sticky_notes_role(self):
        groups = self._get_sticky_note_role_groups()
        for user in self:
            if groups["manager"] and groups["manager"] in user.group_ids:
                user.sd_sticky_notes_role = "manager"
            elif groups["user"] and groups["user"] in user.group_ids:
                user.sd_sticky_notes_role = "user"
            else:
                user.sd_sticky_notes_role = False

    def _inverse_sd_sticky_notes_role(self):
        groups = self._get_sticky_note_role_groups()
        if not groups["user"]:
            return
        for user in self:
            role = user.sd_sticky_notes_role
            if role == "manager" and groups["manager"]:
                user.group_ids = [(4, groups["manager"].id)]
            elif role == "user":
                cmds = [(4, groups["user"].id)]
                if groups["manager"]:
                    cmds.append((3, groups["manager"].id))
                user.group_ids = cmds
            else:
                cmds = []
                if groups["user"]:
                    cmds.append((3, groups["user"].id))
                if groups["manager"]:
                    cmds.append((3, groups["manager"].id))
                user.group_ids = cmds

    def _wants_helpdesk_notification(self, event):
        self.ensure_one()
        field_map = {
            "create": "sd_new_ticket_notification",
            "assign": "sd_ticket_assigned_notification",
            "done": "sd_ticket_done_notification",
            "cancel": "sd_ticket_cancel_notification",
            "stage": "sd_ticket_stage_notification",
        }
        field_name = field_map.get(event)
        if not field_name:
            return False
        return bool(getattr(self, field_name, True))

    @api.model
    def _sync_helpdesk_inbox_notifications(self):
        """Use Odoo systray bell for helpdesk alerts (not email-only mode)."""
        inbox_group = self.env.ref(
            "mail.group_mail_notification_type_inbox", raise_if_not_found=False
        )
        helpdesk_groups = [
            self.env.ref("tv_service_desk.group_service_desk_user", raise_if_not_found=False),
            self.env.ref("tv_service_desk.group_service_desk_team_leader", raise_if_not_found=False),
            self.env.ref("tv_service_desk.group_service_desk_manager", raise_if_not_found=False),
        ]
        helpdesk_groups = [group for group in helpdesk_groups if group]
        if not helpdesk_groups:
            return
        users = self.sudo().search([
            ("share", "=", False),
            ("group_ids", "in", [group.id for group in helpdesk_groups]),
        ])
        for user in users:
            write_vals = {}
            if user.notification_type != "inbox":
                write_vals["notification_type"] = "inbox"
            if inbox_group and inbox_group not in user.group_ids:
                write_vals["group_ids"] = [(4, inbox_group.id)]
            if write_vals:
                user.write(write_vals)
