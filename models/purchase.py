from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


class AtsSharePurchase(models.Model):
    _name = 'ats.share.purchase'
    _description = 'Share Purchase'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'purchase_date desc, id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New',
        tracking=True,
    )

    shareholder_id = fields.Many2one(
        comodel_name='ats.shareholder',
        string='Shareholder',
        required=True,
        ondelete='restrict',
        tracking=True,
    )

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        related='shareholder_id.company_id',
        store=True,
        readonly=True,
        index=True,
    )

    quantity = fields.Integer(
        string='Quantity',
        required=True,
        tracking=True,
    )

    unit_price = fields.Float(
        string='Price per Share',
        digits=(16, 2),
        required=True,
        readonly=True,
        default=lambda self: float(
            self.env['ir.config_parameter'].sudo().get_param(
                'ats_share_management.price_per_share',
                default=0,
            )
        ),
        tracking=True,
    )

    total_amount = fields.Float(
        string='Total Amount',
        compute='_compute_total_amount',
        store=True,
        digits=(16, 2),
    )

    purchase_date = fields.Datetime(
        string='Purchase Date',
        default=fields.Datetime.now,
        required=True,
        tracking=True,
    )

    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
    )

    notes = fields.Text(
        string='Notes',
    )

    @api.depends('quantity', 'unit_price')
    def _compute_total_amount(self):
        for purchase in self:
            purchase.total_amount = (
                purchase.quantity * purchase.unit_price
            )

    @api.constrains('quantity')
    def _check_quantity(self):
        for purchase in self:
            if purchase.quantity <= 0:
                raise ValidationError(
                    'Purchase quantity must be greater than zero.'
                )

    @api.constrains('unit_price')
    def _check_unit_price(self):
        for purchase in self:
            if purchase.unit_price < 0:
                raise ValidationError(
                    'Price per Share cannot be negative.'
                )

    @api.model_create_multi
    def create(self, vals_list):
        config = self.env['ir.config_parameter'].sudo()

        configured_price = float(
            config.get_param(
                'ats_share_management.price_per_share',
                default=0,
            )
        )

        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code(
                        'ats.share.purchase'
                    ) or 'New'
                )

            if 'unit_price' not in vals:
                vals['unit_price'] = configured_price

        return super().create(vals_list)

    def write(self, vals):
        if 'unit_price' in vals:
            raise ValidationError(
                'The Price per Share is controlled by Share Management '
                'Settings and cannot be changed on a purchase.'
            )

        if not self.env.user.has_group(
            'ats_share_management.group_sms_administrator'
        ):
            for purchase in self:
                if purchase.state != 'draft':
                    raise AccessError(
                        'Only Draft purchases can be edited by an Officer.'
                    )

        return super().write(vals)

    def unlink(self):
        if not self.env.user.has_group(
            'ats_share_management.group_sms_administrator'
        ):
            raise AccessError(
                'Only SMS Administrators can delete purchases.'
            )

        for purchase in self:
            if purchase.state == 'completed':
                raise AccessError(
                    'Completed purchases cannot be deleted.'
                )

        return super().unlink()

    def action_submit(self):
        for purchase in self:
            if purchase.state != 'draft':
                raise ValidationError(
                    'Only Draft purchases can be submitted.'
                )

            purchase.state = 'submitted'

        return True

    def action_approve(self):
        if not self.env.user.has_group(
            'ats_share_management.group_sms_administrator'
        ):
            raise AccessError(
                'Only SMS Administrators can approve purchases.'
            )

        for purchase in self:
            if purchase.state != 'submitted':
                raise ValidationError(
                    'Only Submitted purchases can be approved.'
                )

            purchase.state = 'approved'

        return True

    def action_complete(self):
        if not self.env.user.has_group(
            'ats_share_management.group_sms_administrator'
        ):
            raise AccessError(
                'Only SMS Administrators can complete purchases.'
            )

        Transaction = self.env['ats.share.transaction']
        config = self.env['ir.config_parameter'].sudo()

        for purchase in self:

            if purchase.state != 'approved':
                raise ValidationError(
                    'Only Approved purchases can be completed.'
                )

            total_shares = int(
                config.get_param(
                    'ats_share_management.total_shares_available',
                    default=0,
                )
            )

            sold_shares = sum(
                Transaction.search([
                    ('transaction_type', '=', 'purchase'),
                    ('state', '=', 'completed'),
                    ('company_id', '=', purchase.company_id.id),
                ]).mapped('quantity')
            )

            remaining_shares = total_shares - sold_shares

            if purchase.quantity > remaining_shares:
                raise ValidationError(
                    'There are not enough shares available for this '
                    'purchase. '
                    f'Remaining shares: {remaining_shares}, '
                    f'Requested: {purchase.quantity}.'
                )

            Transaction.create({
                'shareholder_id': purchase.shareholder_id.id,
                'transaction_type': 'purchase',
                'quantity': purchase.quantity,
                'transaction_date': purchase.purchase_date,
                'state': 'completed',
                'notes': f'Created from Purchase {purchase.name}',
            })

            purchase.state = 'completed'

        return True

    def action_cancel(self):
        for purchase in self:

            if purchase.state == 'completed':
                raise ValidationError(
                    'Completed purchases cannot be cancelled.'
                )

            if purchase.state == 'cancelled':
                raise ValidationError(
                    'This purchase is already cancelled.'
                )

            if purchase.state == 'draft':
                purchase.state = 'cancelled'
                continue

            if purchase.state in ('submitted', 'approved'):
                if not self.env.user.has_group(
                    'ats_share_management.group_sms_administrator'
                ):
                    raise AccessError(
                        'Only SMS Administrators can cancel '
                        'submitted or approved purchases.'
                    )

                purchase.state = 'cancelled'

        return True
