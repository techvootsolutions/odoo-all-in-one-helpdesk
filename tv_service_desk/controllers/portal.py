import base64
from odoo import _, fields, http
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import content_disposition, request

from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class ServiceDeskPortal(CustomerPortal):

    def _config_bool(self, key, default=True):
        value = request.env["ir.config_parameter"].sudo().get_param(key)
        if value is None:
            return default
        return str(value).lower() in ("1", "true", "yes")

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        user = request.env.user
        if "sd_ticket_count" in counters:
            if user.has_group("tv_service_desk.group_portal_support"):
                domain = [("partner_id", "=", partner.id)]
            else:
                domain = [("partner_id", "child_of", partner.commercial_partner_id.id)]
            values["sd_ticket_count"] = request.env["service.desk.ticket"].search_count(domain)
        return values

    @http.route(["/my/service-desk", "/my/service-desk/page/<int:page>"], type="http", auth="user", website=True)
    def portal_my_tickets(self, page=1, sortby=None, filterby=None, groupby=None, search=None, search_in='all', **kw):
        values = self._prepare_portal_layout_values()
        Ticket = request.env["service.desk.ticket"]
        partner = request.env.user.partner_id
        user = request.env.user

        # Base security domain
        if user.has_group("tv_service_desk.group_portal_support"):
            domain = [("partner_id", "=", partner.id)]
        else:
            domain = [("partner_id", "child_of", partner.commercial_partner_id.id)]

        # Sorting
        searchbar_sortings = {
            "date": {"label": _("Newest"), "order": "create_date desc"},
            "date_old": {"label": _("Oldest"), "order": "create_date asc"},
            "name": {"label": _("Reference"), "order": "name asc"},
            "update": {"label": _("Last Update"), "order": "write_date desc"},
            "stage": {"label": _("Status"), "order": "stage_id asc"},
            "priority": {"label": _("Priority"), "order": "priority_id desc"},
        }
        if not sortby:
            sortby = "date"
        order = searchbar_sortings.get(sortby, searchbar_sortings["date"])["order"]

        # Filtering (Stages)
        stages = request.env["service.desk.stage"].sudo().search([])
        searchbar_filters = {
            "all": {"label": _("All"), "domain": []}
        }
        for stage in stages:
            searchbar_filters[str(stage.id)] = {
                "label": stage.name,
                "domain": [("stage_id", "=", stage.id)]
            }
        if not filterby:
            filterby = "all"
        filter_domain = searchbar_filters.get(filterby, searchbar_filters["all"])["domain"]
        domain += filter_domain

        # Grouping
        searchbar_groupby = {
            "none": {"label": _("None"), "input": "none"},
            "status": {"label": _("Status"), "input": "status"},
            "customer": {"label": _("Customer"), "input": "customer"},
            "category": {"label": _("Category"), "input": "category"},
            "sub_category": {"label": _("Sub Category"), "input": "sub_category"},
            "subject": {"label": _("Subject"), "input": "subject"},
            "priority": {"label": _("Priority"), "input": "priority"},
            "reply_status": {"label": _("Reply Status"), "input": "reply_status"},
            "created_by": {"label": _("Created By"), "input": "created_by"},
            "ticket_type": {"label": _("Ticket Type"), "input": "ticket_type"},
        }
        if not groupby:
            groupby = "none"

        # Searching
        searchbar_inputs = {
            "all": {"label": _("Search in All"), "input": "all"},
            "name": {"label": _("Search in Ticket Number"), "input": "name"},
            "subject": {"label": _("Search in Subject"), "input": "subject"},
            "description": {"label": _("Search in Description"), "input": "description"},
        }
        if search and search_in:
            search_domain = []
            if search_in == 'all':
                search_domain = ["|", "|", ("name", "ilike", search), ("subject", "ilike", search), ("description", "ilike", search)]
            elif search_in == 'name':
                search_domain = [("name", "ilike", search)]
            elif search_in == 'subject':
                search_domain = [("subject", "ilike", search)]
            elif search_in == 'description':
                search_domain = [("description", "ilike", search)]
            domain += search_domain

        # Count & Pager
        ticket_count = Ticket.search_count(domain)
        pager = portal_pager(
            url="/my/service-desk",
            url_args={"sortby": sortby, "filterby": filterby, "groupby": groupby, "search": search, "search_in": search_in},
            total=ticket_count,
            page=page,
            step=10,
        )
        
        tickets = Ticket.search(domain, order=order, limit=10, offset=pager["offset"])
        
        # Grouped Tickets construction
        grouped_tickets = []
        if groupby and groupby != "none":
            groupby_mapping = {
                "status": "stage_id",
                "customer": "partner_id",
                "category": "category_id",
                "sub_category": "subcategory_id",
                "subject": "subject",
                "priority": "priority_id",
                "reply_status": "replied_status",
                "created_by": "create_uid",
                "ticket_type": "ticket_type_id",
            }
            groupby_labels = {
                "status": _("Status"),
                "customer": _("Customer"),
                "category": _("Category"),
                "sub_category": _("Sub Category"),
                "subject": _("Subject"),
                "priority": _("Priority"),
                "reply_status": _("Reply Status"),
                "created_by": _("Created By"),
                "ticket_type": _("Ticket Type"),
            }
            field_name = groupby_mapping.get(groupby)
            group_prefix = groupby_labels.get(groupby, "")
            
            if field_name:
                from collections import defaultdict
                groups = defaultdict(list)
                for ticket in tickets:
                    val = ticket[field_name]
                    if hasattr(val, "display_name"):
                        val_name = val.display_name if val else _("None")
                    else:
                        selection = getattr(ticket._fields[field_name], 'selection', None)
                        val_name = dict(selection).get(val, val) if selection else val
                    val_name = val_name or _("None")
                    group_name = f"{group_prefix}: {val_name}" if group_prefix else val_name
                    groups[group_name].append(ticket)
                
                for group_name, group_tickets in groups.items():
                    grouped_tickets.append({
                        "name": group_name,
                        "tickets": group_tickets,
                    })
        else:
            grouped_tickets = [{"name": "", "tickets": tickets}]

        # Create Ticket Wizard dropdown options
        categories = request.env["service.desk.category"].sudo().search([("parent_id", "=", False)])
        subcategories = request.env["service.desk.category"].sudo().search([("parent_id", "!=", False)])
        ticket_types = request.env["service.desk.ticket.type"].sudo().search([])
        priorities = request.env["service.desk.priority"].sudo().search([])
        
        if user.has_group("tv_service_desk.group_portal_manager"):
            partners = request.env["res.partner"].sudo().search([
                "|", ("id", "=", partner.commercial_partner_id.id),
                ("parent_id", "child_of", partner.commercial_partner_id.id)
            ])
        else:
            partners = request.env["res.partner"]

        category_enabled = self._config_bool("tv_service_desk.category_enabled")
        subcategory_enabled = self._config_bool("tv_service_desk.subcategory_enabled")
        customer_rating_enabled = self._config_bool("tv_service_desk.customer_rating_enabled")

        values.update({
            "tickets": tickets,
            "grouped_tickets": grouped_tickets,
            "page_name": "service_desk",
            "pager": pager,
            "default_url": "/my/service-desk",
            "searchbar_sortings": searchbar_sortings,
            "searchbar_filters": searchbar_filters,
            "searchbar_groupby": searchbar_groupby,
            "searchbar_inputs": searchbar_inputs,
            "sortby": sortby,
            "filterby": filterby,
            "groupby": groupby,
            "search": search,
            "search_in": search_in,
            "categories": categories,
            "subcategories": subcategories,
            "ticket_types": ticket_types,
            "priorities": priorities,
            "partners": partners,
            "category_enabled": category_enabled,
            "subcategory_enabled": subcategory_enabled,
            "customer_rating_enabled": customer_rating_enabled,
        })
        return request.render("tv_service_desk.portal_my_tickets", values)

    @http.route(["/my/service-desk/create"], type="http", auth="user", methods=["POST"], website=True)
    def portal_create_ticket(self, **post):
        user = request.env.user
        partner = user.partner_id
        
        if user.has_group("tv_service_desk.group_portal_support"):
            partner_id = partner.id
            person_name = partner.name
            email = partner.email
        else:
            partner_id = int(post.get("partner_id")) if post.get("partner_id") else partner.id
            selected_partner = request.env["res.partner"].browse(partner_id)
            person_name = post.get("person_name") or selected_partner.name
            email = post.get("email") or selected_partner.email

        ticket_vals = {
            "subject": post.get("subject"),
            "partner_id": partner_id,
            "person_name": person_name,
            "partner_email": email,
            "partner_phone": post.get("mobile"),
            "category_id": int(post.get("category_id")) if post.get("category_id") else False,
            "subcategory_id": int(post.get("subcategory_id")) if post.get("subcategory_id") else False,
            "description": post.get("description"),
            "ticket_type_id": int(post.get("ticket_type_id")) if post.get("ticket_type_id") else False,
            "priority_id": int(post.get("priority_id")) if post.get("priority_id") else False,
            "source": "portal",
        }
        
        limit_kb = int(request.env["ir.config_parameter"].sudo().get_param("tv_service_desk.portal_attachment_size_kb", 50))
        if request.httprequest.files.getlist("attachments"):
            for attachment in request.httprequest.files.getlist("attachments"):
                if attachment.filename:
                    attachment_data = attachment.read()
                    attachment.seek(0)
                    if len(attachment_data) > limit_kb * 1024:
                        raise UserError(_("%s exceeds the %sKB file size limit") % (attachment.filename, limit_kb))

        ticket = request.env["service.desk.ticket"].sudo().create(ticket_vals)
        ticket.message_subscribe(partner_ids=[partner.id])
        
        if request.httprequest.files.getlist("attachments"):
            attachments = request.httprequest.files.getlist("attachments")
            for attachment in attachments:
                if attachment.filename:
                    attachment_data = attachment.read()
                    attachment_rec = request.env["ir.attachment"].sudo().create({
                        "name": attachment.filename,
                        "res_model": "service.desk.ticket",
                        "res_id": ticket.id,
                        "datas": base64.b64encode(attachment_data),
                    })
                    ticket.sudo().write({
                        "attachment_ids": [(4, attachment_rec.id)]
                    })
        return request.redirect(f"/my/service-desk/{ticket.id}")

    @http.route(["/my/service-desk/<int:ticket_id>/message"], type="http", auth="user", methods=["POST"], website=True)
    def portal_ticket_message(self, ticket_id, **post):
        ticket = request.env["service.desk.ticket"].browse(ticket_id)
        try:
            ticket.check_access("read")
        except (AccessError, MissingError):
            return request.redirect("/my")
            
        body = post.get("body")
        if body:
            limit_kb = int(request.env["ir.config_parameter"].sudo().get_param("tv_service_desk.portal_attachment_size_kb", 50))
            if request.httprequest.files.getlist("attachments"):
                for attachment in request.httprequest.files.getlist("attachments"):
                    if attachment.filename:
                        attachment_data = attachment.read()
                        attachment.seek(0)
                        if len(attachment_data) > limit_kb * 1024:
                            raise UserError(_("%s exceeds the %sKB file size limit") % (attachment.filename, limit_kb))

            message_values = {
                "body": body,
                "message_type": "comment",
                "subtype_xmlid": "mail.mt_comment",
            }
            attachments = []
            if request.httprequest.files.getlist("attachments"):
                for attachment in request.httprequest.files.getlist("attachments"):
                    if attachment.filename:
                        attachment_data = attachment.read()
                        attachment_rec = request.env["ir.attachment"].sudo().create({
                            "name": attachment.filename,
                            "res_model": "service.desk.ticket",
                            "res_id": ticket.id,
                            "datas": base64.b64encode(attachment_data),
                        })
                        attachments.append(attachment_rec.id)
            if attachments:
                message_values["attachment_ids"] = [(6, 0, attachments)]
                ticket.sudo().write({
                    "attachment_ids": [(4, att_id) for att_id in attachments]
                })
            ticket.message_post(**message_values)
        return request.redirect(f"/my/service-desk/{ticket.id}")

    def _check_ticket_portal_access(self, ticket, access_token=None):
        ticket_sudo = ticket.sudo()
        if access_token and ticket_sudo.access_token and access_token == ticket_sudo.access_token:
            return ticket_sudo
        try:
            ticket.check_access("read")
            return ticket
        except (AccessError, MissingError):
            return False

    @http.route(["/download/ht/<int:ticket_id>"], type="http", auth="public", website=True)
    def download_ticket_ht(self, ticket_id, access_token=None, **kw):
        ticket = request.env["service.desk.ticket"].sudo().browse(ticket_id)
        if not ticket.exists():
            return request.not_found()
        ticket = self._check_ticket_portal_access(ticket, access_token=access_token)
        if not ticket:
            return request.not_found()
        pdf_content, _report_format = request.env["ir.actions.report"].sudo()._render_qweb_pdf(
            "tv_service_desk.action_report_service_desk_ticket",
            ticket.ids,
        )
        pdfhttpheaders = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", len(pdf_content)),
            ("Content-Disposition", content_disposition("%s.pdf" % (ticket.name or "ticket"))),
        ]
        return request.make_response(pdf_content, headers=pdfhttpheaders)

    @http.route(["/my/sh_tickets/<int:ticket_id>"], type="http", auth="public", website=True)
    def portal_sh_ticket_history(self, ticket_id, access_token=None, **kw):
        ticket = request.env["service.desk.ticket"].sudo().browse(ticket_id)
        if not ticket.exists():
            return request.not_found()
        ticket = self._check_ticket_portal_access(ticket, access_token=access_token)
        if not ticket:
            return request.not_found()
        if request.env.user.has_group("base.group_portal") and not request.env.user._is_public():
            ticket.sudo()._notify_customer_portal_view()
        values = self._prepare_portal_layout_values()
        values.update({
            "ticket": ticket,
            "customer_rating_enabled": self._config_bool("tv_service_desk.customer_rating_enabled"),
        })
        return request.render("tv_service_desk.portal_ticket_detail", values)

    @http.route(["/my/service-desk/<int:ticket_id>"], type="http", auth="user", website=True)
    def portal_ticket_detail(self, ticket_id, **kw):
        ticket = request.env["service.desk.ticket"].browse(ticket_id)
        try:
            ticket.check_access("read")
        except (AccessError, MissingError):
            return request.redirect("/my")
        if request.env.user.has_group("base.group_portal"):
            ticket.sudo()._notify_customer_portal_view()
        values = self._prepare_portal_layout_values()
        values.update({
            "ticket": ticket,
            "customer_rating_enabled": self._config_bool("tv_service_desk.customer_rating_enabled"),
        })
        return request.render("tv_service_desk.portal_ticket_detail", values)

    def _is_customer_rating_enabled(self):
        return self._config_bool("tv_service_desk.customer_rating_enabled")

    @http.route(["/my/service-desk/<int:ticket_id>/feedback"], type="http", auth="public", website=True)
    def portal_ticket_feedback(self, ticket_id, access_token=None, **kw):
        if not self._is_customer_rating_enabled():
            return request.not_found()
        ticket = request.env["service.desk.ticket"].browse(ticket_id)
        if not ticket.exists():
            return request.not_found()
        ticket_access = self._check_ticket_portal_access(ticket, access_token=access_token)
        if not ticket_access:
            return request.not_found()
        values = {"ticket": ticket_access, "token": access_token}
        return request.render("tv_service_desk.portal_ticket_feedback", values)

    @http.route(["/my/service-desk/<int:ticket_id>/submit-feedback"], type="http", auth="public", methods=["POST"], website=True)
    def portal_submit_feedback(self, ticket_id, **post):
        if not self._is_customer_rating_enabled():
            return request.not_found()
        ticket = request.env["service.desk.ticket"].browse(ticket_id)
        if not ticket.exists():
            return request.not_found()
        access_token = post.get("access_token")
        ticket_access = self._check_ticket_portal_access(ticket, access_token=access_token)
        if not ticket_access:
            return request.not_found()
        rating_val = post.get("rating", "0")
        if rating_val and rating_val != "0":
            request.env["service.desk.ticket.rating"].sudo().create({
                "ticket_id": ticket_access.id,
                "partner_id": ticket_access.partner_id.id,
                "user_id": ticket_access.user_id.id,
                "team_id": ticket_access.team_id.id,
                "rating": rating_val,
                "comment": post.get("comment"),
            })
        return request.render("tv_service_desk.portal_ticket_feedback_thanks", {"ticket": ticket_access})

    @http.route(["/helpdesk/knowledge", "/helpdesk/knowledge/page/<int:page>"], type="http", auth="public", website=True)
    def portal_knowledge(self, page=1, search=None, category_id=None, **kw):
        Article = request.env["service.desk.knowledge.article"].sudo()
        domain = [("is_published", "=", True)]
        if search:
            domain += ["|", ("name", "ilike", search), ("content", "ilike", search)]
        if category_id:
            domain.append(("category_id", "=", int(category_id)))
        article_count = Article.search_count(domain)
        pager = portal_pager(url="/helpdesk/knowledge", total=article_count, page=page, step=12)
        articles = Article.search(domain, limit=12, offset=pager["offset"], order="sequence, name")
        categories = request.env["service.desk.knowledge.category"].sudo().search([("active", "=", True)])
        return request.render("tv_service_desk.portal_knowledge", {
            "articles": articles,
            "categories": categories,
            "pager": pager,
            "search": search or "",
            "category_id": int(category_id) if category_id else False,
        })

    @http.route(["/helpdesk/knowledge/<int:article_id>"], type="http", auth="public", website=True)
    def portal_knowledge_article(self, article_id, **kw):
        article = request.env["service.desk.knowledge.article"].sudo().browse(article_id)
        if not article.exists() or not article.is_published:
            return request.not_found()
        article.action_increment_view()
        return request.render("tv_service_desk.portal_knowledge_article", {"article": article})
