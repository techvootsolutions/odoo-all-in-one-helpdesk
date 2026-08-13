/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";

class HelpdeskTicketPopover extends Component {
    static template = "tv_service_desk.HelpdeskTicketPopover";
    static props = {
        tickets: { type: Array },
        onAdd: { type: Function },
        onEdit: { type: Function },
        close: { type: Function },
    };

    onAddClick() {
        this.props.onAdd();
    }

    onEditClick(ticketId) {
        this.props.onEdit(ticketId);
    }
}

export class HelpdeskTicketField extends Component {
    static template = "tv_service_desk.HelpdeskTicketField";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.rootRef = useRef("root");
        this.state = useState({ tickets: null, loading: false });
        this.popover = usePopover(HelpdeskTicketPopover, {
            position: "bottom",
            closeOnClickAway: true,
        });
    }

    get count() {
        return this.props.record.data.sd_ticket_count || 0;
    }

    async loadTickets() {
        if (this.state.tickets !== null) {
            return this.state.tickets;
        }
        this.state.loading = true;
        const data = await this.orm.call(
            this.props.record.resModel,
            "get_helpdesk_ticket_widget_data",
            [[this.props.record.resId]]
        );
        this.state.tickets = data[this.props.record.resId] || [];
        this.state.loading = false;
        return this.state.tickets;
    }

    async onClick(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        const tickets = await this.loadTickets();
        this.popover.open(this.rootRef.el, {
            tickets,
            onAdd: () => this.onAddTicket(),
            onEdit: (ticketId) => this.onEditTicket(ticketId),
            close: () => this.popover.close(),
        });
    }

    _normalizeActWindowAction(action) {
        if (
            action?.type === "ir.actions.act_window" &&
            !action.views?.length &&
            action.view_mode
        ) {
            action.views = action.view_mode
                .split(",")
                .map((mode) => [false, mode.trim()]);
        }
        return action;
    }

    async onAddTicket() {
        this.popover.close();
        const action = await this.orm.call(
            this.props.record.resModel,
            "action_create_service_desk_ticket",
            [[this.props.record.resId]]
        );
        if (action) {
            this.action.doAction(this._normalizeActWindowAction(action));
        }
    }

    async onEditTicket(ticketId) {
        this.popover.close();
        const action = await this.orm.call(
            this.props.record.resModel,
            "action_helpdesk_ticket_widget_open",
            [[this.props.record.resId], ticketId]
        );
        if (action) {
            this.action.doAction(this._normalizeActWindowAction(action));
        }
    }
}

export const helpdeskTicketField = {
    component: HelpdeskTicketField,
};

registry.category("fields").add("helpdesk_ticket", helpdeskTicketField);
