from odoo import api, fields, models

class ElguRequestStage(models.Model):
    _name = "elgu.request.stage"
    _description = "eLGU Request Stage"
    _order = "sequence, id"

    name = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    is_initial = fields.Boolean(default=False)
    is_closed = fields.Boolean(default=False)
    fold = fields.Boolean(string="Fold in Kanban", default=False)
    description = fields.Text()

    # Optional governance controls (future use):
    require_payment_before_enter = fields.Boolean(
        string="Requires Payment Before Entering",
        help="If enabled, request cannot be moved into this stage unless paid."
    )
