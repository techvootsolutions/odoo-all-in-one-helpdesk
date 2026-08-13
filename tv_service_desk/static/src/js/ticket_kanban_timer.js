/** @odoo-module **/

import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { patch } from "@web/core/utils/patch";
import { onMounted, onWillUnmount } from "@odoo/owl";
import { formatElapsed } from "./timer_utils";

function refreshKanbanTimers(root) {
    if (!root) {
        return;
    }
    root.querySelectorAll(".o_sd_timer_display[data-start]").forEach((el) => {
        el.textContent = formatElapsed(el.dataset.start);
    });
}

patch(KanbanRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        this._sdTimerInterval = null;
        onMounted(() => {
            if (this.props.list.resModel !== "service.desk.ticket") {
                return;
            }
            refreshKanbanTimers(this.rootRef?.el);
            this._sdTimerInterval = setInterval(() => {
                refreshKanbanTimers(this.rootRef?.el);
            }, 1000);
        });
        onWillUnmount(() => {
            if (this._sdTimerInterval) {
                clearInterval(this._sdTimerInterval);
                this._sdTimerInterval = null;
            }
        });
    },
});
