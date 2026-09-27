# ATS Share Management

> A professional Odoo 17 module for managing shareholders, share ownership, purchases, transfers, transactions, certificates, and reporting.

ATS Share Management is an Odoo 17 business management module developed by **Ashewa Technology Solution S.C.** It provides a structured workflow for managing shareholding activities and maintaining a reliable history of share transactions.

---

## Features

### Shareholder Management

- Register individual shareholders
- Register corporate shareholders
- Unique shareholder registration numbers
- Automatic shareholder identification
- Shareholder status management
- Registration date tracking
- Contact and company information
- Shareholder ownership tracking

### Share Purchase Management

- Create share purchase records
- Validate share quantities
- Validate share prices
- Track purchase transactions
- Transaction state management
- Automatic transaction numbering
- Completed transaction protection

### Share Transfers

- Transfer shares between shareholders
- Validate available ownership before transfer
- Prevent invalid transfer quantities
- Prevent transfers to the same shareholder
- Track transfer history
- Maintain transaction records for ownership changes

### Ownership Management

The module calculates shareholder ownership based on completed share transactions.

Ownership information can be used to review:

- Total shares held
- Share ownership history
- Purchases
- Transfers
- Reversals
- Current ownership position

### Transaction Management

All major share activities are recorded as transactions.

The transaction system supports:

- Purchases
- Transfers
- Transaction states
- Transaction dates
- Transaction references
- Transaction history
- Transaction reversal

Completed transactions are protected from normal modification. Corrections are handled through reversal transactions rather than changing historical completed records.

### Reports and Certificates

The module provides reporting functionality for:

- Shareholder Register
- Share Certificates
- Ownership Reports

### Security and Access Control

The module includes:

- Security groups
- Model access permissions
- Record rules
- Permission checks for sensitive operations
- Restrictions on protected transaction records

### Automated Testing

The module includes automated tests covering major business workflows, including:

- Shareholder creation
- Duplicate registration validation
- Purchase workflows
- Purchase validation
- Transfer workflows
- Transfer validation
- Ownership calculations
- Transaction protection
- Transaction reversal
- Access control

---

## Module Architecture

```text
ats_share_management/
├── data/
│   ├── demo_data.xml
│   ├── purchase_sequence.xml
│   ├── shareholder_sequence.xml
│   ├── transaction_sequence.xml
│   └── transfer_sequence.xml
│
├── models/
│   ├── purchase.py
│   ├── shareholder.py
│   ├── share_dashboard.py
│   ├── share_settings.py
│   ├── transaction.py
│   └── transfer.py
│
├── reports/
│   ├── share_certificate_report.xml
│   └── shareholder_register_report.xml
│
├── security/
│   ├── ir.model.access.csv
│   ├── security_groups.xml
│   └── share_management_rules.xml
│
├── tests/
│   ├── __init__.py
│   └── test_share_management.py
│
├── views/
│   ├── ownership_report_views.xml
│   ├── purchase_views.xml
│   ├── share_dashboard_views.xml
│   ├── share_management_menu.xml
│   ├── share_settings_views.xml
│   ├── shareholder_views.xml
│   ├── transaction_views.xml
│   └── transfer_views.xml
│
├── DATA_MODEL.md
├── README.md
├── __init__.py
└── __manifest__.py

Business Workflow

Shareholder Registration
          |
          v
   Share Purchase
          |
          v
 Completed Transaction
          |
          v
 Ownership Calculation
          |
     +----+----+
     |         |
     v         v
 Transfer   Reports
     |
     v
Transaction History

Shareholder Types

The module supports two shareholder types:

Type	Description
Individual	A natural person holding shares
Corporate	A company or other corporate entity holding shares

The shareholder type describes the nature of the shareholder.

The Odoo company_id field is separate and identifies the Odoo company associated with the record.

Transaction Integrity

A key design principle of the module is protecting completed historical transactions.

Once a transaction is completed, it should not be casually modified because changing historical transactions can affect ownership calculations and transaction history.

Corrections are handled through reversal transactions.

This approach helps maintain:

Historical integrity
Traceability
Accurate ownership calculations
Clear transaction history
Safer correction workflows
Requirements
Odoo 17.0
Python 3.10+
PostgreSQL
Odoo modules:
base
mail
Installation
Copy the ats_share_management folder into your Odoo custom addons directory.
Make sure the custom addons directory is included in odoo.conf.
Restart Odoo.
Update the Apps list.
Search for ATS Share Management.
Install the module.
Development
Update the Module

From the Odoo installation directory:

python odoo-bin -c odoo.conf -d odoo -u ats_share_management --stop-after-init
Run Automated Tests
python odoo-bin -c odoo.conf -d odoo -u ats_share_management --test-enable --stop-after-init

A successful test run reports:

0 failed, 0 error(s)
Start Odoo
python odoo-bin -c odoo.conf
Demo Data

Demo data is included for development and testing.

The demo dataset includes individual and corporate shareholders together with sample share transactions.

Completed demo transactions are protected from modification during module upgrades.

Documentation

Additional technical documentation is available in:

DATA_MODEL.md

This document provides additional information about the module's data model and relationships.

Project Status

The module has been implemented and tested for the core share-management workflows.

The automated test suite currently passes with:

0 failed, 0 error(s) of 22 tests

Test coverage includes:

Shareholder creation and validation
Duplicate registration prevention
Purchase workflows
Purchase validation
Transfer workflows
Transfer validation
Ownership calculations
Completed transaction protection
Transaction reversal
Reversal validation
Access control
License

LGPL-3

Author

Ashewa Technology Solution S.C.

