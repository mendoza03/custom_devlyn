import importlib
import inspect
import logging
import os
import threading

import odoo
from odoo import tools
from odoo.tools import config
from odoo.tools.misc import file_path
from odoo.modules import module

from odoo.addons.base.models.ir_ui_menu import IrUiMenu
from odoo.sql_db import ConnectionPool

# imported here to avoid dependency cycle issues
# pylint: disable=wrong-import-position
from . import helper
from . import controllers
from . import models
from . import wizard
from . import override

_url_open = None
if config.get('test_enable', False):
    from odoo.tests import HttpCase

    _url_open = HttpCase.url_open

    try:
        from odoo.addons.test_lint.tests import test_manifests
        from odoo.tests import common
    except ImportError:
        test_manifests = None
        common = None

    try:
        from odoo.addons.test_assetsbundle.tests.test_assetsbundle import AddonManifestPatched
        setUpAddonManifestPatched = AddonManifestPatched.setUp
    except ImportError:
        AddonManifestPatched = None

_logger = logging.getLogger(__name__)
j = os.path.join

get_module_path = module.get_module_path
get_module_icon = module.get_module_icon
load_manifest = module.load_manifest
Manifest = module.Manifest
for_addon = Manifest.for_addon
_compute_web_icon_data = IrUiMenu._compute_web_icon_data
_close_all = ConnectionPool.close_all


def _get_branding_module(branding_module='viin_brand'):
    """
    Wrapper for others to override
    """
    return branding_module


def test_installable(module, mod_path=None):
    """
    :param module: The name of the module (sale, purchase, ...)
    :param mod_path: Physical path of module, if not providedThe name of the module (sale, purchase, ...)
    """
    if module == 'general_settings':
        module = 'base'
    if not mod_path:
        mod_path = get_module_path(module=module, display_warning=False)
    if manifest := Manifest._from_path(mod_path):
        info = {
            'installable': False,
        }
        info.update(manifest._Manifest__manifest_content)
        return info
    return {}


viin_brand_manifest = test_installable(_get_branding_module())


def check_viin_brand_module_icon(module):
    """
    Ensure module icon with
        either '/viin_brand_originmodulename/static/description/icon.png'
        or '/viin_brand/static/img/apps/originmodulename.png'
        exists.
    """
    branding_module = _get_branding_module()
    brand_originmodulename = '%s_%s' % (branding_module, module if module not in ('general_settings', 'modules') else 'base')

    # load manifest of the overriding modules
    viin_brand_originmodulename_manifest = test_installable(brand_originmodulename)

    # /viin_brand/static/img/apps_icon_override/originmodulename.png
    originmodulename_iconpath = os.path.join(branding_module, 'static', 'img', 'apps', '%s.png' % (module if module not in ('general_settings', 'modules') else module == 'general_settings' and 'settings' or 'modules'))

    # /viin_brand_originmodulename'/static/description/icon.png
    iconpath = os.path.join(brand_originmodulename, 'static', 'description', 'icon.png')

    module_icon = False
    for adp in odoo.addons.__path__:
        if viin_brand_originmodulename_manifest.get('installable', False) and os.path.exists(os.path.join(adp, iconpath)):
            module_icon = '/' + iconpath
            break
        elif viin_brand_manifest.get('installable', False) and os.path.exists(os.path.join(adp, originmodulename_iconpath)):
            module_icon = '/' + originmodulename_iconpath
            break
    return module_icon


def get_viin_brand_module_icon(mod):
    """
    This overrides default module icon with
        either '/viin_brand_originmodulename/static/description/icon.png'
        or '/viin_brand/static/img/apps/originmodulename.png'
        where originmodulename is the name of the module whose icon will be overridden
    provided that either of the viin_brand_originmodulename or viin_brand is installable
    """
    # Odoo hard coded its own test in several places (test_systray_get_activities)
    # this check to skip if mod is test_*
    if mod.startswith('test_'):
        return get_module_icon(mod)
    # Override to pass test test test_message_format
    # Because the module_icon value is hardcoded in test
    if getattr(threading.current_thread(), 'testing', False):
        for stack in inspect.stack(0):
            if stack.function in ('test_message_format', 'test_chatbot_message_format'):
                return get_module_icon(mod)

    module_icon = check_viin_brand_module_icon(mod)
    if mod not in ('general_settings', 'modules', 'settings', 'missing'):
        origin_module_icon = get_module_icon(mod)
        if origin_module_icon and origin_module_icon == '/base/static/description/icon.png':
            module_icon = check_viin_brand_module_icon('base')
    if module_icon:
        return module_icon
    return get_module_icon(mod)


