from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


class AtsShareTransfer(models.Model):
    _name = 'ats.share.transfer'
    _description = 'Share Transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'transfer_date desc'

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
        string='From Shareholder',
        required=True,
        ondelete='restrict',
        tracking=True,
    )

    recipient_id = fields.Many2one(
        comodel_name='ats.shareholder',
        string='To Shareholder',
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
    )

    quantity = fields.Integer(
        string='Quantity',
        required=True,
        tracking=True,
    )

    transfer_date = fields.Datetime(
        string='Transfer Date',
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
            ('rejected', 'Rejected'),
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

    @api.constrains(
        'shareholder_id',
        'recipient_id',
        'quantity',
    )
    def _check_transfer(self):
        for transfer in self:

            if transfer.quantity <= 0:
                raise ValidationError(
                    'Transfer quantity must be greater than zero.'
                )

            if (
                transfer.shareholder_id
                and transfer.recipient_id
                and transfer.shareholder_id == transfer.recipient_id
            ):
                raise ValidationError(
                    'The recipient cannot be the same as the '
                    'source shareholder.'
                )

            if (
                transfer.shareholder_id
                and transfer.recipient_id
                and transfer.shareholder_id.company_id
                != transfer.recipient_id.company_id
            ):
                raise ValidationError(
                    'The source and recipient shareholders must '
                    'belong to the same company.'
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code(
                        'ats.share.transfer'
                    ) or 'New'
                )

        return super().create(vals_list)

    def write(self, vals):
        if not self.env.user.has_group(
            'ats_share_management.group_sms_administrator'
        ):
            for transfer in self:
                if transfer.state != 'draft':
                    raise AccessError(
                        'Only Draft transfers can be edited by an Officer.'
                    )

        return super().write(vals)

    def unlink(self):
        if not self.env.user.has_group(
            'ats_share_management.group_sms_administrator'
        ):
            raise AccessError(
                'Only SMS Administrators can delete transfers.'
            )

        return super().unlink()

    def action_submit(self):
        for transfer in self:
            if transfer.state == 'draft':
                transfer.state = 'submitted'

        return True

    def action_approve(self):
        if not self.env.user.has_group(
            'ats_share_management.group_sms_administrator'
        ):
            raise AccessError(
                'Only SMS Administrators can approve transfers.'
            )

        for transfer in self:
            if transfer.state == 'submitted':
                transfer.state = 'approved'

        return True

    def action_complete(self):
        if not self.env.user.has_group(
            'ats_share_management.group_sms_administrator'
        ):
            raise AccessError(
                'Only SMS Administrators can complete transfers.'
            )

        Transaction = self.env['ats.share.transaction']

        for transfer in self:
            if transfer.state != 'approved':
                continue

            source = transfer.shareholder_id

            if transfer.quantity > source.total_shares_owned:
                raise ValidationError(
                    f'{source.name} does not own enough shares. '
                    f'Available shares: {source.total_shares_owned}, '
                    f'Requested: {transfer.quantity}.'
                )

            Transaction.create({
                'shareholder_id': source.id,
                'recipient_id': transfer.recipient_id.id,
                'transaction_type': 'transfer',
                'quantity': transfer.quantity,
                'transaction_date': transfer.transfer_date,
                'state': 'completed',
                'notes': f'Created from Transfer {transfer.name}',
            })

            transfer.state = 'completed'

        return True

    def action_reject(self):
        if not self.env.user.has_group(
            'ats_share_management.group_sms_administrator'
        ):
            raise AccessError(
                'Only SMS Administrators can reject transfers.'
            )

        for transfer in self:
            if transfer.state == 'submitted':
                transfer.state = 'rejected'

        return True

    def action_cancel(self):
        for transfer in self:
            if transfer.state in (
                'completed',
                'rejected',
                'cancelled',
            ):
                continue

            if transfer.state in ('submitted', 'approved'):
                if not self.env.user.has_group(
                    'ats_share_management.group_sms_administrator'
                ):
                    raise AccessError(
                        'Only SMS Administrators can cancel '
                        'submitted or approved transfers.'
                    )

            transfer.state = 'cancelled'

        return True
