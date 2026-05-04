# -*- coding: utf-8 -*-
import base64
import json
from odoo import http
from odoo.http import request


class ProductImageOverlayController(http.Controller):

    # -------- Map 'source' keys to product fields/labels ----------
    _SOURCE_MAP = {
        "name":        ("PRODUCT",        lambda p: p.display_name or ""),
        "default_code":("INTERNAL REFERENCE", lambda p: p.default_code or ""),
        "list_price":  ("LIST PRICE",     lambda p: f"{p.list_price:,.2f}"),
        "uom":         ("UOM",            lambda p: (p.uom_id.name or "")),
        "category":    ("CATEGORY",       lambda p: (p.categ_id.display_name or "")),
        "qty_available": ("QTY AVAILABLE", lambda p: f"{p.sudo().qty_available:,.2f}"),
    }

    @staticmethod
    def _sanitize_pct(val, default=0.0):
        try:
            v = float(val)
        except Exception:
            return float(default)
        # clamp 0..100
        return max(0.0, min(100.0, v))

    def _resolve_overlays(self, product, overlays_client):
        """From client overlays (with 'source') build final overlays with text."""
        final = []
        for o in overlays_client:
            src = (o.get("source") or "").strip()
            x = self._sanitize_pct(o.get("x_pct", 0))
            y = self._sanitize_pct(o.get("y_pct", 0))
            w = self._sanitize_pct(o.get("w_pct", 10))
            h = self._sanitize_pct(o.get("h_pct", 8))

            if src in self._SOURCE_MAP:
                default_title, value_fn = self._SOURCE_MAP[src]
                title = (o.get("title") or default_title).strip()
                text = value_fn(product)
            else:
                # Free text (if user passed 'source' empty, allow manual text)
                title = (o.get("title") or "BOX").strip()
                text = (o.get("text") or "").strip()

            final.append({
                "x_pct": x, "y_pct": y, "w_pct": w, "h_pct": h,
                "title": title, "text": text,
            })
        return final

    # ---------------- GET: page with form ----------------
    @http.route("/product/overlay", type="http", auth="user", website=True, methods=["GET"])
    def product_overlay_form(self, **kwargs):
        products = request.env["product.template"].sudo().search(
            [("sale_ok", "=", True)], limit=200, order="name asc"
        )
        values = {
            "products": products,
            "image_data_url": None,
            "product": None,
            "overlays": [],
        }
        return request.render("product_image_overlay.product_image_overlay_page", values)

    # ---------------- POST: render preview ----------------
    @http.route("/product/overlay/preview", type="http", auth="user", website=True, methods=["POST"])
    def product_overlay_preview(self, **post):
        product_id = int(post.get("product_id") or 0)
        product = request.env["product.template"].sudo().browse(product_id)
        if not product.exists():
            return request.redirect("/product/overlay")

        # Image: read file -> base64 -> data URL
        image_data_url = None
        upfile = request.httprequest.files.get("image_file")
        if upfile:
            raw = upfile.read()
            mime = upfile.mimetype or "image/png"
            image_b64 = base64.b64encode(raw).decode("utf-8")
            image_data_url = f"data:{mime};base64,{image_b64}"

        # Overlays from client (JSON)
        overlays_client = []
        if post.get("overlays_json"):
            try:
                overlays_client = json.loads(post["overlays_json"])
                if not isinstance(overlays_client, list):
                    overlays_client = []
            except Exception:
                overlays_client = []

        # Build final overlays (resolve 'source' -> product field text)
        overlays = self._resolve_overlays(product, overlays_client)

        values = {
            "products": request.env["product.template"].sudo().search([], limit=200, order="name asc"),
            "image_data_url": image_data_url,
            "product": product,
            "overlays": overlays,
        }
        return request.render("product_image_overlay.product_image_overlay_page", values)
# -*- coding: utf-8 -*-
import base64
import json
from odoo import http
from odoo.http import request


class ProductImageOverlayController(http.Controller):

    # -------- Map 'source' keys to product fields/labels ----------
    _SOURCE_MAP = {
        "name":        ("PRODUCT",        lambda p: p.display_name or ""),
        "default_code":("INTERNAL REFERENCE", lambda p: p.default_code or ""),
        "list_price":  ("LIST PRICE",     lambda p: f"{p.list_price:,.2f}"),
        "uom":         ("UOM",            lambda p: (p.uom_id.name or "")),
        "category":    ("CATEGORY",       lambda p: (p.categ_id.display_name or "")),
        "qty_available": ("QTY AVAILABLE", lambda p: f"{p.sudo().qty_available:,.2f}"),
    }

    @staticmethod
    def _sanitize_pct(val, default=0.0):
        try:
            v = float(val)
        except Exception:
            return float(default)
        # clamp 0..100
        return max(0.0, min(100.0, v))

    def _resolve_overlays(self, product, overlays_client):
        """From client overlays (with 'source') build final overlays with text."""
        final = []
        for o in overlays_client:
            src = (o.get("source") or "").strip()
            x = self._sanitize_pct(o.get("x_pct", 0))
            y = self._sanitize_pct(o.get("y_pct", 0))
            w = self._sanitize_pct(o.get("w_pct", 10))
            h = self._sanitize_pct(o.get("h_pct", 8))

            if src in self._SOURCE_MAP:
                default_title, value_fn = self._SOURCE_MAP[src]
                title = (o.get("title") or default_title).strip()
                text = value_fn(product)
            else:
                # Free text (if user passed 'source' empty, allow manual text)
                title = (o.get("title") or "BOX").strip()
                text = (o.get("text") or "").strip()

            final.append({
                "x_pct": x, "y_pct": y, "w_pct": w, "h_pct": h,
                "title": title, "text": text,
            })
        return final

    # ---------------- GET: page with form ----------------
    @http.route("/product/overlay", type="http", auth="user", website=True, methods=["GET"])
    def product_overlay_form(self, **kwargs):
        products = request.env["product.template"].sudo().search(
            [("sale_ok", "=", True)], limit=200, order="name asc"
        )
        values = {
            "products": products,
            "image_data_url": None,
            "product": None,
            "overlays": [],
        }
        return request.render("product_image_overlay.product_image_overlay_page", values)

    # ---------------- POST: render preview ----------------
    @http.route("/product/overlay/preview", type="http", auth="user", website=True, methods=["POST"])
    def product_overlay_preview(self, **post):
        product_id = int(post.get("product_id") or 0)
        product = request.env["product.template"].sudo().browse(product_id)
        if not product.exists():
            return request.redirect("/product/overlay")

        # Image: read file -> base64 -> data URL
        image_data_url = None
        upfile = request.httprequest.files.get("image_file")
        if upfile:
            raw = upfile.read()
            mime = upfile.mimetype or "image/png"
            image_b64 = base64.b64encode(raw).decode("utf-8")
            image_data_url = f"data:{mime};base64,{image_b64}"

        # Overlays from client (JSON)
        overlays_client = []
        if post.get("overlays_json"):
            try:
                overlays_client = json.loads(post["overlays_json"])
                if not isinstance(overlays_client, list):
                    overlays_client = []
            except Exception:
                overlays_client = []

        # Build final overlays (resolve 'source' -> product field text)
        overlays = self._resolve_overlays(product, overlays_client)

        values = {
            "products": request.env["product.template"].sudo().search([], limit=200, order="name asc"),
            "image_data_url": image_data_url,
            "product": product,
            "overlays": overlays,
        }
        return request.render("product_image_overlay.product_image_overlay_page", values)
