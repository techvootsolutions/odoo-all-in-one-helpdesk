"""Module hooks and shared maintenance helpers."""


def _deactivate_broken_ticket_form_inherits(cr):
    """Disable invalid custom tab/field inherits that block module upgrades."""
    cr.execute(
        """
        UPDATE ir_ui_view
           SET active = false
         WHERE model = 'service.desk.ticket'
           AND mode = 'extension'
           AND (
                arch_db LIKE '%%page[@name=''False'']%%'
             OR arch_db LIKE '%%page[@name="False"]%%'
             OR arch_db LIKE '%%page[@name=''false'']%%'
           )
        """
    )


def pre_init_hook(cr):
    _deactivate_broken_ticket_form_inherits(cr)


def _grant_helpdesk_access_to_demo_user(env):
    """Give Marc Demo (login: demo) access to the Helpdesk app and integrations."""
    demo = env.ref("base.user_demo", raise_if_not_found=False)
    if not demo:
        return
    # Use the same inverse fields as the user form (Preferences / Extra Rights).
    demo.sudo().write(
        {
            "sd_helpdesk_role": "user",
            "sd_sticky_notes_role": "user",
            "sd_ticket_alarm": True,
            "sd_sla_policy": True,
            "sd_helpdesk_task": True,
            "sd_helpdesk_timesheet": True,
            "sd_crm_helpdesk": True,
            "sd_sale_helpdesk": True,
            "sd_purchase_helpdesk": True,
            "sd_invoice_helpdesk": True,
            "sd_repair_helpdesk": True,
            "sd_custom_field_tab": True,
            "sd_whatsapp_feature": True,
        }
    )


def _sync_helpdesk_repair_users(env):
    """Ensure Helpdesk repair users can access repair.order (Inventory/User)."""
    repair_group = env.ref("tv_service_desk.group_service_desk_repair", raise_if_not_found=False)
    stock_group = env.ref("stock.group_stock_user", raise_if_not_found=False)
    if not repair_group or not stock_group:
        return
    users = env["res.users"].sudo().search([("group_ids", "in", repair_group.id)])
    users.filtered(lambda user: stock_group not in user.group_ids).write(
        {"group_ids": [(4, stock_group.id)]}
    )


def _sync_helpdesk_timesheet_users(env):
    """Ensure Helpdesk timesheet users also have core Timesheets access."""
    timesheet_group = env.ref("tv_service_desk.group_service_desk_timesheet", raise_if_not_found=False)
    hr_timesheet_group = env.ref("hr_timesheet.group_hr_timesheet_user", raise_if_not_found=False)
    if not timesheet_group or not hr_timesheet_group:
        return
    users = env["res.users"].sudo().search([("group_ids", "in", timesheet_group.id)])
    users.filtered(lambda user: hr_timesheet_group not in user.group_ids).write(
        {"group_ids": [(4, hr_timesheet_group.id)]}
    )


def post_init_hook(env):
    env["service.desk.stage"]._repair_all_references()
    tickets = env["service.desk.ticket"].search([])
    if tickets:
        tickets._compute_sd_ui_flags()
    env["res.users"]._migrate_deprecated_timezones()
    _sync_helpdesk_timesheet_users(env)
    _sync_helpdesk_repair_users(env)
    _grant_helpdesk_access_to_demo_user(env)
    env["service.desk.form.field"]._cleanup_orphan_custom_field_artifacts()
    env["service.desk.customer.hour.package"]._run_auto_create_customer_hour_package()
    env["res.users"]._sync_helpdesk_inbox_notifications()
