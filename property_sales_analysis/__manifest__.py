# -*- coding: utf-8 -*-
{
    "name": "Property Sales Analysis",
    "version": "18.0.1.0.0",
    "category": "Real Estate",
    "summary": "Sales and presales analysis by condominium with weekly breakdown",
    "author": "Axeel",
    "license": "LGPL-3",
    "depends": [
        "real_estate_bits",
        "sale_goals_management",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/property_views.xml",
        "views/property_sales_summary_views.xml",
        "views/property_sales_cluster_summary_views.xml",
        "views/property_sales_week_summary_views.xml",
        "views/property_sales_week_cluster_summary_views.xml",
        "views/property_sales_week_cluster_detail_views.xml",
        "views/property_sales_week_property_detail_views.xml", 
        "views/property_sales_manager_summary_views.xml",
        "views/property_sales_manager_week_detail_views.xml",  
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}