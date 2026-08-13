/** @odoo-module **/

import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useState, onWillStart } from "@odoo/owl";
import { user } from "@web/core/user";

const ODOO_COLORS = [
    "#F06050", "#F4A460", "#F7CD1F", "#6CC1ED", "#814968",
    "#EB7E7F", "#2C8397", "#475577", "#D6145F", "#30C381", "#9365B8", "#948686",
];

export class ServiceDeskTicketListController extends ListController {
    static template = "tv_service_desk.TicketListView";

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.state = useState({
            loadingCounts: true,
            activeFilter: "all",
            counts: {
                total: 0,
                open: 0,
                my_tickets: 0,
                sla_failed: 0,
                stages: [],
            },
        });
        this._statusFilterGroupId = null;

        onWillStart(async () => {
            await this._loadStatusCounts();
        });
    }

    async _loadStatusCounts() {
        try {
            const data = await this.orm.call(
                "service.desk.ticket",
                "get_ticket_status_counts",
                []
            );
            this.state.counts = {
                total: data.total || 0,
                open: data.open || 0,
                my_tickets: data.my_tickets || 0,
                sla_failed: data.sla_failed || 0,
                stages: data.stages || [],
            };
        } catch (error) {
            console.error("Failed to load ticket status counts:", error);
        } finally {
            this.state.loadingCounts = false;
        }
    }

    _clearStatusFilter() {
        if (this._statusFilterGroupId) {
            this.env.searchModel.deactivateGroup(this._statusFilterGroupId);
            this._statusFilterGroupId = null;
        }
    }

    async _applyDomainFilter(description, domain, filterKey) {
        this._clearStatusFilter();
        this.state.activeFilter = filterKey;

        if (!domain || domain.length === 0) {
            await this.env.searchModel.search();
            return;
        }

        const filters = this.env.searchModel.createNewFilters([{
            description,
            domain,
            isCustom: true,
        }]);
        if (filters && filters.length) {
            this._statusFilterGroupId = filters[0].groupId;
        }
        await this.env.searchModel.search();
        await this._loadStatusCounts();
    }

    onFilterAll() {
        return this._applyDomainFilter("", [], "all");
    }

    onFilterOpen() {
        return this._applyDomainFilter(
            "Open Tickets",
            [["stage_id.is_closed", "=", false]],
            "open"
        );
    }

    onFilterMyTickets() {
        const uid = user.userId;
        return this._applyDomainFilter(
            "My Tickets",
            ["|", ["user_id", "=", uid], ["assigned_user_ids", "in", [uid]]],
            "my"
        );
    }

    onFilterSlaFailed() {
        return this._applyDomainFilter(
            "SLA Failed",
            [["sla_status", "=", "failed"]],
            "sla"
        );
    }

    onFilterStage(stage) {
        return this._applyDomainFilter(
            stage.name,
            [["stage_id", "=", stage.id]],
            `stage_${stage.id}`
        );
    }

    getStageIcon(stage) {
        const name = (stage.name || "").toLowerCase();
        if (name.includes("new")) return "fa-inbox";
        if (name.includes("progress")) return "fa-spinner";
        if (name.includes("wait")) return "fa-hourglass-half";
        if (name.includes("resolv")) return "fa-check-circle";
        if (name.includes("cancel")) return "fa-times-circle";
        if (name.includes("close")) return "fa-archive";
        return "fa-ticket";
    }

    getStageColor(stage) {
        return stage.color || ODOO_COLORS[0];
    }
}

export const serviceDeskTicketListView = {
    ...listView,
    Controller: ServiceDeskTicketListController,
};

registry.category("views").add("service_desk_ticket_list", serviceDeskTicketListView);
