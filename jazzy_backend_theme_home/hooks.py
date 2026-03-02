from odoo import api, SUPERUSER_ID

def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Todos los usuarios internos (no portal)
    users = env["res.users"].search([("share", "=", False)])

    # 🔥 Esto es la clave:
    # Quitamos cualquier acción de inicio (ej: Discuss)
    users.write({"action_id": False})

    print("✅ Home Action limpiado para todos los usuarios internos")