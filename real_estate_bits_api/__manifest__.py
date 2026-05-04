# -*- coding: utf-8 -*-

{
    "name": "Real Estate - API",
    "description": """
=====================================
Real Estate - API
=====================================
Add API for get data of real estate
    """,
    "version": "18.0.0.1.1",
    "category": "Hidden",
    "license": "OPL-1",
    "depends": [
        "fastapi",
        "product",
        "real_estate_bits_extended",
    ],
    "data": [
        "security/real_estate_bits_api_security.xml",
        "security/ir.model.access.csv",
        "views/fastapi_endpoint_views.xml",
    ],
    "support": "luisangel-glez",
    "auto_install": False,
    "installable": True,
}