ATS Share Management - Data Model

1. Purpose

This document describes the data model used by the
ats_share_management Odoo 17 module.

The model design is intended to satisfy the Share Management System
requirements for shareholder management, share purchases, share
transfers, transaction history, configuration, ownership reporting, and
dashboard information.

The SRS intentionally leaves the field-by-field data model to the
implementation team. It requires the design to explain where the share
pool and price are stored, how current ownership is calculated, and how
purchases and transfers are represented.

2. Model Overview

The module uses the following main models:

Model                   Technical Name               Purpose

Shareholder             ats.shareholder            Stores shareholder
identity, contact,
bank, company, and
ownership information.

Share Purchase          ats.share.purchase         Represents a request to
purchase shares and its
approval/completion
workflow.

Share Transfer          ats.share.transfer         Represents movement of
shares from one
shareholder to another.

Share Transaction       ats.share.transaction      Provides the completed
transaction/audit
history used to
calculate ownership.

Share Settings          res.config.settings        Exposes the
configurable total
share pool and price
per share.

Share Dashboard         ats.share.dashboard        Provides dashboard
totals for the current
company.

A separate certificate model is not used. The share certificate is
generated directly from the shareholder record as a QWeb report, in
accordance with the SRS.

3. Shareholder Model

Technical model

ats.shareholder

Purpose

The shareholder model represents an individual or company that owns
shares.

It contains the shareholder's identifying information, contact details,
bank information, company, active status, and calculated current share
ownership.

Main fields

Field                   Type                    Description

name                  Char                    Shareholder name.

shareholder_code      Char                    Unique shareholder code
generated from an Odoo
sequence.

registration_number   Char                    ID or registration
number. It is protected
by a unique SQL
constraint.

shareholder_type      Selection               Identifies an
individual or company
shareholder.

phone                 Char                    Contact telephone
number.

email                 Char                    Contact email address.

address               Text                    Shareholder address.

bank_name             Char                    Bank name.

bank_account          Char                    Bank account
information.

company_id            Many2one                Company to which the
shareholder record
belongs.

status                Selection               Shareholder status.

active                Boolean                 Controls active/archive
status.

date_of_birth         Date                    Date of birth for an
individual shareholder.

gender                Selection               Gender for an
individual shareholder.

registration_date     Date                    Shareholder
registration date.

wallet_balance        Float                   Wallet balance
maintained on the
shareholder record.

Relationships

A shareholder can have:

Many purchase records through ats.share.purchase.

Many outgoing transaction records through ats.share.transaction.

Many incoming transfer transaction records through
ats.share.transaction.

Related transaction and ownership smart-button actions.

Ownership calculation

total_shares_owned is a stored computed field.

Current ownership is derived from completed transaction records rather
than being manually entered by the user. The calculation accounts for:

Completed purchases: add shares.

Outgoing transfers: subtract shares.

Incoming transfers: add shares.

Corrections: increase or decrease ownership according to the
correction direction.

The calculation is clamped so that calculated ownership does not become
negative.

This design makes the transaction history the source of truth for
ownership while exposing the current total directly on the shareholder
form.

4. Share Purchase Model

Technical model

ats.share.purchase

Purpose

The purchase model represents a request to acquire shares from the
available share pool.

Main fields

Field                   Type                    Description

name                  Char                    Purchase reference
generated from an Odoo
sequence.

shareholder_id        Many2one                Shareholder making the
purchase.

company_id            Many2one                Company derived from
the selected
shareholder.

quantity              Integer                 Number of shares
requested.

unit_price            Float                   Price per share
obtained from Share
Management Settings.

total_amount          Float                   Computed as quantity ×
unit price.

purchase_date         Datetime                Purchase request date.

state                 Selection               Purchase workflow
state.

Workflow

The purchase workflow is:

Draft
  |
  v
Submitted
  |
  v
Approved
  |
  v
Completed

A purchase can also be cancelled where permitted by the workflow and
security rules.

Business rules

Quantity must be greater than zero.

Price per share cannot be negative.

