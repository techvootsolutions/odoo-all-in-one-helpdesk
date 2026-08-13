from odoo import api, fields, models

STAGE_XMLIDS = (
    "stage_new",
    "stage_in_progress",
    "stage_waiting",
    "stage_done",
    "stage_cancelled",
    "stage_reopened",
)

CONFIG_STAGE_XMLIDS = {
    "tv_service_desk.stage_draft_id": "stage_new",
    "tv_service_desk.stage_reopened_id": "stage_reopened",
    "tv_service_desk.stage_cancel_id": "stage_cancelled",
    "tv_service_desk.stage_resolved_id": "stage_waiting",
    "tv_service_desk.stage_closed_id": "stage_done",
    "tv_service_desk.customer_replied_stage_id": "stage_in_progress",
    "tv_service_desk.staff_replied_stage_id": "stage_in_progress",
    "tv_service_desk.auto_close_stage_id": "stage_done",
    "tv_service_desk.auto_followup_stage_id": "stage_waiting",
}

CSV_STAGE_CONFIG_KEYS = (
    "tv_service_desk.dashboard_filter_stage_ids",
    "tv_service_desk.dashboard_table_stage_ids",
)


class ServiceDeskStage(models.Model):
    _name = "service.desk.stage"
    _description = "Service Desk Stage"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company")
    color = fields.Integer(string="Dashboard Color")
    fold = fields.Boolean(
        string="Folded in Kanban",
        help="Tickets in folded stages are hidden in the main pipeline.",
    )
    is_closed = fields.Boolean(string="Closing Stage")
    is_default = fields.Boolean(string="Default for New Tickets")
    mail_template_id = fields.Many2one(
        "mail.template",
        string="Email Template",
        domain="[('model', '=', 'service.desk.ticket')]",
    )
    next_stage_id = fields.Many2one(
        "service.desk.stage",
        string="Suggested Next Stage",
        ondelete="set null",
    )
    group_ids = fields.Many2many(
        "res.groups",
        string="Visible To",
        help="Leave empty to allow all service desk users.",
    )
    description = fields.Text()

    @api.model
    def _get_canonical_stages(self):
        stages = {}
        for xmlid in STAGE_XMLIDS:
            stage = self.env.ref(f"tv_service_desk.{xmlid}", raise_if_not_found=False)
            if stage:
                stages[xmlid] = stage
        return stages

    @api.model
    def _stage_from_xmlid(self, xmlid):
        return self.env.ref(f"tv_service_desk.{xmlid}", raise_if_not_found=False)

    @api.model
    def _valid_stage_id(self, stage_id):
        if not stage_id:
            return False
        return self.browse(stage_id).exists()

    @api.model
    def _repair_all_references(self):
        """Repair broken stage FKs and remove duplicate stage records."""
        self._repair_config_stage_parameters()
        self._repair_csv_stage_parameters()
        self._repair_ticket_stages()
        self._repair_stage_logs()
        self._repair_sla_policy_stages()
        self._repair_next_stage_links()
        self._deduplicate_named_stages()
        return True

    @api.model
    def get_config_stage_id(self, param_key, fallback_xmlid=None):
        icp = self.env["ir.config_parameter"].sudo()
        current = icp.get_param(param_key)
        current_id = int(current) if current and str(current).isdigit() else 0
        if self._valid_stage_id(current_id):
            return current_id
        if fallback_xmlid:
            stage = self._stage_from_xmlid(fallback_xmlid)
            if stage:
                return stage.id
        return 0

    @api.model
    def _repair_config_stage_parameters(self):
        icp = self.env["ir.config_parameter"].sudo()
        for param_key, xmlid in CONFIG_STAGE_XMLIDS.items():
            current = icp.get_param(param_key)
            current_id = int(current) if current and str(current).isdigit() else 0
            if self._valid_stage_id(current_id):
                continue
            stage = self._stage_from_xmlid(xmlid)
            if stage:
                icp.set_param(param_key, str(stage.id))

    @api.model
    def _repair_csv_stage_parameters(self):
        icp = self.env["ir.config_parameter"].sudo()
        all_stage_ids = set(self.search([]).ids)
        for param_key in CSV_STAGE_CONFIG_KEYS:
            raw = icp.get_param(param_key) or ""
            stage_ids = [int(x) for x in raw.split(",") if x.isdigit()]
            valid_ids = [sid for sid in stage_ids if sid in all_stage_ids]
            if valid_ids != stage_ids:
                icp.set_param(param_key, ",".join(str(sid) for sid in valid_ids))

    @api.model
    def _default_stage(self):
        stage = self.search([("is_default", "=", True)], limit=1)
        if not stage:
            stage = self._stage_from_xmlid("stage_new")
        if not stage:
            stage = self.search([], order="sequence, id", limit=1)
        return stage

    @api.model
    def _repair_ticket_stages(self):
        default_stage = self._default_stage()
        if not default_stage:
            return
        self.env.cr.execute(
            """
            UPDATE service_desk_ticket
               SET stage_id = %s
             WHERE stage_id IS NULL
                OR NOT EXISTS (
                    SELECT 1
                      FROM service_desk_stage s
                     WHERE s.id = service_desk_ticket.stage_id
                )
            """,
            (default_stage.id,),
        )

    @api.model
    def _repair_stage_logs(self):
        default_stage = self._default_stage()
        if not default_stage:
            return
        self.env.cr.execute(
            """
            UPDATE service_desk_stage_log
               SET old_stage_id = NULL
             WHERE old_stage_id IS NOT NULL
               AND NOT EXISTS (
                   SELECT 1
                     FROM service_desk_stage s
                    WHERE s.id = service_desk_stage_log.old_stage_id
               )
            """
        )
        self.env.cr.execute(
            """
            UPDATE service_desk_stage_log
               SET new_stage_id = %s
             WHERE new_stage_id IS NULL
                OR NOT EXISTS (
                    SELECT 1
                      FROM service_desk_stage s
                     WHERE s.id = service_desk_stage_log.new_stage_id
                )
            """,
            (default_stage.id,),
        )

    @api.model
    def _repair_next_stage_links(self):
        for stage in self.search([]):
            if stage.next_stage_id and not stage.next_stage_id.exists():
                stage.next_stage_id = False

    @api.model
    def _repair_sla_policy_stages(self):
        default_stage = self._default_stage()
        if not default_stage:
            return
        self.env.cr.execute(
            """
            UPDATE service_desk_sla_policy
               SET target_stage_id = %s
             WHERE target_stage_id IS NULL
                OR NOT EXISTS (
                    SELECT 1
                      FROM service_desk_stage s
                     WHERE s.id = service_desk_sla_policy.target_stage_id
                )
            """,
            (default_stage.id,),
        )

    @api.model
    def _table_exists(self, table_name):
        self.env.cr.execute(
            """
            SELECT 1
              FROM information_schema.tables
             WHERE table_schema = current_schema()
               AND table_name = %s
            """,
            (table_name,),
        )
        return bool(self.env.cr.fetchone())

    @api.model
    def _reassign_m2m_stage_rel(self, table, old_id, new_id, stage_column="stage_id"):
        """Point M2M relation rows from old stage to new stage without duplicates."""
        if not old_id or not new_id or old_id == new_id:
            return
        self.env.cr.execute(
            f"""
            DELETE FROM {table} rel_old
             WHERE rel_old.{stage_column} = %s
               AND EXISTS (
                   SELECT 1
                     FROM {table} rel_new
                    WHERE rel_new.{stage_column} = %s
                      AND rel_new.ctid <> rel_old.ctid
                      AND rel_new.team_id = rel_old.team_id
               )
            """,
            (old_id, new_id),
        )
        self.env.cr.execute(
            f"""
            UPDATE {table}
               SET {stage_column} = %s
             WHERE {stage_column} = %s
            """,
            (new_id, old_id),
        )

    @api.model
    def _reassign_config_m2m_stage_rel(self, table, old_id, new_id):
        if not old_id or not new_id or old_id == new_id:
            return
        self.env.cr.execute(
            f"""
            DELETE FROM {table} rel_old
             WHERE rel_old.stage_id = %s
               AND EXISTS (
                   SELECT 1
                     FROM {table} rel_new
                    WHERE rel_new.stage_id = %s
                      AND rel_new.ctid <> rel_old.ctid
                      AND rel_new.config_id = rel_old.config_id
               )
            """,
            (old_id, new_id),
        )
        self.env.cr.execute(
            f"""
            UPDATE {table}
               SET stage_id = %s
             WHERE stage_id = %s
            """,
            (new_id, old_id),
        )

    @api.model
    def _reassign_stage_id_sql(self, old_id, new_id):
        """Reassign stage FKs with SQL so post-migrate deletes are safe."""
        if not old_id or not new_id or old_id == new_id:
            return
        cr = self.env.cr
        cr.execute(
            "UPDATE service_desk_ticket SET stage_id = %s WHERE stage_id = %s",
            (new_id, old_id),
        )
        cr.execute(
            "UPDATE service_desk_stage_log SET old_stage_id = %s WHERE old_stage_id = %s",
            (new_id, old_id),
        )
        cr.execute(
            "UPDATE service_desk_stage_log SET new_stage_id = %s WHERE new_stage_id = %s",
            (new_id, old_id),
        )
        cr.execute(
            "UPDATE service_desk_stage SET next_stage_id = %s WHERE next_stage_id = %s",
            (new_id, old_id),
        )
        cr.execute(
            """
            UPDATE service_desk_sla_policy
               SET target_stage_id = %s
             WHERE target_stage_id = %s
            """,
            (new_id, old_id),
        )
        if self._table_exists("service_desk_team_open_stage_rel"):
            self._reassign_m2m_stage_rel(
                "service_desk_team_open_stage_rel", old_id, new_id,
            )
        if self._table_exists("sd_config_dashboard_filter_stage_rel"):
            self._reassign_config_m2m_stage_rel(
                "sd_config_dashboard_filter_stage_rel", old_id, new_id,
            )
        if self._table_exists("sd_config_dashboard_table_stage_rel"):
            self._reassign_config_m2m_stage_rel(
                "sd_config_dashboard_table_stage_rel", old_id, new_id,
            )

    @api.model
    def _reassign_stage_id(self, old_id, new_id):
        if not old_id or not new_id or old_id == new_id:
            return
        self._reassign_stage_id_sql(old_id, new_id)
        teams = self.env["service.desk.team"].sudo().search([("open_stage_ids", "in", old_id)])
        for team in teams:
            team.open_stage_ids = [(3, old_id), (4, new_id)]
        icp = self.env["ir.config_parameter"].sudo()
        for param_key in CONFIG_STAGE_XMLIDS:
            current = icp.get_param(param_key)
            if current and str(current).isdigit() and int(current) == old_id:
                icp.set_param(param_key, str(new_id))
        for param_key in CSV_STAGE_CONFIG_KEYS:
            raw = icp.get_param(param_key) or ""
            stage_ids = [int(x) for x in raw.split(",") if x.isdigit()]
            if old_id in stage_ids:
                stage_ids = [new_id if sid == old_id else sid for sid in stage_ids]
                icp.set_param(param_key, ",".join(str(sid) for sid in dict.fromkeys(stage_ids)))

    @api.model
    def _deduplicate_named_stages(self):
        canonical = self._get_canonical_stages()
        if not canonical:
            return
        canonical_ids = {stage.id for stage in canonical.values()}
        Stage = self.with_context(active_test=False)
        for stage in canonical.values():
            duplicates = Stage.search([("name", "=", stage.name), ("id", "!=", stage.id)])
            for duplicate in duplicates:
                self._reassign_stage_id(duplicate.id, stage.id)
            dup_ids = tuple(
                did for did in duplicates.ids
                if did not in canonical_ids
            )
            if dup_ids:
                # Safety net: ensure every FK is repointed before hard delete.
                self.env.cr.execute(
                    """
                    UPDATE service_desk_sla_policy
                       SET target_stage_id = %s
                     WHERE target_stage_id IN %s
                    """,
                    (stage.id, dup_ids),
                )
                self.env.cr.execute(
                    """
                    UPDATE service_desk_ticket
                       SET stage_id = %s
                     WHERE stage_id IN %s
                    """,
                    (stage.id, dup_ids),
                )
                self.env.cr.execute(
                    """
                    UPDATE service_desk_stage_log
                       SET old_stage_id = NULL
                     WHERE old_stage_id IN %s
                    """,
                    (dup_ids,),
                )
                self.env.cr.execute(
                    """
                    UPDATE service_desk_stage_log
                       SET new_stage_id = %s
                     WHERE new_stage_id IN %s
                    """,
                    (stage.id, dup_ids),
                )
                self.env.cr.execute(
                    """
                    UPDATE service_desk_stage
                       SET next_stage_id = %s
                     WHERE next_stage_id IN %s
                    """,
                    (stage.id, dup_ids),
                )
                self.env.cr.execute(
                    "DELETE FROM service_desk_stage WHERE id IN %s",
                    (dup_ids,),
                )
                duplicates.invalidate_recordset()

    def unlink(self):
        default_stage = self._default_stage()
        for stage in self:
            if default_stage and stage.id != default_stage.id:
                self._reassign_stage_id(stage.id, default_stage.id)
        return super().unlink()
