import os
import xmlrpc.client


ODOO_URL = os.environ.get("ODOO_URL", "https://erp.odootest.mvpstart.click")
ODOO_DB = os.environ.get("ODOO_DB", "devlyn_com")


def verify_odoo_password(login: str, password: str) -> bool:
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common", allow_none=True)
    uid = common.authenticate(ODOO_DB, login, password, {})
    return bool(uid)


def lambda_handler(event, context):
    username = event.get("userName")
    answer = event.get("request", {}).get("challengeAnswer")

    is_valid = False
    if username and answer:
        try:
            is_valid = verify_odoo_password(username, answer)
        except Exception:
            is_valid = False

    event["response"]["answerCorrect"] = bool(is_valid)
    return event
