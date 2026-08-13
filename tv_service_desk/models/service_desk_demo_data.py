# -*- coding: utf-8 -*-
"""Load full Helpdesk implementation demo data (20+ records, all roles & features)."""

from datetime import timedelta

from odoo import _, api, fields, models

from odoo.addons.tv_service_desk.models.service_desk_sticky_note import STICKY_NOTE_COLOR_PALETTE


DEMO_MARKER = "[Demo]"
DEMO_TEAM_NAME = "Demo Implementation Team"
DEMO_PASSWORD = "demo"


class ServiceDeskTicket(models.Model):
    _inherit = "service.desk.ticket"

    @api.model
    def load_implementation_demo_data(self, force=False):
        """Create demo users, master data, 25+ tickets, tasks, repairs, etc.

        Idempotent: skips if demo team already exists unless ``force=True``.

        Demo logins (password ``demo`` for all):
          - demo_agent   → Helpdesk User (all integration flags)
          - demo_leader  → Team Leader
          - demo_support → Helpdesk User (support team member)
          - admin        → Manager (existing, groups refreshed)
        """
        if not force and self.env["service.desk.team"].sudo().search(
            [("name", "=", DEMO_TEAM_NAME)], limit=1
        ):
            return {
                "skipped": True,
                "message": _(
                    "Demo data already loaded (team '%s' exists). "
                    "Use force=True to reload."
                )
                % DEMO_TEAM_NAME,
            }

        env = self.env(su=True)
        summary = {}

        users = self._demo_ensure_users(env)
        summary["users"] = {k: v.login for k, v in users.items()}

        partners = self._demo_ensure_partners(env)
        summary["partners"] = len(partners)

        master = self._demo_ensure_master_data(env, users)
        summary.update({k: len(v) if isinstance(v, list) else 1 for k, v in master.items()})

        tickets = self._demo_create_tickets(env, users, partners, master)
        summary["tickets"] = len(tickets)

        summary["tasks"] = len(self._demo_create_tasks(env, users, tickets, master))
        summary["repairs"] = len(self._demo_create_repairs(env, users, tickets, master))
        summary["sticky_notes"] = len(self._demo_create_sticky_notes(env, users, tickets))
        summary["ratings"] = self._demo_set_ratings(tickets)

        env["ir.config_parameter"].set_param(
            "tv_service_desk.implementation_demo_loaded", "1"
        )
        return {
            "skipped": False,
            "message": _("Helpdesk implementation demo data loaded successfully."),
            "summary": summary,
            "logins": {
                "manager": "admin (existing)",
                "team_leader": "demo_leader / %s" % DEMO_PASSWORD,
                "agent": "demo_agent / %s" % DEMO_PASSWORD,
                "support": "demo_support / %s" % DEMO_PASSWORD,
            },
        }

    # -------------------------------------------------------------------------
    # Users & groups
    # -------------------------------------------------------------------------

    @api.model
    def _demo_group_ids(self, env, xmlids):
        return [env.ref(x).id for x in xmlids if env.ref(x, raise_if_not_found=False)]

    @api.model
    def _demo_user_integration_groups(self):
        return [
            "tv_service_desk.group_service_desk_crm",
            "tv_service_desk.group_service_desk_sale",
            "tv_service_desk.group_service_desk_purchase",
            "tv_service_desk.group_service_desk_invoice",
            "tv_service_desk.group_service_desk_timesheet",
            "tv_service_desk.group_service_desk_task",
            "tv_service_desk.group_service_desk_repair",
            "tv_service_desk.group_service_desk_custom",
            "tv_service_desk.group_service_desk_ticket_alarm",
            "tv_service_desk.group_service_desk_sla_policy",
            "tv_service_desk.group_service_desk_whatsapp",
            "tv_service_desk.group_service_desk_sticky_note_user",
        ]

    @api.model
    def _demo_ensure_user(self, env, login, name, group_xmlids):
        User = env["res.users"]
        groups = self._demo_group_ids(env, group_xmlids)
        user = User.search([("login", "=", login)], limit=1)
        vals = {
            "name": name,
            "login": login,
            "email": "%s@demo.helpdesk.local" % login,
            "group_ids": [(6, 0, groups)],
            "sd_new_ticket_notification": True,
            "sd_ticket_assigned_notification": True,
            "sd_ticket_done_notification": True,
            "sd_ticket_cancel_notification": True,
            "sd_ticket_stage_notification": True,
        }
        if user:
            user.write(vals)
        else:
            user = User.with_context(no_reset_password=True).create(vals)
            user.write({"password": DEMO_PASSWORD})
        return user

    @api.model
    def _demo_ensure_users(self, env):
        integrations = self._demo_user_integration_groups()
        leader_groups = integrations + [
            "tv_service_desk.group_service_desk_team_leader",
            "tv_service_desk.group_service_desk_mass_update",
            "tv_service_desk.group_service_desk_sticky_note_manager",
        ]
        agent_groups = integrations + ["tv_service_desk.group_service_desk_user"]
        support_groups = integrations + ["tv_service_desk.group_service_desk_user"]

        users = {
            "leader": self._demo_ensure_user(
                env, "demo_leader", "%s Team Leader" % DEMO_MARKER, leader_groups
            ),
            "agent": self._demo_ensure_user(
                env, "demo_agent", "%s Agent" % DEMO_MARKER, agent_groups
            ),
            "support": self._demo_ensure_user(
                env, "demo_support", "%s Support User" % DEMO_MARKER, support_groups
            ),
        }

        admin = env.ref("base.user_admin")
        manager_groups = self._demo_group_ids(
            env,
            leader_groups + ["tv_service_desk.group_service_desk_manager"],
        )
        admin.sudo().write({"group_ids": [(4, gid) for gid in manager_groups]})
        users["manager"] = admin
        return users

    # -------------------------------------------------------------------------
    # Partners
    # -------------------------------------------------------------------------

    @api.model
    def _demo_ensure_partners(self, env):
        Partner = env["res.partner"]
        names = [
            "Acme Corporation",
            "Beta Industries",
            "Gamma Retail",
            "Delta Logistics",
            "Epsilon Healthcare",
            "Zeta Finance",
        ]
        partners = Partner.browse()
        for name in names:
            full = "%s %s" % (DEMO_MARKER, name)
            partner = Partner.search([("name", "=", full)], limit=1)
            if not partner:
                partner = Partner.create({
                    "name": full,
                    "email": "%s@customer.example.com" % name.split()[0].lower(),
                    "phone": "+1-555-010%d" % (len(partners) + 1),
                    "customer_rank": 1,
                })
            partners |= partner
        return partners

    # -------------------------------------------------------------------------
    # Master data
    # -------------------------------------------------------------------------

    @api.model
    def _demo_ref_data(self, env, model, name):
        rec = env[model].search([("name", "=", name)], limit=1)
        return rec

    @api.model
    def _demo_ensure_master_data(self, env, users):
        Stage = env["service.desk.stage"]
        Priority = env["service.desk.priority"]
        Team = env["service.desk.team"]
        Tag = env["service.desk.tag"]
        Category = env["service.desk.category"]
        TicketType = env["service.desk.ticket.type"]
        SubjectType = env["service.desk.ticket.subject.type"]
        Alarm = env["service.desk.alarm"]
        Sla = env["service.desk.sla.policy"]
        AutoFollowup = env["service.desk.auto.followup"]
        HourPackage = env["service.desk.customer.hour.package"]
        Contract = env["service.desk.support.contract"]
        FormTab = env["service.desk.form.tab"]
        FormField = env["service.desk.form.field"]
        Project = env["project.project"]
        Product = env["product.product"]

        stage_new = self._demo_ref_data(env, "service.desk.stage", "New") or env.ref(
            "tv_service_desk.stage_new", raise_if_not_found=False
        )
        stage_progress = self._demo_ref_data(env, "service.desk.stage", "In Progress") or env.ref(
            "tv_service_desk.stage_in_progress", raise_if_not_found=False
        )
        stage_closed = self._demo_ref_data(env, "service.desk.stage", "Closed") or env.ref(
            "tv_service_desk.stage_done", raise_if_not_found=False
        )
        stage_cancelled = self._demo_ref_data(env, "service.desk.stage", "Cancelled") or env.ref(
            "tv_service_desk.stage_cancelled", raise_if_not_found=False
        )
        open_stages = Stage.search([("is_closed", "=", False)])

        team = Team.search([("name", "=", DEMO_TEAM_NAME)], limit=1)
        if not team:
            team = Team.create({
                "name": DEMO_TEAM_NAME,
                "leader_id": users["leader"].id,
                "member_ids": [(6, 0, [users["agent"].id, users["support"].id])],
                "assignment_method": "round_robin",
                "open_stage_ids": [(6, 0, open_stages.ids)],
            })
        else:
            team.write({
                "leader_id": users["leader"].id,
                "member_ids": [(6, 0, [users["agent"].id, users["support"].id])],
            })

        tags = Tag.browse()
        for tag_name in ("Urgent", "VIP", "Bug", "Feature", "Billing"):
            tag = Tag.search([("name", "=", "%s %s" % (DEMO_MARKER, tag_name))], limit=1)
            if not tag:
                tag = Tag.create({"name": "%s %s" % (DEMO_MARKER, tag_name)})
            tags |= tag

        cat_hardware = Category.search(
            [("name", "=", "%s Hardware" % DEMO_MARKER)], limit=1
        )
        if not cat_hardware:
            cat_hardware = Category.create({"name": "%s Hardware" % DEMO_MARKER})
        sub_laptop = Category.search(
            [("name", "=", "%s Laptop" % DEMO_MARKER)], limit=1
        )
        if not sub_laptop:
            sub_laptop = Category.create({
                "name": "%s Laptop" % DEMO_MARKER,
                "parent_id": cat_hardware.id,
            })

        ticket_type = TicketType.search(
            [("name", "=", "%s Support" % DEMO_MARKER)], limit=1
        )
        if not ticket_type:
            ticket_type = TicketType.create({"name": "%s Support" % DEMO_MARKER})

        subject_type = SubjectType.search(
            [("name", "=", "%s Implementation" % DEMO_MARKER)], limit=1
        )
        if not subject_type:
            subject_type = SubjectType.create({
                "name": "%s Implementation" % DEMO_MARKER,
            })

        alarm_popup = env.ref("tv_service_desk.alarm_5_minutes_popup", raise_if_not_found=False)
        alarm_email = env.ref("tv_service_desk.alarm_1_hour_email", raise_if_not_found=False)

        sla = Sla.search([("name", "=", "%s Standard SLA" % DEMO_MARKER)], limit=1)
        if not sla and stage_closed:
            sla = Sla.create({
                "name": "%s Standard SLA" % DEMO_MARKER,
                "team_id": team.id,
                "target_stage_id": stage_closed.id,
                "sla_days": 2,
                "sla_hours": 0,
                "sla_minutes": 0,
                "priority_id": Priority.search([("name", "=", "High")], limit=1).id,
            })

        followup = AutoFollowup.search(
            [("name", "=", "%s Follow-up" % DEMO_MARKER)], limit=1
        )
        if not followup:
            template = env.ref(
                "tv_service_desk.mail_template_ticket_feedback_request",
                raise_if_not_found=False,
            )
            if template:
                followup = AutoFollowup.create({
                    "name": "%s Follow-up" % DEMO_MARKER,
                    "line_ids": [(0, 0, {
                        "interval": 3,
                        "mail_template_id": template.id,
                    })],
                })

        partner = env["res.partner"].search(
            [("name", "ilike", "%s Acme" % DEMO_MARKER)], limit=1
        )
        today = fields.Date.context_today(self)
        hour_pkg = HourPackage.search(
            [("name", "=", "%s Acme Hours" % DEMO_MARKER)], limit=1
        )
        if not hour_pkg and partner:
            hour_pkg = HourPackage.create({
                "name": "%s Acme Hours" % DEMO_MARKER,
                "partner_id": partner.id,
                "date_start": today,
                "date_end": today + timedelta(days=365),
                "initial_allocated_hours": 40.0,
            })

        contract = Contract.search(
            [("name", "=", "%s Acme Support" % DEMO_MARKER)], limit=1
        )
        if not contract and partner:
            contract = Contract.create({
                "name": "%s Acme Support" % DEMO_MARKER,
                "partner_id": partner.id,
                "total_hours": 100.0,
                "date_start": today,
                "date_end": today + timedelta(days=180),
                "state": "active",
            })

        tab = FormTab.search(
            [("name", "=", "%s Extra Info" % DEMO_MARKER)], limit=1
        )
        if not tab:
            tab = FormTab.create({
                "name": "%s Extra Info" % DEMO_MARKER,
                "technical_name": "demo_extra_info",
                "anchor_tab": "other_information",
                "position": "after",
            })
            tab._create_form_view_inherit()

        field = FormField.search(
            [("technical_name", "=", "demo_customer_ref")], limit=1
        )
        if not field:
            field = FormField.create({
                "name": "%s Customer Reference" % DEMO_MARKER,
                "technical_name": "demo_customer_ref",
                "field_type": "char",
                "tab_id": tab.id,
                "anchor_field": "partner_id",
                "position": "after",
            })
            field._create_form_view_inherit()

        project = Project.search([("name", "=", "%s Helpdesk Project" % DEMO_MARKER)], limit=1)
        if not project:
            project = Project.create({"name": "%s Helpdesk Project" % DEMO_MARKER})

        repair_product = Product.search(
            [("default_code", "=", "DEMO-REPAIR-UNIT")], limit=1
        )
        if not repair_product:
            repair_product = Product.create({
                "name": "%s Laptop Repair Unit" % DEMO_MARKER,
                "default_code": "DEMO-REPAIR-UNIT",
                "type": "product",
                "list_price": 500.0,
            })

        return {
            "team": team,
            "stages": {
                "new": stage_new,
                "progress": stage_progress,
                "closed": stage_closed,
                "cancelled": stage_cancelled,
            },
            "tags": tags,
            "category": cat_hardware,
            "subcategory": sub_laptop,
            "ticket_type": ticket_type,
            "subject_type": subject_type,
            "alarms": Alarm.browse([a.id for a in (alarm_popup, alarm_email) if a]),
            "sla": sla,
            "followup": followup,
            "hour_package": hour_pkg,
            "contract": contract,
            "custom_tab": tab,
            "custom_field": field,
            "project": project,
            "repair_product": repair_product,
            "priorities": {
                p.name: p
                for p in Priority.search([])
            },
        }

    # -------------------------------------------------------------------------
    # Tickets (25+)
    # -------------------------------------------------------------------------

    @api.model
    def _demo_create_tickets(self, env, users, partners, master):
        Ticket = env["service.desk.ticket"]
        ctx = {
            "mail_create_nosubscribe": True,
            "mail_notrack": True,
            "tracking_disable": True,
        }
        team = master["team"]
        stages = master["stages"]
        pri = master["priorities"]

        subjects = [
            ("New customer onboarding request", "new", "Low", "new"),
            ("Cannot login to portal", "new", "High", "new"),
            ("Printer not working in office", "progress", "Medium", "staff_replied"),
            ("Email integration failure", "progress", "Urgent", "customer_replied"),
            ("SLA breach investigation", "progress", "High", "new"),
            ("Invoice mismatch on last bill", "new", "Medium", "new"),
            ("Request for new user account", "new", "Low", "new"),
            ("VPN connection drops frequently", "progress", "High", "staff_replied"),
            ("Website checkout error", "progress", "Urgent", "customer_replied"),
            ("Backup restore needed", "new", "High", "new"),
            ("License renewal question", "new", "Low", "new"),
            ("Mobile app crash on startup", "progress", "Medium", "new"),
            ("Password reset not received", "new", "Medium", "new"),
            ("API rate limit exceeded", "progress", "High", "staff_replied"),
            ("Custom report not generating", "progress", "Medium", "new"),
            ("Hardware repair - broken screen", "progress", "High", "new"),
            ("Training session scheduling", "new", "Low", "new"),
            ("Data export for audit", "progress", "Medium", "staff_replied"),
            ("Firewall rule change request", "new", "Urgent", "new"),
            ("Contract hours balance inquiry", "new", "Low", "new"),
            ("Closed - issue resolved", "closed", "Low", "staff_replied"),
            ("Closed - duplicate ticket", "closed", "Low", "new"),
            ("Closed - customer satisfied", "closed", "Medium", "staff_replied"),
            ("Cancelled - customer withdrew", "cancelled", "Low", "new"),
            ("Waiting for customer documents", "progress", "Medium", "staff_replied"),
        ]

        tickets = Ticket.browse()
        alarm_ids = master["alarms"].ids
        followup = master["followup"]
        contract = master["contract"]

        for idx, (subject, stage_key, priority_name, replied) in enumerate(subjects):
            full_subject = "%s %s" % (DEMO_MARKER, subject)
            if Ticket.search([("subject", "=", full_subject)], limit=1):
                continue

            partner = partners[idx % len(partners)]
            stage = stages.get(stage_key) or stages["new"]
            priority = pri.get(priority_name) or list(pri.values())[0]
            assignee = users["agent"] if idx % 2 == 0 else users["support"]

            vals = {
                "subject": full_subject,
                "description": "<p>%s implementation demo ticket #%d.</p>" % (DEMO_MARKER, idx + 1),
                "partner_id": partner.id,
                "team_id": team.id,
                "user_id": assignee.id,
                "stage_id": stage.id,
                "priority_id": priority.id,
                "ticket_type_id": master["ticket_type"].id,
                "subject_type_id": master["subject_type"].id,
                "category_id": master["category"].id,
                "subcategory_id": master["subcategory"].id,
                "tag_ids": [(6, 0, master["tags"].ids)],
                "replied_status": replied,
            }
            if idx < 5 and alarm_ids:
                vals["alarm_ids"] = [(6, 0, alarm_ids)]
            if idx == 4 and followup:
                vals["auto_followup"] = True
                vals["followup_template_id"] = followup.id
            if idx == 19 and contract:
                vals["support_contract_id"] = contract.id
            if master["custom_field"]:
                vals["demo_customer_ref"] = "REF-%04d" % (idx + 1)

            ticket = Ticket.with_context(**ctx).create(vals)
            tickets |= ticket

        return tickets

    # -------------------------------------------------------------------------
    # Tasks, repairs, sticky notes, ratings
    # -------------------------------------------------------------------------

    @api.model
    def _demo_create_tasks(self, env, users, tickets, master):
        Task = env["project.task"]
        project = master["project"]
        if not project:
            return Task.browse()

        task_tickets = tickets[:6]
        tasks = Task.browse()
        for idx, ticket in enumerate(task_tickets):
            name = "%s Task for %s" % (DEMO_MARKER, ticket.name)
            if Task.search([("name", "=", name)], limit=1):
                continue
            tasks |= Task.create({
                "name": name,
                "project_id": project.id,
                "sd_ticket_id": ticket.id,
                "user_ids": [(6, 0, [users["agent"].id])],
                "description": ticket.description,
                "partner_id": ticket.partner_id.id,
            })
        return tasks

    @api.model
    def _demo_create_repairs(self, env, users, tickets, master):
        Repair = env["repair.order"]
        product = master["repair_product"]
        if not product:
            return Repair.browse()

        repairs = Repair.browse()
        repair_tickets = tickets.filtered(lambda t: "repair" in (t.subject or "").lower())[:3]
        if not repair_tickets:
            repair_tickets = tickets[:3]

        for ticket in repair_tickets:
            existing = Repair.search([
                ("partner_id", "=", ticket.partner_id.id),
                ("product_id", "=", product.id),
            ], limit=1)
            if existing:
                ticket.write({"repair_order_ids": [(4, existing.id)]})
                repairs |= existing
                continue
            repair = Repair.with_context(
                sd_link_ticket_id=ticket.id,
            ).create({
                "partner_id": ticket.partner_id.id,
                "product_id": product.id,
                "internal_notes": ticket.description,
            })
            ticket.write({
                "repair_product_id": product.id,
                "repair_order_ids": [(4, repair.id)],
            })
            repairs |= repair
        return repairs

    @api.model
    def _demo_create_sticky_notes(self, env, users, tickets):
        Note = env["service.desk.sticky.note"]
        notes = Note.browse()
        samples = [
            ("Call customer back", 1),
            ("Waiting for parts", 3),
            ("Escalated to vendor", 5),
            ("VIP - handle with care", 2),
            ("Follow up Friday", 4),
            ("Internal only note", 0),
            ("Check SLA deadline", 6),
            ("Document workaround", 7),
        ]
        for title, ticket_idx in samples:
            if ticket_idx >= len(tickets):
                continue
            ticket = tickets[ticket_idx]
            full_title = "%s %s" % (DEMO_MARKER, title)
            if Note.search([("name", "=", full_title), ("ticket_id", "=", ticket.id)], limit=1):
                continue
            notes |= Note.create({
                "name": full_title,
                "ticket_id": ticket.id,
                "user_id": users["leader"].id,
                "note": "<p>%s</p>" % title,
                "color": STICKY_NOTE_COLOR_PALETTE[ticket_idx % len(STICKY_NOTE_COLOR_PALETTE)],
                "is_shared": ticket_idx % 2 == 0,
            })
        return notes

    @api.model
    def _demo_set_ratings(self, tickets):
        closed = tickets.filtered(lambda t: t.stage_id.is_closed)
        ratings = ("5", "4", "5", "3", "4")
        count = 0
        for ticket, rating in zip(closed, ratings):
            ticket.write({"feedback_rating": rating})
            count += 1
        return count
