from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    total_shares_available = fields.Integer(
        string='Total Shares Available',
        config_parameter='ats_share_management.total_shares_available',
        default=0,
    )

    price_per_share = fields.Float(
        string='Price per Share',
        digits=(16, 2),
        config_parameter='ats_share_management.price_per_share',
        default=0.0,
    )

    shares_sold = fields.Integer(
        string='Shares Sold',
        compute='_compute_share_statistics',
    )

    shares_remaining = fields.Integer(
        string='Shares Remaining',
        compute='_compute_share_statistics',
    )

    @api.depends('total_shares_available')
    def _compute_share_statistics(self):
        Transaction = self.env['ats.share.transaction']

        for settings in self:
            purchases = Transaction.search([
                ('transaction_type', '=', 'purchase'),
                ('state', '=', 'completed'),
            ])

            sold = sum(purchases.mapped('quantity'))

            settings.shares_sold = sold
            settings.shares_remaining = (
                settings.total_shares_available - sold
            )

    @api.constrains('total_shares_available')
    def _check_total_shares_available(self):
        Transaction = self.env['ats.share.transaction']

        for settings in self:
            purchases = Transaction.search([
                ('transaction_type', '=', 'purchase'),
                ('state', '=', 'completed'),
            ])

            shares_sold = sum(purchases.mapped('quantity'))

            if settings.total_shares_available < shares_sold:
                raise ValidationError(
                    'Total Shares Available cannot be less than '
                    f'the number of shares already sold ({shares_sold}).'
                )

    @api.constrains('price_per_share')
    def _check_price_per_share(self):
        for settings in self:
            if settings.price_per_share < 0:
                raise ValidationError(
                    'Price per Share cannot be negative.'
                )
