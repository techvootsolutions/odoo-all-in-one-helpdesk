import json
import re

from odoo import api, models


class ServiceDeskTicketAi(models.AbstractModel):
    _name = "service.desk.ticket.ai.mixin"
    _description = "Service Desk AI Helpers"

    @api.model
    def _ai_enabled(self):
        return self.env["ir.config_parameter"].sudo().get_param(
            "tv_service_desk.ai_enabled", "False"
        ).lower() in ("1", "true", "yes")

    @api.model
    def _ai_call_llm(self, prompt):
        """Optional OpenAI-compatible API. Returns text or None."""
        icp = self.env["ir.config_parameter"].sudo()
        api_url = icp.get_param("tv_service_desk.ai_api_url")
        api_key = icp.get_param("tv_service_desk.ai_api_key")
        if not api_url or not api_key:
            return None
        try:
            import urllib.request

            payload = json.dumps({
                "model": icp.get_param("tv_service_desk.ai_model", "gpt-4o-mini"),
                "messages": [{"role": "user", "content": prompt}],
            }).encode()
            req = urllib.request.Request(
                api_url,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer %s" % api_key,
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                return data["choices"][0]["message"]["content"]
        except Exception:
            return None

    def _ai_keyword_category(self, text):
        Category = self.env["service.desk.category"]
        rules = {
            "hardware": ["hardware", "printer", "laptop", "device", "broken"],
            "software": ["software", "app", "login", "password", "bug", "error"],
            "network": ["network", "wifi", "vpn", "connection", "internet"],
            "billing": ["billing", "invoice", "payment", "charge", "refund"],
        }
        lowered = (text or "").lower()
        for key, words in rules.items():
            if any(w in lowered for w in words):
                cat = Category.search([("name", "ilike", key)], limit=1)
                if cat:
                    return cat.id
        return False

    def _ai_keyword_priority(self, text):
        Priority = self.env["service.desk.priority"]
        lowered = (text or "").lower()
        urgent_words = ["urgent", "asap", "immediately", "critical", "down", "outage"]
        if any(w in lowered for w in urgent_words):
            return Priority.search([], order="sequence desc", limit=1).id
        return False

    def _ai_sentiment_score(self, text):
        lowered = (text or "").lower()
        negative = ["angry", "frustrated", "terrible", "unacceptable", "worst", "furious"]
        positive = ["thanks", "great", "appreciate", "excellent"]
        score = 0
        score -= sum(1 for w in negative if w in lowered)
        score += sum(1 for w in positive if w in lowered)
        if score <= -2:
            return "frustrated"
        if score >= 2:
            return "positive"
        if score < 0:
            return "concerned"
        return "neutral"

    def _ai_suggest_articles(self, text, limit=3):
        return self.env["service.desk.knowledge.article"].search_suggestions(text, limit=limit)

    def _ai_summarize_messages(self, messages):
        bodies = [m.body or "" for m in messages if m.body]
        plain = re.sub(r"<[^>]+>", " ", " ".join(bodies))
        plain = re.sub(r"\s+", " ", plain).strip()
        if len(plain) <= 280:
            return plain
        if self._ai_enabled():
            summary = self._ai_call_llm("Summarize this support conversation in 3 sentences:\n%s" % plain[:8000])
            if summary:
                return summary
        return plain[:277] + "..."

    def _ai_suggest_reply(self, ticket):
        if self._ai_enabled():
            prompt = (
                "Draft a professional support reply for ticket subject '%s'. "
                "Description: %s"
            ) % (ticket.subject, re.sub(r"<[^>]+>", "", ticket.description or "")[:2000])
            reply = self._ai_call_llm(prompt)
            if reply:
                return reply
        return (
            "Hello %s,\n\nThank you for contacting us regarding \"%s\". "
            "We are reviewing your request and will update you shortly.\n\nBest regards,\n%s"
        ) % (
            ticket.partner_id.name or "Customer",
            ticket.subject,
            ticket.company_id.name,
        )
