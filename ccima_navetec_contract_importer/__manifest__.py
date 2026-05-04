# -*- coding: utf-8 -*-

{
    "name": "CCIMA Navetec - Contract Importer",
    "summary": "Module for contract importer",
    "version": "18.0.0.0.1",
    "category": "Hidden",
    "license": "OPL-1",
    "depends": [
        "real_state_bits_finance_quote",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/ccima_navetec_contract_importer_line_views.xml",
        "wizard/ccima_navetec_contract_importer_views.xml",
        "views/menuitems.xml",
    ],
    "support": "Cerebellum-ITM",
    "auto_install": False,
    "installable": True,
}
