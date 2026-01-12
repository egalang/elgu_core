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
        default=lambda self: _("New")
    )

    request_type_id = fields.Many2one(
        "elgu.request.type",
        required=True,
        tracking=True,
        index=True
    )

    stage_id = fields.Many2one(
        "elgu.request.stage",
        tracking=True,
        index=True,
        group_expand="_read_group_stage_ids"
    )

    applicant_id = fields.Many2one(
        "res.partner",
        string="Applicant",
        required=True,
        tracking=True,
        index=True
    )

    # Basic citizen details snapshot (optional)
    applicant_email = fields.Char(related="applicant_id.email", readonly=True)
    applicant_phone = fields.Char(related="applicant_id.phone", readonly=True)

    submitted_on = fields.Datetime(readonly=True, tracking=True)
    reference_no_external = fields.Char(string="External Reference", help="Optional LGU legacy reference")

    # Documentary requirements per request
    document_ids = fields.One2many("elgu.request.document", "request_id", string="Documents")

    # Billing fields
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id.id,
        readonly=True
    )
    amount_total = fields.Monetary(string="Total Fees", tracking=True, default=0.0)
    invoice_id = fields.Many2one("account.move", string="Invoice", readonly=True, copy=False)
    payment_state = fields.Selection(
        related="invoice_id.payment_state",
        string="Payment Status",
        readonly=True
    )

    # Internal assignments
    assigned_user_id = fields.Many2one("res.users", string="Assigned To", tracking=True)
    department_notes = fields.Text(string="Internal Notes")

    # Generic outcomes
    decision = fields.Selection(
        [("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")],
        default="pending",
        tracking=True
    )
    decision_notes = fields.Text(string="Decision Notes")

    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        # Assign sequence for each record
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("elgu.request") or _("New")

        records = super().create(vals_list)

        # Default stage logic (after create, we can access request_type_id safely)
        for rec in records:
            if not rec.stage_id:
                stage = rec.request_type_id.default_stage_id
                if not stage and rec.request_type_id.stage_ids:
                    stage = rec.request_type_id.stage_ids.sorted(lambda s: s.sequence)[:1]
                if stage:
                    rec.stage_id = stage.id

        return records

    def action_submit(self):
        for rec in self:
            if rec.submitted_on:
                continue
            rec.submitted_on = fields.Datetime.now()

            # Optional: auto-create missing doc slots based on request type requirements
            required_reqs = rec.request_type_id.requirement_ids
            existing_reqs = rec.document_ids.mapped("requirement_id")
            missing = required_reqs - existing_reqs
            for req in missing:
                rec.env["elgu.request.document"].create({
                    "request_id": rec.id,
                    "requirement_id": req.id,
                    "is_required": req.required,
                })

    def _read_group_stage_ids(self, stages, domain, order):
        # Show all stages so kanban/statusbar can expand properly.
        return self.env["elgu.request.stage"].search([], order=order)

    def action_create_invoice(self):
        """Creates a draft invoice for the request.
        Later we’ll plug fee rules + line breakdown."""
        for rec in self:
            if rec.invoice_id:
                continue
            if rec.amount_total <= 0:
                raise ValidationError(_("Total Fees must be greater than 0 before invoicing."))

            move = self.env["account.move"].create({
                "move_type": "out_invoice",
                "partner_id": rec.applicant_id.id,
                "invoice_line_ids": [(0, 0, {
                    "name": f"{rec.request_type_id.name} - {rec.name}",
                    "quantity": 1,
                    "price_unit": rec.amount_total,
                })],
            })
            rec.invoice_id = move.id

class ElguRequestDocument(models.Model):
    _name = "elgu.request.document"
    _description = "eLGU Request Document"
    _order = "create_date desc, id desc"

    request_id = fields.Many2one("elgu.request", required=True, ondelete="cascade")
    requirement_id = fields.Many2one("elgu.requirement", required=True)
    is_required = fields.Boolean(default=True)

    attachment_id = fields.Many2one(
        "ir.attachment",
        string="File",
        help="Uploaded document attachment"
    )

    status = fields.Selection(
        [("missing", "Missing"), ("submitted", "Submitted"), ("accepted", "Accepted"), ("rejected", "Rejected")],
        default="missing",
        tracking=True
    )
    remarks = fields.Text()

    _sql_constraints = [
        ("uniq_req_requirement", "unique(request_id, requirement_id)", "Requirement already added for this request.")
    ]
