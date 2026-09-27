from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AtsShareholder(models.Model):
    _name = 'ats.shareholder'
    _description = 'Shareholder'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(
        string='Shareholder Name',
        required=True,
        tracking=True,
    )

    shareholder_code = fields.Char(
        string='Shareholder Code',
        readonly=True,
        copy=False,
        tracking=True,
    )

    registration_number = fields.Char(
        string='Registration Number',
        required=True,
        tracking=True,
    )

    shareholder_type = fields.Selection(
        [
            ('individual', 'Individual'),
            ('corporate', 'Corporate'),
        ],
        string='Shareholder Type',
        required=True,
        default='individual',
        tracking=True,
    )

    phone = fields.Char(
        string='Phone',
        tracking=True,
    )

    email = fields.Char(
        string='Email',
        tracking=True,
    )

    address = fields.Text(
        string='Address',
    )

    bank_name = fields.Char(
        string='Bank Name',
    )

    bank_account = fields.Char(
        string='Bank Account',
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
        tracking=True,
    )

    status = fields.Selection(
        [
            ('draft', 'Draft'),
            ('active', 'Active'),
            ('inactive', 'Inactive'),
        ],
        string='Status',
        required=True,
        default='active',
        tracking=True,
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
    )

    date_of_birth = fields.Date(
        string='Date of Birth',
    )

    gender = fields.Selection(
        [
            ('male', 'Male'),
            ('female', 'Female'),
            ('other', 'Other'),
        ],
        string='Gender',
    )

    registration_date = fields.Date(
        string='Registration Date',
        default=fields.Date.context_today,
        tracking=True,
    )

    wallet_balance = fields.Float(
        string='Wallet Balance',
        default=0.0,
        digits=(16, 2),
    )

    total_shares_owned = fields.Integer(
        string='Total Shares Owned',
        compute='_compute_total_shares_owned',
        store=True,
    )

    shares_sold = fields.Integer(
        string='Total Shares Sold',
        compute='_compute_ownership_report',
        store=True,
    )

    ownership_percentage = fields.Float(
        string='Ownership %',
        compute='_compute_ownership_report',
        store=True,
        digits=(16, 2),
    )

    transaction_ids = fields.One2many(
        'ats.share.transaction',
        'shareholder_id',
        string='Transactions',
    )

    recipient_transaction_ids = fields.One2many(
        'ats.share.transaction',
        'recipient_id',
        string='Incoming Transfers',
    )

    transaction_count = fields.Integer(
        string='Transaction Count',
        compute='_compute_transaction_count',
    )

    share_count = fields.Integer(
        string='Share Count',
        compute='_compute_share_count',
    )

    _sql_constraints = [
        (
            'registration_number_unique',
            'unique(registration_number)',
            'Registration Number must be unique.',
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('company_id'):
                vals['company_id'] = self.env.company.id

            if not vals.get('shareholder_code'):
                vals['shareholder_code'] = self.env['ir.sequence'].next_by_code(
                    'ats.shareholder'
                ) or '/'

        return super().create(vals_list)

    @api.depends(
        'transaction_ids.state',
        'transaction_ids.transaction_type',
        'transaction_ids.quantity',
        'recipient_transaction_ids.state',
        'recipient_transaction_ids.transaction_type',
        'recipient_transaction_ids.quantity',
    )
    def _compute_total_shares_owned(self):
        for shareholder in self:
            total = 0

            for transaction in shareholder.transaction_ids:
                if transaction.state != 'completed':
                    continue

                if transaction.transaction_type == 'purchase':
                    total += transaction.quantity

                elif transaction.transaction_type == 'transfer':
                    total -= transaction.quantity

                elif transaction.transaction_type == 'correction':
                    if transaction.correction_direction == 'increase':
                        total += transaction.quantity
                    elif transaction.correction_direction == 'decrease':
                        total -= transaction.quantity

            for transaction in shareholder.recipient_transaction_ids:
                if transaction.state != 'completed':
                    continue

                if transaction.transaction_type == 'transfer':
                    total += transaction.quantity

            shareholder.total_shares_owned = max(total, 0)

    @api.depends(
        'company_id',
        'total_shares_owned',
        'transaction_ids.state',
        'transaction_ids.transaction_type',
        'transaction_ids.quantity',
        'recipient_transaction_ids.state',
        'recipient_transaction_ids.transaction_type',
        'recipient_transaction_ids.quantity',
    )
    def _compute_ownership_report(self):
        Transaction = self.env['ats.share.transaction']

        for shareholder in self:
            if not shareholder.company_id:
                shareholder.shares_sold = 0
                shareholder.ownership_percentage = 0.0
                continue

            purchase_transactions = Transaction.search([
                ('company_id', '=', shareholder.company_id.id),
                ('transaction_type', '=', 'purchase'),
                ('state', '=', 'completed'),
            ])

            shares_sold = sum(
                purchase_transactions.mapped('quantity')
            )

            shareholder.shares_sold = shares_sold

            shareholder.ownership_percentage = (
                shareholder.total_shares_owned / shares_sold
            ) * 100.0 if shares_sold else 0.0

    def _compute_transaction_count(self):
        for shareholder in self:
            shareholder.transaction_count = (
                len(shareholder.transaction_ids)
                + len(shareholder.recipient_transaction_ids)
            )

    def _compute_share_count(self):
        for shareholder in self:
            shareholder.share_count = shareholder.total_shares_owned

    def action_view_transactions(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Transactions',
            'res_model': 'ats.share.transaction',
            'view_mode': 'tree,form',
            'domain': [
                '|',
                ('shareholder_id', '=', self.id),
                ('recipient_id', '=', self.id),
            ],
            'context': {
                'default_shareholder_id': self.id,
            },
        }

    def action_view_shares(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Share Transactions',
            'res_model': 'ats.share.transaction',
            'view_mode': 'tree,form',
            'domain': [
                '|',
                ('shareholder_id', '=', self.id),
                ('recipient_id', '=', self.id),
            ],
            'context': {
                'default_shareholder_id': self.id,
            },
        }

    def _refresh_ownership_report(self):
        self._compute_ownership_report()
