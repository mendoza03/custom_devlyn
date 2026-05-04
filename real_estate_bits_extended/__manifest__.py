# -*- coding: utf-8 -*-

{
    "name": "Real Estate - Extended",
    "description": """
=====================================
Real Estate - Extended
=====================================
Add extended fields
    """,
    "version": "18.0.0.0.1",
    "category": "Hidden",
    "license": "OPL-1",
    "depends": [
        "real_estate_bits",
    ],
    "data": [
        "views/project_amenities_views.xml",
        "views/project_worksite_views.xml",
        "views/property_views.xml",
        "views/menuitems.xml",
    ],
    "assets": {
        "web.assets_backend": [
            # "real_estate_bits_extended/static/src/js/place_autocomplete.js",
            # "real_estate_bits_extended/static/src/xml/dashboard_view.xml",
        ],
    },
    "support": "luisangel-glez",
    "auto_install": False,
    "installable": True,
}