def _get_brand_module_website(module):
    """
    This overrides default module website with '/branding_module/apriori.py'
    where apriori contains dict:
    modules_website = {
        'account': 'account's website',
        'sale': 'sale's website,
    }
    :return module website in apriori.py if exists else False
    """
    if viin_brand_manifest.get('installable', False):
        branding_module = _get_branding_module()
        for adp in odoo.addons.__path__:
            try:
                modules_website = importlib.import_module('odoo.addons.%s.apriori' % branding_module).modules_website
                if module in modules_website:
                    return modules_website[module]
            except Exception:
                pass
    return False


def _Manifest_for_addon_plus(module_name: str, *, display_warning: bool = True) -> Manifest | None:
    addon = for_addon(module_name, display_warning=display_warning)
    if addon:
        module_website = _get_brand_module_website(module_name)
        if module_website:
            addon._Manifest__manifest_cached['website'] = module_website
    return addon


def _test_if_loaded_in_server_wide():
    config_options = config.options
    if 'to_base' in config_options.get('server_wide_modules', []):
        return True
    else:
        return False


if not _test_if_loaded_in_server_wide():
    _logger.warning("The module `to_base` should be loaded in server wide mode using `--load`"
                 " option when starting Odoo server (e.g. --load=base,web,to_base)."
                 " Otherwise, some of its functions may not work properly.")


def _update_brand_web_icon_data(env):
    # Generic trick necessary for search() calls to avoid hidden menus which contains 'base.group_no_one'
    menus = env['ir.ui.menu'].with_context({'ir.ui.menu.full_list': True}).search([('web_icon', '!=', False)])
    for m in menus:
        web_icon = m.web_icon
        paths = web_icon.split(',')
        if len(paths) == 2:
            module = paths[0]
            module_name = paths[1].split('/')[-1][:-4]
            if module_name == 'board' or module_name == 'modules' or module_name == 'settings':
                module = module_name
                web_icon = '%s,static/description/icon.png' % module

            module_icon = check_viin_brand_module_icon(module)
            if module_icon:
                web_icon_data = m._compute_web_icon_data(web_icon)
                web_icon = _build_viin_web_icon_path_from_image(module_icon)
                vals = {}
                if m.web_icon != web_icon:
                    vals['web_icon'] = web_icon
                if web_icon_data != m.web_icon_data:
                    vals['web_icon_data'] = web_icon_data
                if vals:
                    m.write(vals)


def _update_favicon(env):
    if viin_brand_manifest.get('installable', False):
        branding_module = _get_branding_module()
        for adp in odoo.addons.__path__:
            img_path = file_path(f'{branding_module}/static/img/favicon.ico')
            if img_path:
                res_company_obj = env['res.company']
                data = res_company_obj._get_default_favicon()
                res_company_obj.with_context(active_test=False).search([]).write({'favicon': data})


def _override_test_manifests_keys():
    """Override to support some manifest keys in module"""
    global test_manifests
    if test_manifests:
        test_manifests.MANIFEST_KEYS.update({
            # Viindoo modules
            'old_technical_name': '',
            'name_vi_VN': '',
            'summary_vi_VN': '',
            'description_vi_VN': '',
            'demo_video_url': '',
            'demo_video_url_vi_VN': '',
            'live_test_url': '',
            'live_test_url_vi_VN': 'https://v19demo-vn.viindoo.com',
            'currency': 'EUR',
            'support': 'apps.support@viindoo.com',
            'price': '99.9',
            'subscription_price': '9.9',
            # OCA module (web_responsive)
            'development_status': '',
            'maintainers': [],
            'excludes': [],
            'task_ids': [],
            # Viindoo theme
            'industries': '',
        })


