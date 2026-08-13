/** @odoo-module **/

import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { formatElapsed } from "./timer_utils";

export class TicketTimerSystray extends Component {
    static template = "tv_service_desk.TicketTimerSystray";
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            active: false,
            elapsed: "00:00:00",
            ticketName: "",
            ticketId: false,
        });
        this._interval = null;
        this._timesheetEnabled = false;
        this._refreshing = false;

        onMounted(async () => {
            this._timesheetEnabled = await user.hasGroup(
                "tv_service_desk.group_service_desk_timesheet"
            );
            if (!this._timesheetEnabled) {
                return;
            }
            this._refreshTimer();
            this._interval = setInterval(() => this._refreshTimer(), 1000);
        });
        onWillUnmount(() => {
            if (this._interval) {
                clearInterval(this._interval);
            }
        });
    }

    async _refreshTimer() {
        if (!this._timesheetEnabled || this._refreshing) {
            return;
        }
        this._refreshing = true;
        try {
            const info = await this.orm.call(
                "service.desk.ticket",
                "get_user_active_timer_info",
                []
            );
            if (!info) {
                this.state.active = false;
                this.state.ticketId = false;
                this.state.ticketName = "";
                this.state.elapsed = "00:00:00";
                return;
            }
            this.state.active = true;
            this.state.ticketId = info.ticket_id;
            this.state.ticketName = info.ticket_name;
            this.state.elapsed = formatElapsed(info.start);
        } finally {
            this._refreshing = false;
        }
    }

    async onEndTimer() {
        if (!this.state.ticketId) {
            return;
        }
        await this.orm.call("service.desk.ticket", "action_stop_timer", [[this.state.ticketId]]);
        await this._refreshTimer();
    }

    onOpenTicket() {
        if (!this.state.ticketId) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "service.desk.ticket",
            res_id: this.state.ticketId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

let timesheetSystrayEnabled = false;
user.hasGroup("tv_service_desk.group_service_desk_timesheet").then((enabled) => {
    timesheetSystrayEnabled = enabled;
    if (enabled) {
        registry.category("systray").trigger("UPDATE");
    }
});

registry.category("systray").add(
    "tv_service_desk.TicketTimerSystray",
    {
        Component: TicketTimerSystray,
        isDisplayed: () => timesheetSystrayEnabled,
    },
    { sequence: 25 }
);