The price is taken from the configured Share Management price.

Users cannot manually change the purchase price through normal
editing.

Officers can work with draft purchase records according to the
security rules.

Only SMS Administrators can approve and complete purchases.

Completion verifies the remaining share pool.

A purchase cannot exceed the currently available shares.

Completion creates a completed ats.share.transaction purchase
record.

Completed purchase records cannot be cancelled or deleted.

Total amount

The total purchase amount is calculated automatically:

Total Amount = Quantity × Price per Share

5. Share Transfer Model

Technical model

ats.share.transfer

Purpose

The transfer model represents the movement of shares from one
shareholder to another.

Main concepts

Field / concept    Description

name             Transfer reference generated from an Odoo sequence.
shareholder_id   Source shareholder.
recipient_id     Destination shareholder.
quantity         Number of shares being transferred.
transfer_date    Date of the transfer.
state            Transfer workflow state.
notes            Additional transfer notes.

Workflow

The implemented workflow supports:

Draft
  |
  v
Submitted
  |
  v
Approved
  |
  v
Completed

The implementation also supports rejected/cancelled states where
applicable.

Business rules

Source and destination shareholders must be different.

Transfer quantity must be greater than zero.

The source shareholder must own enough shares.

Only SMS Administrators can approve and complete transfers.

Completion reduces the source shareholder's ownership.

Completion increases the destination shareholder's ownership.

Completion creates a transaction history record.

A transfer does not change the number of shares sold from the global
pool.

6. Share Transaction Model

Technical model

ats.share.transaction

Purpose

The transaction model is the audit/history model for completed share
movements.

It records the completed activity used to calculate shareholder
ownership.

Main fields

Field                       Type                    Description

name                      Char                    Transaction reference.

shareholder_id            Many2one                Shareholder associated
with the transaction.

recipient_id              Many2one                Recipient for transfer
transactions.

company_id                Many2one                Company associated with
the shareholder.

transaction_type          Selection               Purchase, transfer, or
correction transaction.

correction_direction      Selection               Direction used for
correction
transactions.

quantity                  Integer                 Number of shares
involved.

transaction_date          Datetime                Transaction date.

state                     Selection               Transaction state.

running_total             Integer/related         Ownership total
calculated value        associated with the
transaction history.

reversed_transaction_id   Many2one                Links a transaction to
the transaction that
reverses it.

reversal_transaction_id   Many2one                Links to the generated
reversal transaction.

notes                     Text                    Transaction notes.

Transaction types

The model supports:

Purchase

Transfer

Correction

This unified transaction model provides one audit history for completed
share movements while purchase and transfer requests remain separate
workflow models.

Append-only behavior

Completed transactions cannot be edited or deleted.

If a completed transaction must be corrected, the system creates a new
corrective or reversal transaction instead of modifying the original
historical record.

Reversal behavior

The reversal operation is administrator-controlled.

Depending on the original transaction:

A purchase can be reversed through a correction that decreases
ownership.

A transfer can be reversed through a reverse transfer.

A correction can be reversed by applying the opposite correction
direction.

This preserves the original audit record.

7. Share Settings

Technical model

res.config.settings

Purpose

The settings extension stores the configurable values used by the Share
Management application.

Main fields

Field                      Type              Configuration Parameter                         Description

total_shares_available   Integer           ats_share_management.total_shares_available   Total number of
shares that can
be sold.

price_per_share          Float             ats_share_management.price_per_share          Configured price
per share.

shares_sold              Integer           Computed                                        Number of
completed
purchase shares.

Business rules

Total shares available cannot be reduced below shares already sold.

Price per share cannot be negative.

Purchase processing reads the configured price instead of using a
hard-coded application value.

Shares sold are calculated from completed purchase transactions.

Remaining shares are calculated from the configured pool minus
completed purchases.

8. Dashboard Models

Dashboard

ats.share.dashboard

The dashboard is a transient model used to present current share
statistics for the active company.

Main values include:

Total shares available.

Shares sold.

Shares remaining.

Top shareholders by ownership.

