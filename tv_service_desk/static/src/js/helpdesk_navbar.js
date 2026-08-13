/** @odoo-module **/

import { NavBar } from "@web/webclient/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { useBus, useService } from "@web/core/utils/hooks";
import { router, routerBus } from "@web/core/browser/router";
import { onMounted, onWillUnmount } from "@odoo/owl";

const HELPDESK_ROOT_XMLID = "tv_service_desk.menu_service_desk_root";

patch(NavBar.prototype, {
    setup() {
        super.setup(...arguments);
        this.actionService = useService("action");

        const updateActiveMenu = () => this._updateHelpdeskMenuActiveState();

        useBus(routerBus, "ROUTE_CHANGE", updateActiveMenu);

        onMounted(() => {
            this.env.bus.addEventListener("ACTION_MANAGER:UPDATE", updateActiveMenu);
            this.env.bus.addEventListener("MENUS:APP-CHANGED", updateActiveMenu);
            updateActiveMenu();
        });

        onWillUnmount(() => {
            this.env.bus.removeEventListener("ACTION_MANAGER:UPDATE", updateActiveMenu);
            this.env.bus.removeEventListener("MENUS:APP-CHANGED", updateActiveMenu);
        });
    },

    async adapt() {
        const result = await super.adapt(...arguments);
        this._updateHelpdeskMenuActiveState();
        return result;
    },

    _isHelpdeskApp() {
        return this.currentApp?.xmlid === HELPDESK_ROOT_XMLID;
    },

    _getActiveHelpdeskSectionId() {
        const menuId = Number(router.current?.menu_id || 0);
        if (menuId) {
            const menu = this.menuService.getMenu(menuId);
            if (menu?.appID === this.currentApp?.id) {
                let current = menu;
                while (current && current.id !== this.currentApp?.id) {
                    if (current.parentID === this.currentApp?.id) {
                        return current.id;
                    }
                    current = this.menuService.getMenu(current.parentID);
                }
            }
        }

        const controller = this.actionService.currentController;
        const action = controller?.action;
        if (!action) {
            return null;
        }

        const actionIds = new Set(
            [action.id, action.xml_id, action.tag].filter((value) => value !== undefined && value !== null)
        );
        const menus = this.menuService.getAll();
        const match = menus.find(
            (menu) =>
                menu.appID === this.currentApp?.id &&
                menu.parentID === this.currentApp?.id &&
                actionIds.has(menu.actionID)
        );
        return match?.id || null;
    },

    _updateHelpdeskMenuActiveState() {
        const sectionsRoot = this.appSubMenus?.el;
        if (!sectionsRoot) {
            return;
        }

        sectionsRoot.querySelectorAll(".o_nav_entry.focus, .dropdown-toggle.focus").forEach((entry) => {
            entry.classList.remove("focus");
        });

        if (!this._isHelpdeskApp()) {
            return;
        }

        const activeSectionId = this._getActiveHelpdeskSectionId();
        if (!activeSectionId) {
            return;
        }

        const activeTarget = sectionsRoot.querySelector(`[data-section="${activeSectionId}"]`);
        if (!activeTarget) {
            return;
        }

        const navEntry = activeTarget.closest(".o_nav_entry, .dropdown-toggle");
        navEntry?.classList.add("focus");
    },
});
