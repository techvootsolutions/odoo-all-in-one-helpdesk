from odoo import api, fields, models


class ServiceDeskKnowledgeCategory(models.Model):
    _name = "service.desk.knowledge.category"
    _description = "Knowledge Base Category"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company")
    description = fields.Text(translate=True)
    article_count = fields.Integer(compute="_compute_article_count")

    @api.depends("article_ids")
    def _compute_article_count(self):
        for category in self:
            category.article_count = len(category.article_ids)

    article_ids = fields.One2many("service.desk.knowledge.article", "category_id")


class ServiceDeskKnowledgeArticle(models.Model):
    _name = "service.desk.knowledge.article"
    _description = "Knowledge Base Article"
    _inherit = ["mail.thread"]
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True, tracking=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    category_id = fields.Many2one(
        "service.desk.knowledge.category",
        string="Category",
        required=True,
        ondelete="restrict",
    )
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    content = fields.Html(sanitize_attributes=False, translate=True)
    attachment_ids = fields.Many2many("ir.attachment", string="Attachments")
    is_published = fields.Boolean(string="Published on Portal", default=True)
    view_count = fields.Integer(default=0, readonly=True)
    tag_ids = fields.Many2many("service.desk.tag", string="Tags")

    def action_increment_view(self):
        self.sudo().write({"view_count": self.view_count + 1})

    @api.model
    def search_suggestions(self, query, limit=5):
        if not query:
            return self.browse()
        domain = [("is_published", "=", True), "|", ("name", "ilike", query), ("content", "ilike", query)]
        if self.env.company:
            domain += ["|", ("company_id", "=", False), ("company_id", "=", self.env.company.id)]
        return self.search(domain, limit=limit)