The dashboard reads current transaction and shareholder information when
it is opened.

Dashboard line

ats.share.dashboard.line

This transient model stores the rows displayed for the top shareholders.

Main values include:

Dashboard.

Rank.

Shareholder.

Shares owned.

Ownership percentage.

The dashboard limits the displayed shareholders to the top 10 by current
ownership.

Ownership percentage is calculated as:

Ownership Percentage =
    Shareholder Shares Owned / Total Shares Sold × 100

When no shares have been sold, the ownership percentage is zero.

9. Company Relationships

The main business records are associated with an Odoo company.

The key relationship is:

res.company
     |
     +---- ats.shareholder
                 |
                 +---- ats.share.purchase
                 |
                 +---- ats.share.transaction
                 |
                 +---- ats.share.transfer

Purchase and transaction records derive their company from the
shareholder relationship where applicable.

The security configuration also uses company-based record rules so users
work with records belonging to their permitted companies.

10. Overall Data Flow

Purchase

Share Management Settings
        |
        | price per share
        v
Share Purchase
        |
        | Approved
        v
     Completed
        |
        +----> Share Transaction
        |
        +----> Shareholder ownership increases
        |
        +----> Available pool decreases

Transfer

Source Shareholder
        |
        | quantity
        v
   Share Transfer
        |
        | Approved
        v
     Completed
        |
        +----> Source ownership decreases
        |
        +----> Recipient ownership increases
        |
        +----> Share Transaction
        |
        +----> Total shares sold remains unchanged

Ownership

Completed Transactions
        |
        +---- Purchase       -> +
        +---- Incoming       -> +
        +---- Outgoing       -> -
        +---- Correction     -> +/- 
        |
        v
Current Shareholder Ownership

11. Reporting Relationships

The same ownership information is reused by the reporting features:

Shareholder Register uses shareholder records and current ownership.

Ownership Breakdown uses shareholder ownership and total shares
sold.

Ownership Pivot and Graph operate on shareholder ownership data.

Dashboard uses completed purchases and current shareholder
ownership.

Share Certificate reads the current shareholder ownership at the
time the report is printed.

Transaction History uses ats.share.transaction.

No separate certificate ownership table is maintained.

12. Security Considerations

The module defines three application roles:

Role                                General responsibility

SMS Administrator                   Full administration, settings,
approval, completion, and reversal
operations.

SMS Officer                         Creates and edits records allowed
by the workflow, particularly draft
requests.

SMS Viewer                          Read-only access to SMS records.

The business models also enforce workflow-specific restrictions in
Python in addition to Odoo ACLs and record rules.

13. Design Decisions

Separate Purchase and Transfer models

Purchases and transfers are represented by separate request models
because they have different business workflows and validation rules:

Purchases consume shares from the global pool and calculate a
purchase amount.

Transfers move existing shares between shareholders and do not
change total shares sold.

Both ultimately create records in the unified transaction history model.

Transaction history as the ownership source

Current ownership is calculated from completed transactions rather than
manually maintained by users. This supports the audit requirement and
makes reversals representable as new records.

No separate certificate model

The SRS specifies that the certificate should be generated from the
shareholder record and reflect current ownership when printed.
Therefore, the implementation uses a QWeb report instead of maintaining
a separate certificate database model.

14. Relationship Summary

                    res.company
                         |
                         v
                  ats.shareholder
                  /       |       \
                 /        |        \
                v         v         v
       ats.share.purchase |   ats.share.transfer
                |         |         |
                |         v         |
                +----> ats.share.transaction <----+
                              |
                              v
                    Current Ownership

res.config.settings
        |
        +---- total shares available
        +---- price per share
        +---- shares sold / remaining

ats.share.dashboard
        |
        v
ats.share.dashboard.line

15. Source and Scope

This document describes the current ATS Share Management implementation
and is aligned with the Share Management System SRS.

The SRS explicitly states that the field-by-field data model is
intentionally left to the implementation team. Therefore, the field
definitions and design decisions above document the implemented solution
rather than reproducing a prescribed field-by-field model from the SRS.