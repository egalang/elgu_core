from odoo import api, fields, models

class ElguRequestType(models.Model):
    _name = "elgu.request.type"
    _description = "eLGU Request Type"
    _order = "sequence, name"

    name = fields.Char(required=True, index=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)

    active = fields.Boolean(default=True)

    # Workflow defaults
    default_stage_id = fields.Many2one("elgu.request.stage", string="Default Stage")
    stage_ids = fields.Many2many("elgu.request.stage", string="Allowed Stages")

    # Requirements catalog for this type
    requirement_ids = fields.Many2many("elgu.requirement", string="Document Requirements")

    # Billing configuration placeholders (we’ll expand later)
    requires_payment = fields.Boolean(default=True)
    fee_notes = fields.Text(string="Fee Notes / Policy Reference")
    fee_amount = fields.Float(string="Fee Amount")