from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


class AtsShareTransaction(models.Model):
    _name = 'ats.share.transaction'
    _description = 'Share Transaction'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'transaction_date desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New',
        tracking=True,
    )

    shareholder_id = fields.Many2one(
        'ats.shareholder',
        string='Shareholder',
        required=True,
        ondelete='restrict',
        tracking=True,
    )

    recipient_id = fields.Many2one(
        'ats.shareholder',
        string='Recipient',
        ondelete='restrict',
        tracking=True,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='shareholder_id.company_id',
        store=True,
        readonly=True,
    )

    transaction_type = fields.Selection(
        [
            ('purchase', 'Purchase'),
            ('transfer', 'Transfer'),
            ('correction', 'Correction'),
        ],
        string='Transaction Type',
        required=True,
        tracking=True,
    )

    correction_direction = fields.Selection(
        [
            ('increase', 'Increase'),
            ('decrease', 'Decrease'),
        ],
        string='Correction Direction',
        tracking=True,
    )

    quantity = fields.Integer(
        string='Quantity',
        required=True,
        tracking=True,
    )

    transaction_date = fields.Datetime(
        string='Transaction Date',
        required=True,
        default=fields.Datetime.now,
        tracking=True,
    )

    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
    )

    running_total = fields.Integer(
        string='Running Total',
        compute='_compute_running_total',
    )

    reversed_transaction_id = fields.Many2one(
        'ats.share.transaction',
        string='Reversed Transaction',
        readonly=True,
        copy=False,
    )

    reversal_transaction_id = fields.Many2one(
        'ats.share.transaction',
        string='Reversal Transaction',
        readonly=True,
        copy=False,
    )

    notes = fields.Text(
        string='Notes',
    )

    @api.depends(
        'shareholder_id',
        'transaction_date',
        'quantity',
        'state',
        'transaction_type',
        'correction_direction',
    )
    def _compute_running_total(self):
        Transaction = self.env['ats.share.transaction']

        for transaction in self:
            if not transaction.shareholder_id:
                transaction.running_total = 0
                continue

            transactions = Transaction.search([
                (
                    'shareholder_id',
                    '=',
                    transaction.shareholder_id.id,
                ),
                ('state', '=', 'completed'),
                (
                    'transaction_date',
                    '<=',
                    transaction.transaction_date,
                ),
                ('id', '<=', transaction.id),
            ], order='transaction_date asc, id asc')

            total = 0

            for item in transactions:
                if item.transaction_type == 'purchase':
                    total += item.quantity

                elif item.transaction_type == 'transfer':
                    total -= item.quantity

                elif item.transaction_type == 'correction':
                    if item.correction_direction == 'increase':
                        total += item.quantity
                    elif item.correction_direction == 'decrease':
                        total -= item.quantity

            transaction.running_total = total

    @api.constrains('quantity')
    def _check_quantity(self):
        for transaction in self:
            if transaction.quantity <= 0:
                raise ValidationError(
                    'Transaction quantity must be greater than zero.'
                )

    @api.constrains(
        'transaction_type',
        'correction_direction',
        'recipient_id',
        'shareholder_id',
    )
    def _check_transaction_values(self):
        for transaction in self:
            if (
                transaction.transaction_type == 'correction'
                and not transaction.correction_direction
            ):
                raise ValidationError(
                    'Correction direction is required for corrections.'
                )

            if (
                transaction.transaction_type != 'correction'
                and transaction.correction_direction
            ):
                raise ValidationError(
                    'Correction direction is only allowed for corrections.'
                )

            if transaction.transaction_type == 'transfer':
                if not transaction.recipient_id:
                    raise ValidationError(
                        'A transfer must have a recipient.'
                    )

                if transaction.shareholder_id == transaction.recipient_id:
                    raise ValidationError(
                        'A shareholder cannot transfer shares to itself.'
                    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code(
                        'ats.share.transaction'
                    ) or 'New'
                )

        return super().create(vals_list)

    def write(self, vals):
        for transaction in self:
            if transaction.state == 'completed':
                if (
                    self.env.context.get('allow_reversal_link')
                    and set(vals.keys()) == {'reversal_transaction_id'}
                ):
                    continue

                raise AccessError(
                    'Completed transactions cannot be edited. '
                    'Create a corrective transaction instead.'
                )

        return super().write(vals)

    def unlink(self):
        for transaction in self:
            if transaction.state == 'completed':
                raise AccessError(
                    'Completed transactions cannot be deleted. '
                    'Create a corrective transaction instead.'
                )

        return super().unlink()

    def _refresh_ownership_report(self):
        companies = self.mapped('company_id')

        if not companies:
            return

        shareholders = self.env['ats.shareholder'].search([
            ('company_id', 'in', companies.ids),
        ])

        shareholders._compute_ownership_report()

    def action_complete(self):
        for transaction in self:
            if transaction.state != 'draft':
                continue

            if transaction.transaction_type == 'transfer':
                ownership = transaction.shareholder_id.share_count

                if transaction.quantity > ownership:
                    raise ValidationError(
                        'The shareholder does not own enough shares '
                        'for this transfer.'
                    )

            elif (
                transaction.transaction_type == 'correction'
                and transaction.correction_direction == 'decrease'
            ):
                ownership = transaction.shareholder_id.share_count

                if transaction.quantity > ownership:
                    raise ValidationError(
                        'The shareholder does not own enough shares '
                        'for this correction.'
                    )

            transaction.state = 'completed'

        self._refresh_ownership_report()

        return True

    def action_cancel(self):
        for transaction in self:
            if transaction.state == 'draft':
                transaction.state = 'cancelled'

        return True

    def action_reset_to_draft(self):
        for transaction in self:
            if transaction.state == 'cancelled':
                transaction.state = 'draft'

        return True

    def action_reverse(self):
        if not self.env.user.has_group(
            'ats_share_management.group_sms_administrator'
        ):
            raise AccessError(
                'Only SMS Administrators can reverse transactions.'
            )

        for transaction in self:
            if transaction.state != 'completed':
                raise ValidationError(
                    'Only completed transactions can be reversed.'
                )

            if transaction.reversal_transaction_id:
                raise ValidationError(
                    'This transaction has already been reversed.'
                )

            vals = {
                'transaction_date': fields.Datetime.now(),
                'state': 'draft',
                'reversed_transaction_id': transaction.id,
                'notes': (
                    f'Reversal of Transaction {transaction.name}'
                ),
            }

            if transaction.transaction_type == 'purchase':
                vals.update({
                    'shareholder_id': transaction.shareholder_id.id,
                    'transaction_type': 'correction',
                    'correction_direction': 'decrease',
                    'quantity': transaction.quantity,
                })

            elif transaction.transaction_type == 'transfer':
                vals.update({
                    'shareholder_id': transaction.recipient_id.id,
                    'recipient_id': transaction.shareholder_id.id,
                    'transaction_type': 'transfer',
                    'quantity': transaction.quantity,
                })

            elif transaction.transaction_type == 'correction':
                vals.update({
                    'shareholder_id': transaction.shareholder_id.id,
                    'transaction_type': 'correction',
                    'correction_direction': (
                        'decrease'
                        if transaction.correction_direction == 'increase'
                        else 'increase'
                    ),
                    'quantity': transaction.quantity,
                })

            reversal = self.create(vals)

            reversal.action_complete()

            transaction.with_context(
                allow_reversal_link=True
            ).write({
                'reversal_transaction_id': reversal.id,
            })

        return True
