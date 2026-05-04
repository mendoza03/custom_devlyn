# -*- coding: utf-8 -*-

{
    "name": "Real estate bits - Commissions",
    "summary": "",
    "version": "18.0.0.0.1",
    "category": "Base",
    "license": "OPL-1",
    "depends": [
        "crm",
        "account",
        "sale_management",
        "real_estate_bits",
        "real_state_bits_finance_quote",
    ],
    "data": [
        "data/commission_scenary_data.xml",
        "security/ir.model.access.csv",
        "./security/groups.xml",
        "views/account_move_views.xml",
        "views/commission_calculate_views.xml",
        "views/commission_scenary_views.xml",
        "views/product_template_views.xml",
        "views/property_contract_views.xml",
        "views/res_config_settings_views.xml",
        "views/menuitems.xml",
    ],
    "support": "luisangel-glez",
    "auto_install": False,
    "installable": True,
}