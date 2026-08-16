{
    'name': 'Purchase Combo Products',
    'version': '1.0',
    'category': 'Purchases',
    'summary': "Allow selecting Combo products directly on Purchase Order lines",
    'description': """
        Lets a user pick a Combo-type product directly in the normal
        "Add a product" field of a Purchase Order line (core Odoo hides
        Combo products there by default since they are usually not
        purchase_ok). As soon as a Combo product is selected, all of its
        components are automatically added as separate lines (with their
        own cost and quantity), linked back to the parent Combo line.
        No manual choice/dialog is involved.
    """,
    'depends': ['purchase', 'product'],
    'data': [],
    'installable': True,
    'application': False,
}
