from odoo import fields, models

class ElguRequirement(models.Model):
    _name = "elgu.requirement"
    _description = "eLGU Documentary Requirement"
    _order = "sequence, name"

    name = fields.Char(required=True)
    code = fields.Char(index=True)
    sequence = fields.Integer(default=10)
    description = fields.Text()

    allowed_file_types = fields.Char(
        default="pdf,jpg,jpeg,png",
        help="Comma-separated list, e.g. pdf,jpg,png"
    )
    max_file_size_mb = fields.Integer(default=10)
    required = fields.Boolean(default=True)
