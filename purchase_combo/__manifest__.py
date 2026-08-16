{
    'name': 'Purchase Combo Products',
    'version': '1.0',
    'category': 'Purchases',
    'summary': "Add Combo products to Purchase Orders via a choice wizard",
    'description': """
        Lets a user add a Combo-type product to a Purchase Order. A wizard
        ("Add Combo Product") lets them pick which item to buy for each
        combo choice, then automatically creates the corresponding
        purchase order lines (one parent line for the combo, one line per
        chosen item, linked back to the parent line).
    """,
    'depends': ['purchase', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'wizards/purchase_combo_configurator_views.xml',
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
}
