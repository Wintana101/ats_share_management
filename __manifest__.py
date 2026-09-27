{
    'name': 'ATS Share Management',
    'version': '17.0.1.0.0',
    'category': 'Operations',
    'summary': 'Shareholder and share transaction management',
    'description': """ATS Share Management
        Manage shareholders, share purchases, share transfers,
        ownership, transaction history, certificates, and reports.
    """,

    'author': 'Ashewa Technology Solution S.C',
    'license': 'LGPL-3',

    'depends': [
        'base',
        'mail',
    ],

    'data': [
        'security/security_groups.xml',
        'security/share_management_rules.xml',
        'security/ir.model.access.csv',

        'data/shareholder_sequence.xml',
        'data/purchase_sequence.xml',
        'data/transaction_sequence.xml',
        'data/transfer_sequence.xml',
        'data/demo_data.xml',

        'reports/share_certificate_report.xml',
        'reports/shareholder_register_report.xml',

        'views/share_management_menu.xml',
        'views/share_dashboard_views.xml',
        'views/shareholder_views.xml',
        'views/purchase_views.xml',
        'views/transaction_views.xml',
        'views/share_settings_views.xml',
        'views/transfer_views.xml',
        'views/ownership_report_views.xml',
    ],

    'installable': True,
    'application': True,
}
