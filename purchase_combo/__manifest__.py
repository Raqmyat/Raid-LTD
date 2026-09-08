{
    'name': 'Purchase Combo Products',
    'version': '19.0.2.0.0',
    'category': 'Purchases',
    'summary': 'Allow Combo products in Purchase Orders with linked component lines',
    'description': """
        Odoo 19 Purchase Combo support.

        - Allows selecting Combo products on Purchase Orders.
        - Automatically expands the Combo into its component products.
        - Keeps the Combo parent and component lines linked.
        - Preserves existing Purchase Order lines.
        - Uses virtual linkage for unsaved parent/child lines.
        - Synchronizes component quantities with the Combo quantity.
        - Persists components when a Combo PO line is created through API/import.
    """,
    'depends': ['purchase', 'product'],
    'data': [
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
