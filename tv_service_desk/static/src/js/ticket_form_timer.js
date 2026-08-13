/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { onMounted, onWillUnmount } from "@odoo/owl";

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        this._sdFormTimerInterval = null;
        onMounted(() => this._sdStartFormTimerTicker());
        onWillUnmount(() => this._sdStopFormTimerTicker());
    },

    async onWillLoadRoot() {
        await super.onWillLoadRoot(...arguments);
        this._sdStartFormTimerTicker();
    },

    _sdStartFormTimerTicker() {
        this._sdStopFormTimerTicker();
        if (this.props.resModel !== "service.desk.ticket") {
            return;
        }
        this._sdFormTimerInterval = setInterval(() => {
            const record = this.model?.root;
            if (!record || !record.data.is_timer_running) {
                return;
            }
            const startIso = record.data.current_user_timer_start;
            if (!startIso) {
                return;
            }
            const baseHours = record.data.real_duration || 0;
            const startMs = typeof startIso === "string"
                ? Date.parse(startIso.replace(" ", "T"))
                : startIso?.ts ?? Date.parse(String(startIso));
            if (!startMs || Number.isNaN(startMs)) {
                return;
            }
            const elapsedHours = (Date.now() - startMs) / 3600000;
            const display = (baseHours + elapsedHours).toFixed(2);
            const fieldNode = this.rootRef?.el?.querySelector(
                '.o_field_widget[name="real_duration"] .o_field_float, .o_field_widget[name="real_duration"] span, .o_field_widget[name="real_duration"]'
            );
            if (fieldNode) {
                fieldNode.textContent = display;
            }
        }, 1000);
    },

    _sdStopFormTimerTicker() {
        if (this._sdFormTimerInterval) {
            clearInterval(this._sdFormTimerInterval);
            this._sdFormTimerInterval = null;
        }
    },
});