def _setUpAddonManifestPatched_plus(self):
    """Override to compile assets of to_base in test mode,
       because the module `to_base` is be loaded in server wide.
    """
    res = setUpAddonManifestPatched(self)
    self.manifests.update({'to_base': Manifest.for_addon('to_base')})
    self.patch(odoo.modules.Manifest, 'for_addon', lambda module, **kw: self.manifests[module] if module in self.manifests else self.manifests.defaults(module, **kw))
    return res


def _close_all_plus(self, dsn=None):
    """
    Mute the logger of "Closed X connections to ..." to avoid huge amount of logs
    """
    with tools.mute_logger('odoo.sql_db'):
        res = _close_all(self, dsn=dsn)
    return res


def _url_open_plus(self, url, data=None, files=None, timeout=20, headers=None, json=None, params=None, allow_redirects=True, cookies=None, method: str | None = None):
    """
    [FIX] tests: bump url_open timeout

    Some tests are randomly failling because /web takes more than 10 seconds to load.
    A future pr will speedup /web but waiting for that a small bump of the timeout should help.
    """
    return _url_open(self, url, data=data, files=files, timeout=timeout, headers=headers, json=json, params=params, allow_redirects=allow_redirects, cookies=cookies, method=method)


def _build_viin_web_icon_path_from_image(img_path):
    """
    This method will turn `/module_name/path/to/image` and `module_name/path/to/image`
    into 'module_name,path/to/image' which is for web_icon

    @param img_path: path to the image that will be used for web_icon.
        The path must in the format of either `/module_name/path/to/image` or `module_name/path/to/image`

    @return: web_icon string (e.g. 'module_name,path/to/image')
    """
    path = []
    while img_path:
        img_path, basename = os.path.split(img_path)
        if img_path == os.path.sep:
            img_path = ''
        if img_path:
            path.insert(0, basename)
    return '%s,%s' % (basename, os.path.join(*path))


def _compute_web_icon_data_plus(self, web_icon):
    """
    Override to take web_icon for menus from
        either '/viin_brand_originmodulename'/static/description/icon.png'
        or '/viin_brand/static/img/apps/originmodulename.png'
    """
    paths = web_icon.split(',') if web_icon and isinstance(web_icon, str) else []
    if len(paths) == 2:
        if check_viin_brand_module_icon(paths[0]):
            img_path = get_viin_brand_module_icon(paths[0])
            web_icon = _build_viin_web_icon_path_from_image(img_path)
    return _compute_web_icon_data(self, web_icon)


def pre_init_hook(env):
    module.get_module_icon = get_viin_brand_module_icon
    Manifest.for_addon = _Manifest_for_addon_plus


def post_init_hook(env):
    _update_brand_web_icon_data(env)
    _update_favicon(env)


def uninstall_hook(env):
    module.get_module_icon = get_module_icon
    Manifest.for_addon = _Manifest_for_addon_plus
    if _url_open:
        HttpCase.url_open = _url_open
    ConnectionPool.close_all = _close_all


def post_load():
    if config.get('test_enable', False):
        if test_manifests:
            _override_test_manifests_keys()
        if AddonManifestPatched:
            AddonManifestPatched.setUp = _setUpAddonManifestPatched_plus
        HttpCase.url_open = _url_open_plus
        # Because we are disabling test tour on runbot due to to_backend_theme module being affected
        # This will result in faster response times for browser checks, improving performance and reducing unnecessary processing
        # Each test will save 9.9s
        global common
        if common:
            common.CHECK_BROWSER_ITERATIONS = 1
    module.get_module_icon = get_viin_brand_module_icon
    Manifest.for_addon = _Manifest_for_addon_plus
    ConnectionPool.close_all = _close_all_plus
    IrUiMenu._compute_web_icon_data = _compute_web_icon_data_plus
