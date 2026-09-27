from psycopg2 import IntegrityError

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestShareManagement(TransactionCase):
    """Tests for ATS Share Management."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.Shareholder = cls.env['ats.shareholder']
        cls.Purchase = cls.env['ats.share.purchase']
        cls.Transfer = cls.env['ats.share.transfer']
        cls.Transaction = cls.env['ats.share.transaction']
        cls.Settings = cls.env['res.config.settings']

        cls.company = cls.env.company

        cls.shareholder_a = cls.Shareholder.create({
            'name': 'Test Shareholder A',
            'registration_number': 'TEST-001',
            'shareholder_type': 'individual',
            'company_id': cls.company.id,
        })

        cls.shareholder_b = cls.Shareholder.create({
            'name': 'Test Shareholder B',
            'registration_number': 'TEST-002',
            'shareholder_type': 'individual',
            'company_id': cls.company.id,
        })

        cls.config = cls.env['ir.config_parameter'].sudo()

        cls.config.set_param(
            'ats_share_management.total_shares_available',
            '10000',
        )

        cls.config.set_param(
            'ats_share_management.price_per_share',
            '100',
        )

        # Create an SMS Administrator test user.
        cls.admin_group = cls.env.ref(
            'ats_share_management.group_sms_administrator'
        )

        cls.admin_user = cls.env['res.users'].with_context(
            no_reset_password=True
        ).create({
            'name': 'ATS Test Administrator',
            'login': 'ats_test_admin',
            'email': 'ats_test_admin@example.com',
            'groups_id': [(6, 0, [
                cls.admin_group.id,
            ])],
        })

        cls.admin_env = cls.env(user=cls.admin_user)

    def test_01_shareholder_creation(self):
        """A shareholder should be created correctly."""

        shareholder = self.Shareholder.create({
            'name': 'New Test Shareholder',
            'registration_number': 'TEST-003',
            'shareholder_type': 'individual',
            'company_id': self.company.id,
        })

        self.assertTrue(shareholder.id)
        self.assertTrue(shareholder.shareholder_code)
        self.assertEqual(
            shareholder.total_shares_owned,
            0,
        )

    def test_02_duplicate_registration_number(self):
        """Registration numbers must be unique."""

        with self.assertRaises(IntegrityError):
            self.Shareholder.create({
                'name': 'Duplicate Shareholder',
                'registration_number': 'TEST-001',
                'shareholder_type': 'individual',
                'company_id': self.company.id,
            })

    def test_03_purchase_workflow(self):
        """Purchase should move through the complete workflow."""

        purchase = self.Purchase.create({
            'shareholder_id': self.shareholder_a.id,
            'quantity': 100,
            'unit_price': 100,
        })

        self.assertEqual(purchase.state, 'draft')

        purchase.action_submit()
        self.assertEqual(purchase.state, 'submitted')

        purchase = purchase.with_env(self.admin_env)
        purchase.action_approve()
        self.assertEqual(purchase.state, 'approved')

        purchase.action_complete()

        self.assertEqual(purchase.state, 'completed')

        transaction = self.Transaction.search([
            ('shareholder_id', '=', self.shareholder_a.id),
            ('transaction_type', '=', 'purchase'),
            ('quantity', '=', 100),
        ], order='id desc', limit=1)

        self.assertTrue(transaction)
        self.assertEqual(transaction.state, 'completed')

        self.shareholder_a.invalidate_recordset()

        self.assertEqual(
            self.shareholder_a.total_shares_owned,
            100,
        )

    def test_04_purchase_cannot_exceed_available_shares(self):
        """A purchase cannot exceed the configured share pool."""

        self.config.set_param(
            'ats_share_management.total_shares_available',
            '10',
        )

        purchase = self.Purchase.create({
            'shareholder_id': self.shareholder_a.id,
            'quantity': 20,
            'unit_price': 100,
        })

        purchase.action_submit()

        purchase = purchase.with_env(self.admin_env)
        purchase.action_approve()

        with self.assertRaises(ValidationError):
            purchase.action_complete()

        self.assertEqual(purchase.state, 'approved')

    def test_05_purchase_quantity_must_be_positive(self):
        """Purchase quantity must be greater than zero."""

        with self.assertRaises(ValidationError):
            self.Purchase.create({
                'shareholder_id': self.shareholder_a.id,
                'quantity': 0,
                'unit_price': 100,
            })

    def test_06_purchase_price_cannot_be_negative(self):
        """Purchase price cannot be negative."""

        with self.assertRaises(ValidationError):
            self.Purchase.create({
                'shareholder_id': self.shareholder_a.id,
                'quantity': 10,
                'unit_price': -1,
            })

    def test_07_transfer_workflow(self):
        """Transfer should move shares between shareholders."""

        purchase_transaction = self.Transaction.create({
            'shareholder_id': self.shareholder_a.id,
            'transaction_type': 'purchase',
            'quantity': 100,
            'transaction_date': '2026-01-01 10:00:00',
            'state': 'completed',
        })

        self.assertTrue(purchase_transaction)

        self.shareholder_a.invalidate_recordset()

        self.assertEqual(
            self.shareholder_a.total_shares_owned,
            100,
        )

        transfer = self.Transfer.create({
            'shareholder_id': self.shareholder_a.id,
            'recipient_id': self.shareholder_b.id,
            'quantity': 40,
        })

        self.assertEqual(transfer.state, 'draft')

        transfer.action_submit()
        self.assertEqual(transfer.state, 'submitted')

        transfer = transfer.with_env(self.admin_env)
        transfer.action_approve()
        self.assertEqual(transfer.state, 'approved')

        transfer.action_complete()

        self.assertEqual(transfer.state, 'completed')

        self.shareholder_a.invalidate_recordset()
        self.shareholder_b.invalidate_recordset()

        self.assertEqual(
            self.shareholder_a.total_shares_owned,
            60,
        )

        self.assertEqual(
            self.shareholder_b.total_shares_owned,
            40,
        )

        transaction = self.Transaction.search([
            ('shareholder_id', '=', self.shareholder_a.id),
            ('recipient_id', '=', self.shareholder_b.id),
            ('transaction_type', '=', 'transfer'),
            ('quantity', '=', 40),
        ], order='id desc', limit=1)

        self.assertTrue(transaction)
        self.assertEqual(transaction.state, 'completed')

    def test_08_transfer_cannot_exceed_ownership(self):
        """A shareholder cannot transfer more shares than owned."""

        self.Transaction.create({
            'shareholder_id': self.shareholder_a.id,
            'transaction_type': 'purchase',
            'quantity': 20,
            'transaction_date': '2026-01-01 10:00:00',
            'state': 'completed',
        })

        self.shareholder_a.invalidate_recordset()

        transfer = self.Transfer.create({
            'shareholder_id': self.shareholder_a.id,
            'recipient_id': self.shareholder_b.id,
            'quantity': 50,
        })

        transfer.action_submit()

        transfer = transfer.with_env(self.admin_env)
        transfer.action_approve()

        with self.assertRaises(ValidationError):
            transfer.action_complete()

        self.assertEqual(transfer.state, 'approved')

    def test_09_transfer_same_shareholder_not_allowed(self):
        """A shareholder cannot transfer shares to itself."""

        with self.assertRaises(ValidationError):
            self.Transfer.create({
                'shareholder_id': self.shareholder_a.id,
                'recipient_id': self.shareholder_a.id,
                'quantity': 10,
            })

    def test_10_transfer_quantity_must_be_positive(self):
        """Transfer quantity must be greater than zero."""

        with self.assertRaises(ValidationError):
            self.Transfer.create({
                'shareholder_id': self.shareholder_a.id,
                'recipient_id': self.shareholder_b.id,
                'quantity': 0,
            })

    def test_11_completed_transaction_cannot_be_edited(self):
        """Completed transactions must be append-only."""

        transaction = self.Transaction.create({
            'shareholder_id': self.shareholder_a.id,
            'transaction_type': 'purchase',
            'quantity': 50,
            'state': 'completed',
        })

        with self.assertRaises(AccessError):
            transaction.write({
                'quantity': 100,
            })

    def test_12_completed_transaction_cannot_be_deleted(self):
        """Completed transactions cannot be deleted."""

        transaction = self.Transaction.create({
            'shareholder_id': self.shareholder_a.id,
            'transaction_type': 'purchase',
            'quantity': 50,
            'state': 'completed',
        })

        with self.assertRaises(AccessError):
            transaction.unlink()

    def test_13_transfer_transaction_requires_recipient(self):
        """A transfer transaction requires a recipient."""

        with self.assertRaises(ValidationError):
            self.Transaction.create({
                'shareholder_id': self.shareholder_a.id,
                'transaction_type': 'transfer',
                'quantity': 10,
                'state': 'completed',
            })

    def test_14_total_shares_cannot_be_less_than_sold(self):
        """Total configured shares cannot be below shares sold."""

        self.Transaction.create({
            'shareholder_id': self.shareholder_a.id,
            'transaction_type': 'purchase',
            'quantity': 100,
            'state': 'completed',
        })

        with self.assertRaises(ValidationError):
            self.Settings.create({
                'total_shares_available': 50,
                'price_per_share': 100,
            })

    def test_15_price_per_share_cannot_be_negative(self):
        """Price per share cannot be negative."""

        with self.assertRaises(ValidationError):
            self.Settings.create({
                'total_shares_available': 1000,
                'price_per_share': -10,
            })

    def test_16_ownership_calculation(self):
        """Ownership should reflect purchases and transfers."""

        self.Transaction.create({
            'shareholder_id': self.shareholder_a.id,
            'transaction_type': 'purchase',
            'quantity': 200,
            'state': 'completed',
        })

        self.Transaction.create({
            'shareholder_id': self.shareholder_a.id,
            'recipient_id': self.shareholder_b.id,
            'transaction_type': 'transfer',
            'quantity': 75,
            'state': 'completed',
        })

        self.shareholder_a.invalidate_recordset()
        self.shareholder_b.invalidate_recordset()

        self.assertEqual(
            self.shareholder_a.total_shares_owned,
            125,
        )

        self.assertEqual(
            self.shareholder_b.total_shares_owned,
            75,
        )

    def test_17_purchase_transaction_can_be_reversed(self):
        """A completed purchase can be reversed."""

        purchase = self.Purchase.create({
            'shareholder_id': self.shareholder_a.id,
            'quantity': 10,
            'unit_price': 100,
        })

        purchase.action_submit()

        purchase = purchase.with_env(self.admin_env)

        purchase.action_approve()
        purchase.action_complete()

        self.shareholder_a.invalidate_recordset()

        self.assertEqual(
            self.shareholder_a.total_shares_owned,
            10,
        )

        transaction = self.Transaction.search([
            ('shareholder_id', '=', self.shareholder_a.id),
            ('transaction_type', '=', 'purchase'),
            ('quantity', '=', 10),
            ('state', '=', 'completed'),
        ], order='id desc', limit=1)

        self.assertTrue(transaction)

        transaction = transaction.with_env(self.admin_env)
        transaction.action_reverse()

        transaction.invalidate_recordset()

        reversal = transaction.reversal_transaction_id

        self.assertTrue(reversal)
        self.assertEqual(
            reversal.reversed_transaction_id,
            transaction,
        )
        self.assertEqual(
            reversal.transaction_type,
            'correction',
        )
        self.assertEqual(
            reversal.correction_direction,
            'decrease',
        )
        self.assertEqual(
            reversal.quantity,
            10,
        )
        self.assertEqual(
            reversal.state,
            'completed',
        )

        self.shareholder_a.invalidate_recordset()

        self.assertEqual(
            self.shareholder_a.total_shares_owned,
            0,
        )

    def test_18_transfer_transaction_can_be_reversed(self):
        """A completed transfer can be reversed."""

        recipient = self.Shareholder.create({
            'name': 'Reversal Recipient',
            'registration_number': 'REV-REC-001',
            'shareholder_type': 'individual',
            'company_id': self.company.id,
        })

        purchase = self.Purchase.create({
            'shareholder_id': self.shareholder_a.id,
            'quantity': 20,
            'unit_price': 100,
        })

        purchase.action_submit()

        purchase = purchase.with_env(self.admin_env)

        purchase.action_approve()
        purchase.action_complete()

        transfer = self.Transfer.create({
            'shareholder_id': self.shareholder_a.id,
            'recipient_id': recipient.id,
            'quantity': 8,
        })

        transfer.action_submit()

        transfer = transfer.with_env(self.admin_env)

        transfer.action_approve()
        transfer.action_complete()

        self.shareholder_a.invalidate_recordset()
        recipient.invalidate_recordset()

        self.assertEqual(
            self.shareholder_a.total_shares_owned,
            12,
        )

        self.assertEqual(
            recipient.total_shares_owned,
            8,
        )

        transaction = self.Transaction.search([
            ('shareholder_id', '=', self.shareholder_a.id),
            ('recipient_id', '=', recipient.id),
            ('transaction_type', '=', 'transfer'),
            ('quantity', '=', 8),
            ('state', '=', 'completed'),
        ], order='id desc', limit=1)

        self.assertTrue(transaction)

        transaction = transaction.with_env(self.admin_env)
        transaction.action_reverse()

        transaction.invalidate_recordset()

        reversal = transaction.reversal_transaction_id

        self.assertTrue(reversal)
        self.assertEqual(
            reversal.reversed_transaction_id,
            transaction,
        )
        self.assertEqual(
            reversal.transaction_type,
            'transfer',
        )
        self.assertEqual(
            reversal.shareholder_id,
            recipient,
        )
        self.assertEqual(
            reversal.recipient_id,
            self.shareholder_a,
        )
        self.assertEqual(
            reversal.quantity,
            8,
        )
        self.assertEqual(
            reversal.state,
            'completed',
        )

        self.shareholder_a.invalidate_recordset()
        recipient.invalidate_recordset()

        self.assertEqual(
            self.shareholder_a.total_shares_owned,
            20,
        )

        self.assertEqual(
            recipient.total_shares_owned,
            0,
        )

    def test_19_transaction_cannot_be_reversed_twice(self):
        """A transaction cannot be reversed more than once."""

        purchase = self.Purchase.create({
            'shareholder_id': self.shareholder_a.id,
            'quantity': 5,
            'unit_price': 100,
        })

        purchase.action_submit()

        purchase = purchase.with_env(self.admin_env)

        purchase.action_approve()
        purchase.action_complete()

        transaction = self.Transaction.search([
            ('shareholder_id', '=', self.shareholder_a.id),
            ('transaction_type', '=', 'purchase'),
            ('quantity', '=', 5),
            ('state', '=', 'completed'),
        ], order='id desc', limit=1)

        self.assertTrue(transaction)

        transaction = transaction.with_env(self.admin_env)

        transaction.action_reverse()

        with self.assertRaises(ValidationError):
            transaction.action_reverse()

    def test_20_completed_reversal_cannot_be_edited(self):
        """A completed reversal remains immutable."""

        purchase = self.Purchase.create({
            'shareholder_id': self.shareholder_a.id,
            'quantity': 5,
            'unit_price': 100,
        })

        purchase.action_submit()

        purchase = purchase.with_env(self.admin_env)

        purchase.action_approve()
        purchase.action_complete()

        transaction = self.Transaction.search([
            ('shareholder_id', '=', self.shareholder_a.id),
            ('transaction_type', '=', 'purchase'),
            ('quantity', '=', 5),
            ('state', '=', 'completed'),
        ], order='id desc', limit=1)

        transaction = transaction.with_env(self.admin_env)
        transaction.action_reverse()

        reversal = transaction.reversal_transaction_id

        with self.assertRaises(AccessError):
            reversal.write({
                'quantity': 3,
            })

    def test_21_reversal_cannot_make_ownership_negative(self):
        """A purchase reversal cannot reduce ownership below zero."""

        purchase = self.Purchase.create({
            'shareholder_id': self.shareholder_a.id,
            'quantity': 10,
            'unit_price': 100,
        })

        purchase.action_submit()

        purchase = purchase.with_env(self.admin_env)

        purchase.action_approve()
        purchase.action_complete()

        transaction = self.Transaction.search([
            ('shareholder_id', '=', self.shareholder_a.id),
            ('transaction_type', '=', 'purchase'),
            ('quantity', '=', 10),
            ('state', '=', 'completed'),
        ], order='id desc', limit=1)

        recipient = self.Shareholder.create({
            'name': 'Ownership Test Recipient',
            'registration_number': 'REV-REC-002',
            'shareholder_type': 'individual',
            'company_id': self.company.id,
        })

        transfer = self.Transfer.create({
            'shareholder_id': self.shareholder_a.id,
            'recipient_id': recipient.id,
            'quantity': 6,
        })

        transfer.action_submit()

        transfer = transfer.with_env(self.admin_env)

        transfer.action_approve()
        transfer.action_complete()

        self.shareholder_a.invalidate_recordset()

        self.assertEqual(
            self.shareholder_a.total_shares_owned,
            4,
        )

        transaction = transaction.with_env(self.admin_env)

        with self.assertRaises(ValidationError):
            transaction.action_reverse()

        transaction.invalidate_recordset()

        self.assertFalse(
            transaction.reversal_transaction_id,
        )

    def test_22_non_admin_cannot_reverse_transaction(self):
        """Only SMS Administrators can reverse transactions."""

        purchase = self.Purchase.create({
            'shareholder_id': self.shareholder_a.id,
            'quantity': 5,
            'unit_price': 100,
        })

        purchase.action_submit()

        purchase = purchase.with_env(self.admin_env)

        purchase.action_approve()
        purchase.action_complete()

        transaction = self.Transaction.search([
            ('shareholder_id', '=', self.shareholder_a.id),
            ('transaction_type', '=', 'purchase'),
            ('quantity', '=', 5),
            ('state', '=', 'completed'),
        ], order='id desc', limit=1)

        officer_group = self.env.ref(
            'ats_share_management.group_sms_officer'
        )

        officer = self.env['res.users'].with_context(
            no_reset_password=True
        ).create({
            'name': 'ATS Test Officer',
            'login': 'ats_test_officer',
            'email': 'ats_test_officer@example.com',
            'groups_id': [(6, 0, [
                officer_group.id,
            ])],
        })

        transaction_as_officer = transaction.with_user(officer)

        with self.assertRaises(AccessError):
            transaction_as_officer.action_reverse()
