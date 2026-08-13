import json

from odoo import http
from odoo.http import request


class ServiceDeskWhatsappController(http.Controller):

    @http.route("/service_desk/whatsapp/webhook", type="json", auth="public", methods=["POST"], csrf=False)
    def whatsapp_webhook(self, **kwargs):
        """Generic webhook for WhatsApp Business API providers."""
        data = request.get_json_data() or {}
        phone = data.get("from") or data.get("phone") or data.get("sender")
        message = data.get("body") or data.get("text") or data.get("message", "")
        external_id = data.get("id") or data.get("message_id")
        if not phone or not message:
            return {"status": "ignored"}
        ticket = request.env["service.desk.whatsapp.message"].sudo().process_incoming(
            phone, message, external_id=external_id,
        )
        return {"status": "ok", "ticket_id": ticket.id}
