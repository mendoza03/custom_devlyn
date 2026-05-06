from odoo import SUPERUSER_ID, api

from .services.catalog_loader import DevlynCatalogLoader


def post_init_hook(*args):
    if len(args) == 1:
        env = args[0]
    elif len(args) == 2:
        cr, _registry = args
        env = api.Environment(cr, SUPERUSER_ID, {})
    else:
        raise TypeError(f"Unexpected post_init_hook arguments: {args!r}")
    DevlynCatalogLoader(env).load_all()
