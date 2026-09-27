from odoo import api, fields, models


class AtsShareDashboard(models.TransientModel):
    _name = 'ats.share.dashboard'
    _description = 'Share Management Dashboard'

    name = fields.Char(
        string='Dashboard',
        default='Share Management Dashboard',
        readonly=True,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        readonly=True,
    )

    total_shares_available = fields.Integer(
        string='Total Shares Available',
        readonly=True,
    )

    shares_sold = fields.Integer(
        string='Shares Sold',
        readonly=True,
    )

    shares_remaining = fields.Integer(
        string='Shares Remaining',
        readonly=True,
    )

    top_shareholder_ids = fields.One2many(
        'ats.share.dashboard.line',
        'dashboard_id',
        string='Top 10 Shareholders',
        readonly=True,
    )

    @api.model
    def action_open_dashboard(self):
        company = self.env.company

        total_shares_available = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'ats_share_management.total_shares_available',
                default='0',
            )
        )

        Transaction = self.env['ats.share.transaction']

        purchase_transactions = Transaction.search([
            ('company_id', '=', company.id),
            ('transaction_type', '=', 'purchase'),
            ('state', '=', 'completed'),
        ])

        shares_sold = sum(
            purchase_transactions.mapped('quantity')
        )

        shares_remaining = max(
            total_shares_available - shares_sold,
            0,
        )

        shareholders = self.env['ats.shareholder'].search(
            [
                ('company_id', '=', company.id),
                ('active', '=', True),
                ('total_shares_owned', '>', 0),
            ],
            order='total_shares_owned desc, name asc',
            limit=10,
        )

        dashboard = self.create({
            'name': 'Share Management Dashboard',
            'company_id': company.id,
            'total_shares_available': total_shares_available,
            'shares_sold': shares_sold,
            'shares_remaining': shares_remaining,
        })

        line_vals = []

        for rank, shareholder in enumerate(
            shareholders,
            start=1,
        ):
            ownership_percentage = 0.0

            if shares_sold:
                ownership_percentage = (
                    shareholder.total_shares_owned
                    / shares_sold
                ) * 100.0

            line_vals.append({
                'dashboard_id': dashboard.id,
                'rank': rank,
                'shareholder_id': shareholder.id,
                'shares_owned': shareholder.total_shares_owned,
                'ownership_percentage': ownership_percentage,
            })

        if line_vals:
            self.env['ats.share.dashboard.line'].create(
                line_vals
            )

        return {
            'type': 'ir.actions.act_window',
            'name': 'Share Management Dashboard',
            'res_model': 'ats.share.dashboard',
            'view_mode': 'form',
            'res_id': dashboard.id,
            'target': 'current',
        }


class AtsShareDashboardLine(models.TransientModel):
    _name = 'ats.share.dashboard.line'
    _description = 'Share Management Dashboard Line'
    _order = 'rank asc'

    dashboard_id = fields.Many2one(
        'ats.share.dashboard',
        string='Dashboard',
        required=True,
        ondelete='cascade',
        readonly=True,
    )

    rank = fields.Integer(
        string='Rank',
        readonly=True,
    )

    shareholder_id = fields.Many2one(
        'ats.shareholder',
        string='Shareholder',
        readonly=True,
    )

    shares_owned = fields.Integer(
        string='Shares Owned',
        readonly=True,
    )

    ownership_percentage = fields.Float(
        string='Ownership %',
        digits=(16, 2),
        readonly=True,
    )
