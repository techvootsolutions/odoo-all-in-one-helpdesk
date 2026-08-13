# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class ServiceDeskReminderController(http.Controller):

    @http.route("/service_desk/reminder_notify", type="jsonrpc", auth="user")
    def reminder_notify(self):
        """Poll due ticket reminder popups (same pattern as calendar /calendar/notify)."""
        return request.env["service.desk.ticket"].get_ticket_reminder_popups()
