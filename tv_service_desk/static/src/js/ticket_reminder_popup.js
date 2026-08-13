/** @odoo-module **/

import { Component, reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { rpc, ConnectionLostError } from "@web/core/network/rpc";

const POLL_INTERVAL_MS = 10000;
const BUS_CHANNEL = "tv_service_desk.ticket_reminder";

export class TicketReminderPopup extends Component {
    static template = "tv_service_desk.TicketReminderPopup";
    static props = {
        reminder: Object,
        onClose: Function,
        onOpenTicket: Function,
    };

    onCloseClick() {
        this.props.onClose(this.props.reminder.id);
    }

    onTicketClick(ev) {
        ev.preventDefault();
        this.props.onOpenTicket(this.props.reminder.id);
    }
}

export class TicketReminderContainer extends Component {
    static template = "tv_service_desk.TicketReminderContainer";
    static components = { TicketReminderPopup };
    static props = {
        remindersState: Object,
        dismissReminder: Function,
        openTicket: Function,
    };
}

function mergeReminders(state, payload) {
    const reminders = Array.isArray(payload) ? payload : [payload];
    const byId = new Map(state.reminders.map((reminder) => [reminder.id, reminder]));
    for (const reminder of reminders) {
        if (reminder?.id) {
            byId.set(reminder.id, reminder);
        }
    }
    state.reminders = [...byId.values()];
}

export const ticketReminderService = {
    dependencies: ["bus_service", "orm", "action"],

    async start(env, { bus_service, orm, action }) {
        const remindersState = reactive({ reminders: [] });

        async function dismissReminder(ticketId) {
            await orm.call(
                "service.desk.ticket",
                "action_mark_reminder_popup_shown",
                [[ticketId]]
            );
            remindersState.reminders = remindersState.reminders.filter(
                (reminder) => reminder.id !== ticketId
            );
        }

        async function openTicket(ticketId) {
            const act = await orm.call(
                "service.desk.ticket",
                "action_open_from_reminder_popup",
                [[ticketId]]
            );
            remindersState.reminders = remindersState.reminders.filter(
                (reminder) => reminder.id !== ticketId
            );
            await action.doAction(act);
        }

        async function pollReminders() {
            try {
                const reminders = await rpc("/service_desk/reminder_notify", {}, { silent: true });
                mergeReminders(remindersState, reminders);
            } catch (error) {
                if (!(error instanceof ConnectionLostError)) {
                    throw error;
                }
            }
        }

        bus_service.subscribe(BUS_CHANNEL, (payload) => {
            mergeReminders(remindersState, payload);
        });
        bus_service.start();

        registry.category("main_components").add("tv_service_desk.TicketReminderContainer", {
            Component: TicketReminderContainer,
            props: {
                remindersState,
                dismissReminder,
                openTicket,
            },
        });

        await pollReminders();
        browser.setInterval(pollReminders, POLL_INTERVAL_MS);
        browser.addEventListener("visibilitychange", () => {
            if (document.visibilityState === "visible") {
                pollReminders();
            }
        });

        return { remindersState, dismissReminder, openTicket, pollReminders };
    },
};

registry.category("services").add("tv_service_desk.ticket_reminder", ticketReminderService);
