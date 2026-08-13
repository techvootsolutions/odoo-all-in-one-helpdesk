/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";

patch(FormController.prototype, {
  setup() {
    super.setup(...arguments);
    this._sdMarkTicketViewed();
  },

  onWillLoadRoot(record) {
    super.onWillLoadRoot(...arguments);
    this._sdMarkTicketViewed(record);
  },

  _sdMarkTicketViewed(record) {
    const root = record || this.model?.root;
    if (
      this.props.resModel !== "service.desk.ticket" ||
      !root?.resId ||
      root.isNew
    ) {
      return;
    }
    this.orm.call("service.desk.ticket", "action_mark_viewed", [[root.resId]]);
  },
});
