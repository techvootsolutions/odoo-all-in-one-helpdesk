/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, useState, onWillStart } from "@odoo/owl";
import { user } from "@web/core/user";

export class ServiceDeskDashboard extends Component {
    static template = "tv_service_desk.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            loading: true,
            myTicketsOnly: false,
            counts: {
                total_tickets: 0,
                open_tickets: 0,
                in_progress_tickets: 0,
                waiting_customer_tickets: 0,
                resolved_tickets: 0,
                closed_tickets: 0,
                my_tickets: 0,
                sla_breached: 0,
                avg_rating: 0,
                active_contracts: 0,
                low_balance_contracts: 0,
            },
            recentTickets: [],
            recentActivities: [],
            filterStageKpis: [],
            stageTables: [],
            pagerLimit: 4,
            tableOffsets: {},
            expandedStageIds: {},
            // Advanced filters
            filters: {
                teamLeaderId: "",
                teamId: "",
                assignedUserId: "",
                dateFilter: "month",
                dateStart: "",
                dateEnd: "",
            },
            filterOptions: {
                teamLeaders: [],
                teams: [],
                assignedUsers: [],
            },
            uiConfig: {
                visible_filter_codes: [],
                visible_filters: [],
                date_options: [],
                default_date_filter: "month",
                pager_limit: 4,
                show_whatsapp: false,
                show_extended_kpis: false,
            },
            initialDateFilter: "month",
        });

        onWillStart(async () => {
            await this._loadFilterOptions();
        });

        onMounted(() => this._loadDashboard());
    }

    isFilterVisible(code) {
        return this.state.uiConfig.visible_filter_codes.includes(code);
    }

    isCustomDate() {
        return this.state.filters.dateFilter === "custom";
    }

    get activeFilterTags() {
        const tags = [];
        const f = this.state.filters;

        if (f.teamLeaderId) {
            const leader = this.state.filterOptions.teamLeaders.find(
                (item) => String(item.id) === String(f.teamLeaderId)
            );
            tags.push({ key: "teamLeaderId", label: leader?.name || "Team Leader" });
        }
        if (f.teamId) {
            const team = this.state.filterOptions.teams.find(
                (item) => String(item.id) === String(f.teamId)
            );
            tags.push({ key: "teamId", label: team?.name || "Team" });
        }
        if (f.assignedUserId) {
            const assignee = this.state.filterOptions.assignedUsers.find(
                (item) => String(item.id) === String(f.assignedUserId)
            );
            tags.push({ key: "assignedUserId", label: assignee?.name || "Assigned User" });
        }
        if (f.dateFilter && f.dateFilter !== "all" && f.dateFilter !== this.state.initialDateFilter) {
            const option = this.state.uiConfig.date_options.find((item) => item.code === f.dateFilter);
            tags.push({ key: "dateFilter", label: option?.name || f.dateFilter });
        }
        return tags;
    }

    hasActiveFilterTags() {
        return this.activeFilterTags.length > 0;
    }

    async removeFilterTag(key) {
        if (key === "teamLeaderId") {
            this.state.filters.teamLeaderId = "";
        } else if (key === "teamId") {
            this.state.filters.teamId = "";
        } else if (key === "assignedUserId") {
            this.state.filters.assignedUserId = "";
        } else if (key === "dateFilter") {
            this.state.filters.dateFilter = this.state.initialDateFilter || "all";
            this.state.filters.dateStart = "";
            this.state.filters.dateEnd = "";
        }
        await this.onAdvancedFilterChange();
    }

    _syncExpandedStages(stageTables) {
        const expanded = { ...this.state.expandedStageIds };
        const activeIds = new Set(stageTables.map((table) => table.stage_id));
        for (const table of stageTables) {
            if (!(table.stage_id in expanded)) {
                expanded[table.stage_id] = true;
            }
        }
        for (const key of Object.keys(expanded)) {
            if (!activeIds.has(parseInt(key, 10))) {
                delete expanded[key];
            }
        }
        this.state.expandedStageIds = expanded;
    }

    isStageExpanded(stageId) {
        if (stageId in this.state.expandedStageIds) {
            return this.state.expandedStageIds[stageId];
        }
        return true;
    }

    toggleStageAccordion(stageId) {
        this.state.expandedStageIds = {
            ...this.state.expandedStageIds,
            [stageId]: !this.isStageExpanded(stageId),
        };
    }

    _getRpcFilters() {
        const f = this.state.filters;
        return {
            team_leader_id: f.teamLeaderId ? parseInt(f.teamLeaderId, 10) : false,
            team_id: f.teamId ? parseInt(f.teamId, 10) : false,
            assigned_user_id: f.assignedUserId ? parseInt(f.assignedUserId, 10) : false,
            filter_type: f.dateFilter || "all",
            date_start: f.dateFilter === "custom" ? f.dateStart : false,
            date_end: f.dateFilter === "custom" ? f.dateEnd : false,
            my_tickets: this.state.myTicketsOnly,
        };
    }

    async _loadFilterOptions() {
        try {
            const data = await this.orm.call(
                "service.desk.ticket",
                "get_dashboard_filter_options",
                []
            );
            this.state.filterOptions = {
                teamLeaders: data.team_leaders || [],
                teams: data.teams || [],
                assignedUsers: data.assigned_users || [],
            };
            this.state.uiConfig = data.config || this.state.uiConfig;
            const defaultDate = data.config?.default_date_filter || "month";
            this.state.initialDateFilter = defaultDate;
            this.state.filters.dateFilter = defaultDate;
            this.state.pagerLimit = data.config?.pager_limit || 4;
        } catch (error) {
            console.error("Error loading dashboard filter options:", error);
        }
    }

    async _loadDashboard() {
        this.state.loading = true;
        try {
            const data = await this.orm.call(
                "service.desk.ticket",
                "get_dashboard_data",
                [],
                {
                    filters: this._getRpcFilters(),
                    table_offsets: this.state.tableOffsets,
                }
            );

            this.state.counts = {
                total_tickets: data.total_tickets || 0,
                open_tickets: data.open_tickets || 0,
                in_progress_tickets: data.in_progress_tickets || 0,
                waiting_customer_tickets: data.waiting_customer_tickets || 0,
                resolved_tickets: data.resolved_tickets || 0,
                closed_tickets: data.closed_tickets || 0,
                my_tickets: data.my_tickets || 0,
                sla_breached: data.sla_breached || 0,
                avg_rating: data.avg_rating || 0.0,
                active_contracts: data.active_contracts || 0,
                low_balance_contracts: data.low_balance_contracts || 0,
            };

            this.state.recentTickets = data.recent_tickets || [];
            this.state.recentActivities = data.recent_activities || [];
            this.state.filterStageKpis = data.filter_stage_kpis || [];
            this.state.stageTables = data.stage_tables || [];
            this.state.pagerLimit = data.pager_limit || 4;
            this._syncExpandedStages(this.state.stageTables);
        } catch (error) {
            console.error("Error loading dashboard data:", error);
        } finally {
            this.state.loading = false;
        }
    }

    async onAdvancedFilterChange() {
        this.state.tableOffsets = {};
        await this._loadDashboard();
    }

    async onDateFilterChange(ev) {
        this.state.filters.dateFilter = ev.target.value;
        if (this.state.filters.dateFilter !== "custom") {
            this.state.filters.dateStart = "";
            this.state.filters.dateEnd = "";
        }
        await this.onAdvancedFilterChange();
    }

    async onSelectFilterChange(field, ev) {
        this.state.filters[field] = ev.target.value;
        await this.onAdvancedFilterChange();
    }

    async onCustomDateChange(field, ev) {
        this.state.filters[field] = ev.target.value;
        if (this.state.filters.dateStart && this.state.filters.dateEnd) {
            await this.onAdvancedFilterChange();
        }
    }

    toggleMyTickets() {
        this.state.myTicketsOnly = !this.state.myTicketsOnly;
        this.state.tableOffsets = {};
        this._loadDashboard();
    }

    _buildActionDomain(extraDomain = []) {
        const rpcFilters = this._getRpcFilters();
        return this.orm.call(
            "service.desk.ticket",
            "build_dashboard_base_domain",
            [rpcFilters]
        ).then((domain) => {
            if (!extraDomain.length) {
                return domain;
            }
            if (!domain.length) {
                return extraDomain;
            }
            return ["&", ...domain, ...extraDomain];
        });
    }

    async openFilteredTicketsByStage(stageId) {
        const domain = await this._buildActionDomain([["stage_id", "=", stageId]]);
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Tickets",
            res_model: "service.desk.ticket",
            views: [[false, "list"], [false, "kanban"], [false, "form"]],
            domain,
        });
    }

    async openFilteredTickets(cardType) {
        let extraDomain = [];
        let name = "Tickets";
        let resModel = "service.desk.ticket";

        switch (cardType) {
            case "total":
                name = "Total Tickets";
                break;
            case "open":
                extraDomain = [
                    ["stage_id.is_closed", "=", false],
                    ["stage_id.name", "in", ["New", "Open"]],
                ];
                name = "Open Tickets";
                break;
            case "progress":
                extraDomain = [
                    ["stage_id.is_closed", "=", false],
                    ["stage_id.name", "ilike", "Progress"],
                ];
                name = "In Progress Tickets";
                break;
            case "waiting":
                extraDomain = [["stage_id.name", "ilike", "Waiting"]];
                name = "Waiting Customer";
                break;
            case "resolved":
                extraDomain = [["stage_id.name", "ilike", "Resolved"]];
                name = "Resolved Tickets";
                break;
            case "closed":
                extraDomain = [["stage_id.is_closed", "=", true]];
                name = "Closed Tickets";
                break;
            case "my": {
                const uid = user.userId;
                extraDomain = ["|", ["user_id", "=", uid], ["assigned_user_ids", "in", [uid]]];
                name = "My Tickets";
                break;
            }
            case "sla":
                extraDomain = [["sla_status", "=", "failed"]];
                name = "SLA Breached Tickets";
                break;
            case "rating":
                extraDomain = [
                    ["feedback_rating", "!=", false],
                    ["feedback_rating", "!=", "0"],
                ];
                name = "Customer Rated Tickets";
                break;
            case "active_contracts":
                resModel = "service.desk.support.contract";
                this.action.doAction({
                    type: "ir.actions.act_window",
                    name: "Active Support Contracts",
                    res_model: resModel,
                    views: [[false, "list"], [false, "form"]],
                    domain: [["state", "=", "active"]],
                });
                return;
            case "low_contracts":
                resModel = "service.desk.support.contract";
                this.action.doAction({
                    type: "ir.actions.act_window",
                    name: "Low Balance Contracts",
                    res_model: resModel,
                    views: [[false, "list"], [false, "form"]],
                    domain: [["state", "=", "active"], ["remaining_hours", "<=", 2]],
                });
                return;
        }

        const domain = await this._buildActionDomain(extraDomain);
        this.action.doAction({
            type: "ir.actions.act_window",
            name,
            res_model: resModel,
            views: [[false, "list"], [false, "kanban"], [false, "form"]],
            domain,
        });
    }

    async onStageTablePager(stageId, direction, ev) {
        if (ev) {
            ev.stopPropagation();
        }
        const table = this.state.stageTables.find((t) => t.stage_id === stageId);
        if (!table) {
            return;
        }
        const limit = this.state.pagerLimit;
        let offset = table.offset || 0;
        if (direction === "next" && table.has_next) {
            offset += limit;
        } else if (direction === "prev" && table.has_prev) {
            offset = Math.max(0, offset - limit);
        } else {
            return;
        }
        this.state.tableOffsets = { ...this.state.tableOffsets, [String(stageId)]: offset };
        await this._loadDashboard();
    }

    getPageEnd(table) {
        return Math.min((table.offset || 0) + (table.limit || 0), table.total || 0);
    }

    getStageIcon(name) {
        const label = (name || "").toLowerCase();
        if (label.includes("new")) return "fa-inbox";
        if (label.includes("progress")) return "fa-spinner";
        if (label.includes("wait")) return "fa-hourglass-half";
        if (label.includes("resolv") || label.includes("done")) return "fa-check-circle";
        if (label.includes("cancel")) return "fa-times-circle";
        if (label.includes("close")) return "fa-archive";
        if (label.includes("reopen")) return "fa-refresh";
        return "fa-ticket";
    }

    getStageColor(stage) {
        if (!stage) return "#4b5563";
        if (stage.color && typeof stage.color === "string" && stage.color.startsWith("#")) {
            return stage.color;
        }
        const name = (stage.name || "").toLowerCase();
        if (name.includes("new")) return "#4b5563";
        if (name.includes("progress")) return "#2563eb";
        if (name.includes("done") || name.includes("resolv")) return "#16a34a";
        if (name.includes("close")) return "#06b6d4";
        if (name.includes("cancel")) return "#dc2626";
        if (name.includes("reopen")) return "#1f2937";
        return stage.color || "#4b5563";
    }

    openTicket(ticketId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "service.desk.ticket",
            res_id: ticketId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async onWhatsappClick(ticketId, ev) {
        if (ev) {
            ev.stopPropagation();
        }
        const action = await this.orm.call(
            "service.desk.ticket",
            "action_send_by_whatsapp",
            [[ticketId]]
        );
        if (action) {
            await this.action.doAction(action);
        }
    }

    onNewTicket() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "New Ticket",
            res_model: "service.desk.ticket",
            views: [[false, "form"]],
            target: "current",
            context: { form_view_initial_mode: "edit" },
        });
    }

    onMyTickets() {
        this.openFilteredTickets("my");
    }

    onReports() {
        this.action.doAction("tv_service_desk.action_service_desk_ticket_analysis");
    }
}

registry.category("actions").add("tv_service_desk_dashboard", ServiceDeskDashboard);
