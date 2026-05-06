from odoo import api, fields, models


class DevlynCatalogRegion(models.Model):
    _name = "devlyn.catalog.region"
    _description = "Catalogo Devlyn de Regiones"
    _order = "name"

    name = fields.Char(required=True, index=True, string="Nombre")
    legacy_region_id = fields.Integer(required=True, index=True, string="Id Región Legado")
    active = fields.Boolean(default=True, index=True, string="Activo")

    _legacy_region_id_uniq = models.Constraint("UNIQUE(legacy_region_id)", "La region ya existe.")


class DevlynCatalogZone(models.Model):
    _name = "devlyn.catalog.zone"
    _description = "Catalogo Devlyn de Zonas"
    _order = "region_id, name"

    name = fields.Char(required=True, index=True, string="Nombre")
    legacy_zone_id = fields.Integer(required=True, index=True, string="Id Zona Legado")
    region_id = fields.Many2one(
        "devlyn.catalog.region",
        required=True,
        ondelete="restrict",
        index=True,
        string="Región",
    )
    active = fields.Boolean(default=True, index=True, string="Activo")

    _legacy_zone_id_uniq = models.Constraint("UNIQUE(legacy_zone_id)", "La zona ya existe.")


class DevlynCatalogDistrict(models.Model):
    _name = "devlyn.catalog.district"
    _description = "Catalogo Devlyn de Distritos"
    _order = "zone_id, name"

    name = fields.Char(required=True, index=True, string="Nombre")
    legacy_district_id = fields.Integer(required=True, index=True, string="Id Distrito Legado")
    region_id = fields.Many2one(
        "devlyn.catalog.region",
        required=True,
        ondelete="restrict",
        index=True,
        string="Región",
    )
    zone_id = fields.Many2one(
        "devlyn.catalog.zone",
        required=True,
        ondelete="restrict",
        index=True,
        string="Zona",
    )
    active = fields.Boolean(default=True, index=True, string="Activo")

    _legacy_district_id_uniq = models.Constraint("UNIQUE(legacy_district_id)", "El distrito ya existe.")


class DevlynCatalogFormat(models.Model):
    _name = "devlyn.catalog.format"
    _description = "Catalogo Devlyn de Formatos"
    _order = "name"

    name = fields.Char(required=True, index=True, string="Nombre")
    active = fields.Boolean(default=True, index=True, string="Activo")

    _name_uniq = models.Constraint("UNIQUE(name)", "El formato ya existe.")


class DevlynCatalogStatus(models.Model):
    _name = "devlyn.catalog.status"
    _description = "Catalogo Devlyn de Estatus"
    _order = "name"

    name = fields.Char(required=True, index=True, string="Nombre")
    active = fields.Boolean(default=True, index=True, string="Activo")

    _name_uniq = models.Constraint("UNIQUE(name)", "El estatus ya existe.")


class DevlynCatalogOpticalLevel(models.Model):
    _name = "devlyn.catalog.optical.level"
    _description = "Catalogo Devlyn de Nivel Optica Ventas"
    _order = "code"

    code = fields.Char(required=True, index=True, string="Código")
    name = fields.Char(required=True, string="Nombre")
    active = fields.Boolean(default=True, index=True, string="Activo")

    _code_uniq = models.Constraint("UNIQUE(code)", "El nivel de optica ya existe.")


class DevlynCatalogBranch(models.Model):
    _name = "devlyn.catalog.branch"
    _description = "Catalogo Devlyn de Sucursales"
    _order = "center_code"
    _rec_name = "name"

    name = fields.Char(compute="_compute_name", store=True, index=True, string="Descripción")
    center_code = fields.Char(required=True, index=True, string="Id Centro")
    branch_code = fields.Char(required=True, index=True, string="Sucursal")
    branch_name = fields.Char(required=True, index=True, string="Nombre Sucursal")
    optical_level_id = fields.Many2one(
        "devlyn.catalog.optical.level",
        required=True,
        ondelete="restrict",
        index=True,
        string="Nivel Óptica Ventas",
    )
    format_id = fields.Many2one(
        "devlyn.catalog.format",
        required=True,
        ondelete="restrict",
        index=True,
        string="Formato",
    )
    status_id = fields.Many2one(
        "devlyn.catalog.status",
        required=True,
        ondelete="restrict",
        index=True,
        string="Estatus",
    )
    region_id = fields.Many2one(
        "devlyn.catalog.region",
        required=True,
        ondelete="restrict",
        index=True,
        string="Región",
    )
    zone_id = fields.Many2one(
        "devlyn.catalog.zone",
        required=True,
        ondelete="restrict",
        index=True,
        string="Zona",
    )
    district_id = fields.Many2one(
        "devlyn.catalog.district",
        required=True,
        ondelete="restrict",
        index=True,
        string="Distrito",
    )
    active = fields.Boolean(default=True, index=True, string="Activo")

    _center_code_uniq = models.Constraint("UNIQUE(center_code)", "El centro ya existe.")

    @api.depends("center_code", "branch_name")
    def _compute_name(self):
        for record in self:
            pieces = [piece for piece in [record.center_code, record.branch_name] if piece]
            record.name = " - ".join(pieces) if pieces else ""
