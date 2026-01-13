# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ElguRequest(models.Model):
    _name = "elgu.request"
    _description = "eLGU Service Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(
        string="Request No.",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
        tracking=True,
    )

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    request_type_id = fields.Many2one(
        "elgu.request.type",
        string="Request Type",
        required=True,
        tracking=True,
        index=True,
    )

    stage_id = fields.Many2one(
        "elgu.request.stage",
        string="Stage",
        tracking=True,
        index=True,
        group_expand="_read_group_stage_ids",
    )

    applicant_id = fields.Many2one(
        "res.partner",
        string="Applicant",
        required=True,
        tracking=True,
        index=True,
    )

    applicant_email = fields.Char(related="applicant_id.email", readonly=True)
    applicant_phone = fields.Char(related="applicant_id.phone", readonly=True)

    submitted_on = fields.Datetime(readonly=True, tracking=True)
    reference_no_external = fields.Char(
        string="External Reference",
        help="Optional LGU legacy reference",
        tracking=True,
    )

    document_ids = fields.One2many(
        "elgu.request.document",
        "request_id",
        string="Documents",
        copy=False,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        readonly=True,
    )
    amount_total = fields.Monetary(
        string="Total Fees",
        currency_field="currency_id",
        tracking=True,
        default=0.0,
    )

    invoice_id = fields.Many2one(
        "account.move",
        string="Invoice",
        readonly=True,
        copy=False,
        tracking=True,
    )
    payment_state = fields.Selection(
        related="invoice_id.payment_state",
        string="Payment Status",
        readonly=True,
    )

    is_paid = fields.Boolean(
        string="Paid",
        compute="_compute_is_paid",
        store=False,
    )

    assigned_user_id = fields.Many2one(
        "res.users",
        string="Assigned To",
        tracking=True,
    )
    department_notes = fields.Text(string="Internal Notes")

    decision = fields.Selection(
        [("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")],
        default="pending",
        tracking=True,
    )
    decision_notes = fields.Text(string="Decision Notes")

    active = fields.Boolean(default=True)

    released_attachment_id = fields.Many2one(
        "ir.attachment",
        string="Released Document",
        help="Final released document for the citizen to download (e.g., Permit/Certificate PDF).",
        tracking=True,
    )
    released_date = fields.Datetime(string="Released On", tracking=True)

    all_required_docs_accepted = fields.Boolean(
        string="All Required Docs Accepted",
        compute="_compute_all_required_docs_accepted",
        store=False,
    )

    can_download_released = fields.Boolean(
        string="Can Download Released Document",
        compute="_compute_can_download_released",
        store=False,
    )

    # ------------------------
    # COMPUTES
    # ------------------------
    @api.depends("invoice_id.payment_state")
    def _compute_is_paid(self):
        for rec in self:
            rec.is_paid = bool(rec.invoice_id and rec.invoice_id.payment_state == "paid")

    @api.depends("document_ids.is_required", "document_ids.status")
    def _compute_all_required_docs_accepted(self):
        for rec in self:
            required_docs = rec.document_ids.filtered(lambda d: d.is_required)
            rec.all_required_docs_accepted = all(
                (d.status or "missing") == "accepted" for d in required_docs
            ) if required_docs else True

    @api.depends("released_attachment_id", "invoice_id.payment_state", "all_required_docs_accepted")
    def _compute_can_download_released(self):
        for rec in self:
            paid_ok = (not rec.invoice_id) or rec.invoice_id.payment_state == "paid"
            rec.can_download_released = bool(rec.released_attachment_id and paid_ok and rec.all_required_docs_accepted)

    # ------------------------
    # CREATE / WRITE
    # ------------------------
    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = seq.next_by_code("elgu.request") or _("New")
            vals.setdefault("company_id", self.env.company.id)

        records = super().create(vals_list)

        # Default stage per request type
        for rec in records:
            if not rec.stage_id:
                stage = rec._get_default_stage()
                if stage:
                    rec.stage_id = stage.id

        records._sync_released_attachment_link()
        return records

    def write(self, vals):
        res = super().write(vals)
        if "released_attachment_id" in vals:
            self._sync_released_attachment_link()
        return res

    def _sync_released_attachment_link(self):
        """Ensure released attachment is linked to this request (res_model/res_id)."""
        for rec in self:
            att = rec.released_attachment_id
            if not att:
                continue
            if att.res_model != "elgu.request" or att.res_id != rec.id:
                att.sudo().write({"res_model": "elgu.request", "res_id": rec.id})

    # ------------------------
    # STAGES
    # ------------------------
    def _get_default_stage(self):
        self.ensure_one()
        stage = self.request_type_id.default_stage_id
        if stage:
            return stage
        stages = self.request_type_id.stage_ids.sorted(lambda s: (s.sequence, s.id))
        return stages[:1] and stages[0] or False

    def _read_group_stage_ids(self, stages, domain, order):
        # Expand kanban/statusbar: show all stages (you can later filter per request_type if desired)
        return self.env["elgu.request.stage"].search([], order=order)

    # ------------------------
    # ACTIONS
    # ------------------------
    def action_submit(self):
        for rec in self:
            if not rec.submitted_on:
                rec.submitted_on = fields.Datetime.now()

            # ensure doc slots exist based on request type requirements
            reqs = rec.request_type_id.requirement_ids
            existing = rec.document_ids.mapped("requirement_id")
            missing = reqs - existing
            for r in missing:
                self.env["elgu.request.document"].create({
                    "request_id": rec.id,
                    "requirement_id": r.id,
                    "is_required": bool(r.required),
                    "status": "missing",
                })

    def _get_income_account(self):
        """Find a usable income account for invoice lines (schema-safe)."""
        self.ensure_one()
        Account = self.env["account.account"].with_company(self.company_id)

        domain = []

        # Prefer "account_type" when available
        if "account_type" in Account._fields:
            domain.append(("account_type", "in", ("income", "income_other")))
        elif "internal_type" in Account._fields:
            # older schema fallback
            domain.append(("internal_type", "=", "other"))
        elif "user_type_id" in Account._fields:
            # last resort fallback (very broad; depends on account.account.type setup)
            pass

        # Filter out deprecated accounts only if the field exists
        if "deprecated" in Account._fields:
            domain.append(("deprecated", "=", False))

        # company_id field not always present in your build; don't filter on it.
        acc = Account.search(domain, limit=1)

        if not acc:
            raise ValidationError(
                _("No suitable income account found. Please configure Accounting / Chart of Accounts.")
            )
        return acc

    def action_create_invoice(self):
        """Create a draft customer invoice for the request."""
        Move = self.env["account.move"].with_company(self.company_id)
        for rec in self:
            if rec.invoice_id:
                continue
            if rec.amount_total <= 0:
                raise ValidationError(_("Total Fees must be greater than 0 before invoicing."))

            income_account = rec._get_income_account()

            move = Move.create({
                "move_type": "out_invoice",
                "partner_id": rec.applicant_id.id,
                "invoice_origin": rec.name,
                "invoice_line_ids": [(0, 0, {
                    "name": "%s - %s" % (rec.request_type_id.name, rec.name),
                    "quantity": 1.0,
                    "price_unit": rec.amount_total,
                    "account_id": income_account.id,
                })],
            })
            rec.invoice_id = move.id


class ElguRequestDocument(models.Model):
    _name = "elgu.request.document"
    _description = "eLGU Request Document"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    request_id = fields.Many2one(
        "elgu.request",
        required=True,
        ondelete="cascade",
        index=True,
    )
    requirement_id = fields.Many2one(
        "elgu.requirement",
        required=True,
        index=True,
    )
    is_required = fields.Boolean(default=True)

    attachment_id = fields.Many2one(
        "ir.attachment",
        string="File",
        help="Uploaded document attachment",
    )

    status = fields.Selection(
        [
            ("missing", "Missing"),
            ("submitted", "Submitted"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
        ],
        default="missing",
        tracking=True,
    )
    remarks = fields.Text()

    _sql_constraints = [
        ("uniq_req_requirement", "unique(request_id, requirement_id)", "Requirement already added for this request."),
    ]
