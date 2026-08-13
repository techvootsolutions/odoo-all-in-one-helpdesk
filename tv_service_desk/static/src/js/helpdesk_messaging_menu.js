/** @odoo-module **/

import { MessagingMenu } from "@mail/core/public_web/messaging_menu";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

const HELPDESK_ROOT_XMLID = "tv_service_desk.menu_service_desk_root";

patch(MessagingMenu.prototype, {
    setup() {
        super.setup(...arguments);
        this.menuService = useService("menu");
    },

    _isHelpdeskApp() {
        return this.menuService.getCurrentApp()?.xmlid === HELPDESK_ROOT_XMLID;
    },

    get helpdeskSystrayIconClass() {
        return this._isHelpdeskApp()
            ? "fa fa-lg fa-bell o_tv_helpdesk_notification_systray"
            : "fa fa-lg fa-comments";
    },

    get helpdeskSystrayAriaLabel() {
        return this._isHelpdeskApp() ? _t("Notifications") : _t("Messages");
    },

    onHelpdeskSystrayIconClick() {
        if (this._isHelpdeskApp()) {
            this.store.discuss.activeTab = "notification";
            return;
        }
        this.store.discuss.activeTab =
            this.ui.isSmall && this.store.discuss.activeTab === "notification"
                ? "notification"
                : this.store.discuss.activeTab;
    },

    beforeOpen() {
        super.beforeOpen(...arguments);
        if (this._isHelpdeskApp()) {
            this.store.discuss.activeTab = "notification";
        }
    },
});
