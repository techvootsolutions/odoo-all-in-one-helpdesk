/** @odoo-module **/

import { Message } from "@mail/core/common/message";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";

patch(Message.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(() => {
            if (!this.shadowRoot) {
                return;
            }
            const thread = this.message?.thread;
            if (thread?.model !== "service.desk.ticket") {
                return;
            }
            const style = document.createElement("style");
            style.textContent = `
                *, *::before, *::after {
                    color: #212529 !important;
                    background-color: transparent !important;
                }
                a, a * {
                    color: #0d6efd !important;
                    text-decoration: underline !important;
                }
            `;
            this.shadowRoot.appendChild(style);
        });
    },
});
