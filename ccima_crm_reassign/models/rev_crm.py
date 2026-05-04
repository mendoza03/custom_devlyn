# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import mimetypes
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
from odoo.osv import expression
import logging
_logger = logging.getLogger(__name__)

class ContractBrief(models.Model):
    _name = 'rev.crm.contract.brief'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = 'Contract Brief'
    _rec_name = 'full_name'
    _order = 'id desc'

    person_type = fields.Selection(
        selection=[
            ('fisica', 'Natural Person'),
            ('morial', 'Legal Entity'),
            ('coopropiedad', 'Co-Ownership'),
        ],
        string='Person Type',
    )

    brief_folder_id = fields.Many2one('documents.document', string='Documents Folder')
    contract_folder_id = fields.Many2one('documents.document', string='Documents Folder')
    contract_file = fields.Binary(
        string='Contract File',
        attachment=True,
        help="Main contract file."
    )
    contract_file_name = fields.Char(
        string='Contract File Name',
        help="Name of the contract file."
    )

    full_name = fields.Char(string='Full Name', required=True)
    full_name_file = fields.Binary(string='Full Name Document', attachment=True)
    full_name_file_name = fields.Char(string='Full Name Document Name')

    curp = fields.Char(string='CURP')
    curp_file = fields.Binary(string='CURP Document', attachment=True)
    curp_file_name = fields.Char(string='CURP Document Name')

    rfc = fields.Char(string='RFC')
    rfc_file = fields.Binary(string='RFC Document', attachment=True)
    rfc_file_name = fields.Char(string='RFC Document Name')

    marital_status = fields.Selection(
        selection=[
            ('soltero', 'SOLTERO'),
            ('casado_bienes_separados', 'CASADO BIENES SEPARADOS'),
            ('casado_sociedad_conyugal', 'CASADO SOCIEDAD CONYUGAL'),
            ('soltera', 'SOLTERA'),
            ('casada_bienes_separados', 'CASADA BIENES SEPARADOS'),
            ('casada_sociedad_conyugal', 'CASADA SOCIEDAD CONYUGAL'),
        ],
        string='Marital Status',
    )

    nationality = fields.Char(string='Nationality')
    nationality_person = fields.Many2one('res.country',string='Nacionalidad')
    address = fields.Text(string='Address')
    street_name = fields.Char(string="Street")
    external_number = fields.Char(string="Exterior Number")
    number = fields.Char(string="Number")
    internal_number = fields.Char(string="Interior Number")
    suburb = fields.Char(string="Neighborhood / Suburb")
    municipality = fields.Char(string="Municipality / City")
    state_name = fields.Char(string="State")
    zip_code = fields.Char(string="Postal Code (ZIP Code)")
    address_file = fields.Binary(string='Address Document', attachment=True)
    address_file_name = fields.Char(string='Address Document Name')
    city_rev = fields.Char(string='City')
    state_rev = fields.Many2one('res.country.state', string='Nationality')

    phone_number = fields.Char(string='Phone Number')
    email = fields.Char(string='Email')
    official_id = fields.Char(string='Official ID')
    official_id_file = fields.Binary(string='Official ID Document', attachment=True)
    official_id_file_name = fields.Char(string='Official ID Document Name')

    official_id_name = fields.Char(string='Nombre de la identificacion')
    official_id_emmisor = fields.Char(string='Emmisor de la identificacion')

    lives_in_house = fields.Selection(
        selection=[
            ('propia', 'OWNED'),
            ('rentada', 'RENTED'),
            ('familiar', 'FAMILY'),
        ],
        string='Lives in a house',
    )

    studies = fields.Selection(
        selection=[
            ('primaria', 'PRIMARY'),
            ('secundaria', 'SECONDARY'),
            ('preparatoria', 'HIGH SCHOOL'),
            ('tsu', 'TSU'),
            ('licenciatura', 'BACHELOR'),
            ('ingenieria', 'ENGINEERING'),
            ('maestria', 'MASTER'),
            ('doctorado', 'DOCTORATE'),
        ],
        string='Studies',
    )

    profession = fields.Char(string='Profession')
    occupation = fields.Char(string='Occupation')
    employer_name = fields.Char(string='Employer Name')
    job_position = fields.Char(string='Job Position')
    seniority = fields.Char(string='Seniority')
    employer_phone = fields.Char(string='Employer Phone')
    employer_address = fields.Text(string='Employer Address')
    place_of_birth = fields.Char(string="Place of Birth")
    date_of_birth = fields.Date(string="Date of Birth")
    applies_assets = fields.Char(string="Applies Assets")
    applies_assets_person = fields.Boolean(string="Applies Assets")

    fiscal_address_le = fields.Text(string='Tax Address')
    business_line_le = fields.Char(string='Business Line')
    activity_le = fields.Char(string='Activity')
    registry_folio_le = fields.Char(string='Registry Folio')
    registry_date_le = fields.Char(string='Registry Date')
    registry_city_le = fields.Char(string='Registry City')
    corporate_purpose_le = fields.Text(string='Corporate Purpose')
    mercantile_folio_le = fields.Char(string='Mercantile Folio')
    notary_name_le = fields.Char(string='Notary Name')

    full_name_rl = fields.Char(string='Full Name (RL)')
    full_name_rl_file = fields.Binary(string='Full Name (RL) Document', attachment=True)
    full_name_rl_file_name = fields.Char(string='Full Name (RL) Document Name')

    curp_rl = fields.Char(string='CURP (RL)')
    curp_rl_file = fields.Binary(string='CURP (RL) Document', attachment=True)
    curp_rl_file_name = fields.Char(string='CURP (RL) Document Name')

    rfc_rl = fields.Char(string='RFC (RL)')
    rfc_rl_file = fields.Binary(string='RFC (RL) Document', attachment=True)
    rfc_rl_file_name = fields.Char(string='RFC (RL) Document Name')

    marital_status_rl = fields.Selection(
        selection=[
            ('soltero', 'SINGLE'),
            ('casado_bienes_separados', 'MARRIED SEPARATE PROPERTY'),
            ('casado_sociedad_conyugal', 'MARRIED COMMUNITY PROPERTY'),
        ],
        string='Marital Status (RL)',
    )
    nationality_rl = fields.Char(string='Nationality (RL)')
    address_rl = fields.Text(string='Address (RL)')
    address_rl_file = fields.Binary(string='Address (RL) Document', attachment=True)
    address_rl_file_name = fields.Char(string='Address (RL) Document Name')

    phone_number_rl = fields.Char(string='Phone Number (RL)')
    email_rl = fields.Char(string='Email (RL)')
    official_id_rl = fields.Char(string='Official ID (RL)')
    official_id_rl_file = fields.Binary(string='Official ID (RL) Document', attachment=True)
    official_id_rl_file_name = fields.Char(string='Official ID (RL) Document Name')

    lives_in_house_rl = fields.Selection(
        selection=[
            ('propia', 'OWNED'),
            ('rentada', 'RENTED'),
            ('familiar', 'FAMILY'),
        ],
        string='Lives in a house (RL)',
    )
    studies_rl = fields.Selection(
        selection=[
            ('primaria', 'PRIMARY'),
            ('secundaria', 'SECONDARY'),
            ('preparatoria', 'HIGH SCHOOL'),
            ('tsu', 'TSU'),
            ('licenciatura', 'BACHELOR'),
            ('ingenieria', 'ENGINEERING'),
            ('maestria', 'MASTER'),
            ('doctorado', 'DOCTORATE'),
        ],
        string='Studies (RL)',
    )
    profession_rl = fields.Char(string='Profession (RL)')
    occupation_rl = fields.Char(string='Occupation (RL)')
    employer_name_rl = fields.Char(string='Employer Name (RL)')
    job_position_rl = fields.Char(string='Job Position (RL)')
    seniority_rl = fields.Char(string='Seniority (RL)')
    employer_phone_rl = fields.Char(string='Employer Phone (RL)')
    employer_address_rl = fields.Text(string='Employer Address (RL)')

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    company_legal_name = fields.Char(string='Company Legal Name', compute='_compute_company_legal_name')
    company_legal_rep = fields.Char(string='Legal Representative', default='Lic. Mauricio Rojano Mata')
    company_constitutive_act = fields.Char(string='Constitutive Act', default='Escritura Pública número 37,991 ante Notaría Pública No. 2 de Querétaro')
    company_notary = fields.Char(string='Current Notary', default='Francisco Pérez Rojas, Notaría No. 2, Querétaro')
    company_address = fields.Text(string='Company Address', default='Carretera Querétaro – San Luis Potosí,\nnumero 5997, Santa Rosa Jáuregui,\nQuerétaro, C.P. 76220')
    company_email = fields.Char(string='Company Email', default='cobranza@habitta.com.mx')

    worksite_id = fields.Many2one('project.worksite', string='Development')
    municipality = fields.Char(string='Municipality')
    lot = fields.Char(string='Lot')
    condominium_id = fields.Many2one('condominium.worksite', string='Condominium')
    surface = fields.Char(string='Surface')
    related_public_deeds = fields.Char(string='Related Public Deeds')
    recent_public_deed = fields.Char(string='Recent Public Deed')
    total_price = fields.Char(string='Total Price')
    finance_price = fields.Char(string='Total Price Finance')
    total_down_payment = fields.Char(string='Total Down Payment')
    financing = fields.Char(string='Financing')
    term = fields.Char(string='Term')
    payments_no_interest = fields.Char(string='Payments without interest (48 months)')
    payments_interest_1 = fields.Char(string='Payments with 1% interest (72 months)')
    payments_interest_1_25 = fields.Char(string='Payments with 1.25% interest (60 months)')
    contract_date = fields.Char(string='Contract Date')
    special_authorizations = fields.Text(string='SPECIAL AUTHORIZATIONS OR CONDITIONS')

    internal_fee = fields.Char(string='Internal Maintenance Fee')
    external_fee = fields.Char(string='External Maintenance Fee')
    main_amenities = fields.Char(string='Main Amenities (Zone B)')
    additional_amenities = fields.Char(string='Additional Amenities')

    appreciation_on_time = fields.Char(string='Appreciation On Time', default='Plusvalía del 20% respecto al precio preventa inicial por m², aplicable a los 4 años posteriores a la compra')
    appreciation_late = fields.Char(string='Appreciation Otherwise', default='Se devuelve el monto sin plusvalía y con una penalización del 20% sobre las aportaciones')
    lead_id = fields.Many2one('crm.lead', string='Lead')
    sale_order_id = fields.Many2one('sale.order', string='Quotation')

    state = fields.Selection(
        [('draft', 'Draft'), ('validated', 'Validated')],
        string='Status',
        default='draft'
    )
    validated_date = fields.Date(string='Validated On')
    persons_visible = fields.Integer(default=1)

    full_name_2 = fields.Char()
    full_name_file_2 = fields.Binary(attachment=True)
    full_name_file_name_2 = fields.Char()
    official_id_2 = fields.Char()
    official_id_file_2 = fields.Binary(attachment=True)
    official_id_file_name_2 = fields.Char()
    address_2 = fields.Text()
    street_name_2 = fields.Char(string="Street")
    external_number_2 = fields.Char(string="Exterior Number")
    number_2 = fields.Char(string="Number")
    internal_number_2 = fields.Char(string="Interior Number")
    suburb_2 = fields.Char(string="Neighborhood / Suburb")
    municipality_2 = fields.Char(string="Municipality / City")
    state_name_2 = fields.Char(string="State")
    zip_code_2 = fields.Char(string="ZIP Code")
    address_file_2 = fields.Binary(attachment=True)
    address_file_name_2 = fields.Char()
    lives_in_house_2 = fields.Boolean()
    studies_2 = fields.Selection(
        selection=[
            ('primaria', 'PRIMARY'),
            ('secundaria', 'SECONDARY'),
            ('preparatoria', 'HIGH SCHOOL'),
            ('tsu', 'TSU'),
            ('licenciatura', 'BACHELOR'),
            ('ingenieria', 'ENGINEERING'),
            ('maestria', 'MASTER'),
            ('doctorado', 'DOCTORATE'),
        ],
        string='Studies',
    )
    profession_2 = fields.Char()
    marital_status_2 = fields.Selection(
        selection=[
            ('soltero', 'SINGLE'),
            ('casado_bienes_separados', 'MARRIED SEPARATE PROPERTY'),
            ('casado_sociedad_conyugal', 'MARRIED COMMUNITY PROPERTY'),
        ],
        string='Marital Status',
    )
    phone_number_2 = fields.Char()
    email_2 = fields.Char()
    nationality_2 = fields.Char()
    rfc_2 = fields.Char()
    rfc_file_2 = fields.Binary(attachment=True)
    rfc_file_name_2 = fields.Char()
    curp_2 = fields.Char()
    curp_file_2 = fields.Binary(attachment=True)
    curp_file_name_2 = fields.Char()
    occupation_2 = fields.Char()
    job_position_2 = fields.Char()
    seniority_2 = fields.Char()
    employer_name_2 = fields.Char()
    employer_phone_2 = fields.Char()
    employer_address_2 = fields.Char()
    place_of_birth_2 = fields.Char(string="Place of Birth")
    date_of_birth_2 = fields.Date(string="Date of Birth")
    applies_assets_2 = fields.Char(string="Applies Assets")

    full_name_3 = fields.Char()
    full_name_file_3 = fields.Binary(attachment=True)
    full_name_file_name_3 = fields.Char()
    official_id_3 = fields.Char()
    official_id_file_3 = fields.Binary(attachment=True)
    official_id_file_name_3 = fields.Char()
    address_3 = fields.Text()
    street_name_3 = fields.Char(string="Street")
    external_number_3 = fields.Char(string="Exterior Number")
    number_3 = fields.Char(string="Number")
    internal_number_3 = fields.Char(string="Interior Number")
    suburb_3 = fields.Char(string="Neighborhood / Suburb")
    municipality_3 = fields.Char(string="Municipality / City")
    state_name_3 = fields.Char(string="State")
    zip_code_3 = fields.Char(string="ZIP Code")
    address_file_3 = fields.Binary(attachment=True)
    address_file_name_3 = fields.Char()
    lives_in_house_3 = fields.Boolean()
    studies_3 = fields.Selection(
        selection=[
            ('primaria', 'PRIMARY'),
            ('secundaria', 'SECONDARY'),
            ('preparatoria', 'HIGH SCHOOL'),
            ('tsu', 'TSU'),
            ('licenciatura', 'BACHELOR'),
            ('ingenieria', 'ENGINEERING'),
            ('maestria', 'MASTER'),
            ('doctorado', 'DOCTORATE'),
        ],
        string='Studies',
    )
    profession_3 = fields.Char()
    marital_status_3 = fields.Selection(
        selection=[
            ('soltero', 'SINGLE'),
            ('casado_bienes_separados', 'MARRIED SEPARATE PROPERTY'),
            ('casado_sociedad_conyugal', 'MARRIED COMMUNITY PROPERTY'),
        ],
        string='Marital Status',
    )
    phone_number_3 = fields.Char()
    email_3 = fields.Char()
    nationality_3 = fields.Char()
    rfc_3 = fields.Char()
    rfc_file_3 = fields.Binary(attachment=True)
    rfc_file_name_3 = fields.Char()
    curp_3 = fields.Char()
    curp_file_3 = fields.Binary(attachment=True)
    curp_file_name_3 = fields.Char()
    occupation_3 = fields.Char()
    job_position_3 = fields.Char()
    seniority_3 = fields.Char()
    employer_name_3 = fields.Char()
    employer_phone_3 = fields.Char()
    employer_address_3 = fields.Char()
    place_of_birth_3 = fields.Char(string="Place of Birth")
    date_of_birth_3 = fields.Date(string="Date of Birth")
    applies_assets_3 = fields.Char(string="Applies Assets")

    full_name_4 = fields.Char()
    full_name_file_4 = fields.Binary(attachment=True)
    full_name_file_name_4 = fields.Char()
    official_id_4 = fields.Char()
    official_id_file_4 = fields.Binary(attachment=True)
    official_id_file_name_4 = fields.Char()
    address_4 = fields.Text()
    street_name_4 = fields.Char(string="Street")
    external_number_4 = fields.Char(string="Exterior Number")
    number_4 = fields.Char(string="Number")
    internal_number_4 = fields.Char(string="Interior Number")
    suburb_4 = fields.Char(string="Neighborhood / Suburb")
    municipality_4 = fields.Char(string="Municipality / City")
    state_name_4 = fields.Char(string="State")
    zip_code_4 = fields.Char(string="ZIP Code")
    address_file_4 = fields.Binary(attachment=True)
    address_file_name_4 = fields.Char()
    lives_in_house_4 = fields.Boolean()
    studies_4 = fields.Selection(
        selection=[
            ('primaria', 'PRIMARY'),
            ('secundaria', 'SECONDARY'),
            ('preparatoria', 'HIGH SCHOOL'),
            ('tsu', 'TSU'),
            ('licenciatura', 'BACHELOR'),
            ('ingenieria', 'ENGINEERING'),
            ('maestria', 'MASTER'),
            ('doctorado', 'DOCTORATE'),
        ],
        string='Studies',
    )
    profession_4 = fields.Char()
    marital_status_4 = fields.Selection(
        selection=[
            ('soltero', 'SINGLE'),
            ('casado_bienes_separados', 'MARRIED SEPARATE PROPERTY'),
            ('casado_sociedad_conyugal', 'MARRIED COMMUNITY PROPERTY'),
        ],
        string='Marital Status',
    )
    phone_number_4 = fields.Char()
    email_4 = fields.Char()
    nationality_4 = fields.Char()
    rfc_4 = fields.Char()
    rfc_file_4 = fields.Binary(attachment=True)
    rfc_file_name_4 = fields.Char()
    curp_4 = fields.Char()
    curp_file_4 = fields.Binary(attachment=True)
    curp_file_name_4 = fields.Char()
    occupation_4 = fields.Char()
    job_position_4 = fields.Char()
    seniority_4 = fields.Char()
    employer_name_4 = fields.Char()
    employer_phone_4 = fields.Char()
    employer_address_4 = fields.Char()
    place_of_birth_4 = fields.Char(string="Place of Birth")
    date_of_birth_4 = fields.Date(string="Date of Birth")
    applies_assets_4 = fields.Char(string="Applies Assets")

    full_name_5 = fields.Char()
    full_name_file_5 = fields.Binary(attachment=True)
    full_name_file_name_5 = fields.Char()
    official_id_5 = fields.Char()
    official_id_file_5 = fields.Binary(attachment=True)
    official_id_file_name_5 = fields.Char()
    address_5 = fields.Text()
    street_name_5 = fields.Char(string="Street")
    external_number_5 = fields.Char(string="Exterior Number")
    number_5 = fields.Char(string="Number")
    internal_number_5 = fields.Char(string="Interior Number")
    suburb_5 = fields.Char(string="Neighborhood / Suburb")
    municipality_5 = fields.Char(string="Municipality / City")
    state_name_5 = fields.Char(string="State")
    zip_code_5 = fields.Char(string="ZIP Code")
    address_file_5 = fields.Binary(attachment=True)
    address_file_name_5 = fields.Char()
    lives_in_house_5 = fields.Boolean()
    studies_5 = fields.Selection(
        selection=[
            ('primaria', 'PRIMARY'),
            ('secundaria', 'SECONDARY'),
            ('preparatoria', 'HIGH SCHOOL'),
            ('tsu', 'TSU'),
            ('licenciatura', 'BACHELOR'),
            ('ingenieria', 'ENGINEERING'),
            ('maestria', 'MASTER'),
            ('doctorado', 'DOCTORATE'),
        ],
        string='Studies',
    )
    profession_5 = fields.Char()
    marital_status_5 = fields.Selection(
        selection=[
            ('soltero', 'SINGLE'),
            ('casado_bienes_separados', 'MARRIED SEPARATE PROPERTY'),
            ('casado_sociedad_conyugal', 'MARRIED COMMUNITY PROPERTY'),
        ],
        string='Marital Status',
    )
    phone_number_5 = fields.Char()
    email_5 = fields.Char()
    nationality_5 = fields.Char()
    rfc_5 = fields.Char()
    rfc_file_5 = fields.Binary(attachment=True)
    rfc_file_name_5 = fields.Char()
    curp_5 = fields.Char()
    curp_file_5 = fields.Binary(attachment=True)
    curp_file_name_5 = fields.Char()
    occupation_5 = fields.Char()
    job_position_5 = fields.Char()
    seniority_5 = fields.Char()
    employer_name_5 = fields.Char()
    employer_phone_5 = fields.Char()
    employer_address_5 = fields.Char()
    place_of_birth_5 = fields.Char(string="Place of Birth")
    date_of_birth_5 = fields.Date(string="Date of Birth")
    applies_assets_5 = fields.Char(string="Applies Assets")

    full_name_6 = fields.Char()
    full_name_file_6 = fields.Binary(attachment=True)
    full_name_file_name_6 = fields.Char()
    official_id_6 = fields.Char()
    official_id_file_6 = fields.Binary(attachment=True)
    official_id_file_name_6 = fields.Char()
    address_6 = fields.Text()
    street_name_6 = fields.Char(string="Street")
    external_number_6 = fields.Char(string="Exterior Number")
    number_6 = fields.Char(string="Number")
    internal_number_6 = fields.Char(string="Interior Number")
    suburb_6 = fields.Char(string="Neighborhood / Suburb")
    municipality_6 = fields.Char(string="Municipality / City")
    state_name_6 = fields.Char(string="State")
    zip_code_6 = fields.Char(string="ZIP Code")
    address_file_6 = fields.Binary(attachment=True)
    address_file_name_6 = fields.Char()
    lives_in_house_6 = fields.Boolean()
    studies_6 = fields.Selection(
        selection=[
            ('primaria', 'PRIMARY'),
            ('secundaria', 'SECONDARY'),
            ('preparatoria', 'HIGH SCHOOL'),
            ('tsu', 'TSU'),
            ('licenciatura', 'BACHELOR'),
            ('ingenieria', 'ENGINEERING'),
            ('maestria', 'MASTER'),
            ('doctorado', 'DOCTORATE'),
        ],
        string='Studies',
    )
    profession_6 = fields.Char()
    marital_status_6 = fields.Selection(
        selection=[
            ('soltero', 'SINGLE'),
            ('casado_bienes_separados', 'MARRIED SEPARATE PROPERTY'),
            ('casado_sociedad_conyugal', 'MARRIED COMMUNITY PROPERTY'),
        ],
        string='Marital Status',
    )
    phone_number_6 = fields.Char()
    email_6 = fields.Char()
    nationality_6 = fields.Char()
    rfc_6 = fields.Char()
    rfc_file_6 = fields.Binary(attachment=True)
    rfc_file_name_6 = fields.Char()
    curp_6 = fields.Char()
    curp_file_6 = fields.Binary(attachment=True)
    curp_file_name_6 = fields.Char()
    occupation_6 = fields.Char()
    job_position_6 = fields.Char()
    seniority_6 = fields.Char()
    employer_name_6 = fields.Char()
    employer_phone_6 = fields.Char()
    employer_address_6 = fields.Char()
    place_of_birth_6 = fields.Char(string="Place of Birth")
    date_of_birth_6 = fields.Date(string="Date of Birth")
    applies_assets_6 = fields.Char(string="Applies Assets")

    full_name_7 = fields.Char()
    full_name_file_7 = fields.Binary(attachment=True)
    full_name_file_name_7 = fields.Char()
    official_id_7 = fields.Char()
    official_id_file_7 = fields.Binary(attachment=True)
    official_id_file_name_7 = fields.Char()
    address_7 = fields.Text()
    street_name_7 = fields.Char(string="Street")
    external_number_7 = fields.Char(string="Exterior Number")
    number_7 = fields.Char(string="Number")
    internal_number_7 = fields.Char(string="Interior Number")
    suburb_7 = fields.Char(string="Neighborhood / Suburb")
    municipality_7 = fields.Char(string="Municipality / City")
    state_name_7 = fields.Char(string="State")
    zip_code_7 = fields.Char(string="ZIP Code")
    address_file_7 = fields.Binary(attachment=True)
    address_file_name_7 = fields.Char()
    lives_in_house_7 = fields.Boolean()
    studies_7 = fields.Selection(
        selection=[
            ('primaria', 'PRIMARY'),
            ('secundaria', 'SECONDARY'),
            ('preparatoria', 'HIGH SCHOOL'),
            ('tsu', 'TSU'),
            ('licenciatura', 'BACHELOR'),
            ('ingenieria', 'ENGINEERING'),
            ('maestria', 'MASTER'),
            ('doctorado', 'DOCTORATE'),
        ],
        string='Studies',
    )
    profession_7 = fields.Char()
    marital_status_7 = fields.Selection(
        selection=[
            ('soltero', 'SINGLE'),
            ('casado_bienes_separados', 'MARRIED SEPARATE PROPERTY'),
            ('casado_sociedad_conyugal', 'MARRIED COMMUNITY PROPERTY'),
        ],
        string='Marital Status',
    )
    phone_number_7 = fields.Char()
    email_7 = fields.Char()
    nationality_7 = fields.Char()
    rfc_7 = fields.Char()
    rfc_file_7 = fields.Binary(attachment=True)
    rfc_file_name_7 = fields.Char()
    curp_7 = fields.Char()
    curp_file_7 = fields.Binary(attachment=True)
    curp_file_name_7 = fields.Char()
    occupation_7 = fields.Char()
    job_position_7 = fields.Char()
    seniority_7 = fields.Char()
    employer_name_7 = fields.Char()
    employer_phone_7 = fields.Char()
    employer_address_7 = fields.Char()
    place_of_birth_7 = fields.Char(string="Place of Birth")
    date_of_birth_7 = fields.Date(string="Date of Birth")
    applies_assets_7 = fields.Char(string="Applies Assets")

    full_name_8 = fields.Char()
    full_name_file_8 = fields.Binary(attachment=True)
    full_name_file_name_8 = fields.Char()
    official_id_8 = fields.Char()
    official_id_file_8 = fields.Binary(attachment=True)
    official_id_file_name_8 = fields.Char()
    address_8 = fields.Text()
    street_name_8 = fields.Char(string="Street")
    external_number_8 = fields.Char(string="Exterior Number")
    number_8 = fields.Char(string="Number")
    internal_number_8 = fields.Char(string="Interior Number")
    suburb_8 = fields.Char(string="Neighborhood / Suburb")
    municipality_8 = fields.Char(string="Municipality / City")
    state_name_8 = fields.Char(string="State")
    zip_code_8 = fields.Char(string="ZIP Code")
    address_file_8 = fields.Binary(attachment=True)
    address_file_name_8 = fields.Char()
    lives_in_house_8 = fields.Boolean()
    studies_8 = fields.Selection(
        selection=[
            ('primaria', 'PRIMARY'),
            ('secundaria', 'SECONDARY'),
            ('preparatoria', 'HIGH SCHOOL'),
            ('tsu', 'TSU'),
            ('licenciatura', 'BACHELOR'),
            ('ingenieria', 'ENGINEERING'),
            ('maestria', 'MASTER'),
            ('doctorado', 'DOCTORATE'),
        ],
        string='Studies',
    )
    profession_8 = fields.Char()
    marital_status_8 = fields.Selection(
        selection=[
            ('soltero', 'SINGLE'),
            ('casado_bienes_separados', 'MARRIED SEPARATE PROPERTY'),
            ('casado_sociedad_conyugal', 'MARRIED COMMUNITY PROPERTY'),
        ],
        string='Marital Status',
    )
    phone_number_8 = fields.Char()
    email_8 = fields.Char()
    nationality_8 = fields.Char()
    rfc_8 = fields.Char()
    rfc_file_8 = fields.Binary(attachment=True)
    rfc_file_name_8 = fields.Char()
    curp_8 = fields.Char()
    curp_file_8 = fields.Binary(attachment=True)
    curp_file_name_8 = fields.Char()
    occupation_8 = fields.Char()
    job_position_8 = fields.Char()
    seniority_8 = fields.Char()
    employer_name_8 = fields.Char()
    employer_phone_8 = fields.Char()
    employer_address_8 = fields.Char()
    place_of_birth_8 = fields.Char(string="Place of Birth")
    date_of_birth_8 = fields.Date(string="Date of Birth")
    applies_assets_8 = fields.Char(string="Applies Assets")

    full_name_9 = fields.Char()
    full_name_file_9 = fields.Binary(attachment=True)
    full_name_file_name_9 = fields.Char()
    official_id_9 = fields.Char()
    official_id_file_9 = fields.Binary(attachment=True)
    official_id_file_name_9 = fields.Char()
    address_9 = fields.Text()
    street_name_9 = fields.Char(string="Street")
    external_number_9 = fields.Char(string="Exterior Number")
    number_9 = fields.Char(string="Number")
    internal_number_9 = fields.Char(string="Interior Number")
    suburb_9 = fields.Char(string="Neighborhood / Suburb")
    municipality_9 = fields.Char(string="Municipality / City")
    state_name_9 = fields.Char(string="State")
    zip_code_9 = fields.Char(string="ZIP Code")
    address_file_9 = fields.Binary(attachment=True)
    address_file_name_9 = fields.Char()
    lives_in_house_9 = fields.Boolean()
    studies_9 = fields.Selection(
        selection=[
            ('primaria', 'PRIMARY'),
            ('secundaria', 'SECONDARY'),
            ('preparatoria', 'HIGH SCHOOL'),
            ('tsu', 'TSU'),
            ('licenciatura', 'BACHELOR'),
            ('ingenieria', 'ENGINEERING'),
            ('maestria', 'MASTER'),
            ('doctorado', 'DOCTORATE'),
        ],
        string='Studies',
    )
    profession_9 = fields.Char()
    marital_status_9 = fields.Selection(
        selection=[
            ('soltero', 'SINGLE'),
            ('casado_bienes_separados', 'MARRIED SEPARATE PROPERTY'),
            ('casado_sociedad_conyugal', 'MARRIED COMMUNITY PROPERTY'),
        ],
        string='Marital Status',
    )
    phone_number_9 = fields.Char()
    email_9 = fields.Char()
    nationality_9 = fields.Char()
    rfc_9 = fields.Char()
    rfc_file_9 = fields.Binary(attachment=True)
    rfc_file_name_9 = fields.Char()
    curp_9 = fields.Char()
    curp_file_9 = fields.Binary(attachment=True)
    curp_file_name_9 = fields.Char()
    occupation_9 = fields.Char()
    job_position_9 = fields.Char()
    seniority_9 = fields.Char()
    employer_name_9 = fields.Char()
    employer_phone_9 = fields.Char()
    employer_address_9 = fields.Char()
    place_of_birth_9 = fields.Char(string="Place of Birth")
    date_of_birth_9 = fields.Date(string="Date of Birth")
    applies_assets_9 = fields.Boolean(string="Applies Assets")

    full_name_10 = fields.Char()
    full_name_file_10 = fields.Binary(attachment=True)
    full_name_file_name_10 = fields.Char()
    official_id_10 = fields.Char()
    official_id_file_10 = fields.Binary(attachment=True)
    official_id_file_name_10 = fields.Char()
    address_10 = fields.Text()
    street_name_10 = fields.Char(string="Street")
    external_number_10 = fields.Char(string="Exterior Number")
    number_10 = fields.Char(string="Number")
    internal_number_10 = fields.Char(string="Interior Number")
    suburb_10 = fields.Char(string="Neighborhood / Suburb")
    municipality_10 = fields.Char(string="Municipality / City")
    state_name_10 = fields.Char(string="State")
    zip_code_10 = fields.Char(string="ZIP Code")
    address_file_10 = fields.Binary(attachment=True)
    address_file_name_10 = fields.Char()
    lives_in_house_10 = fields.Boolean()
    studies_10 = fields.Selection(
        selection=[
            ('primaria', 'PRIMARY'),
            ('secundaria', 'SECONDARY'),
            ('preparatoria', 'HIGH SCHOOL'),
            ('tsu', 'TSU'),
            ('licenciatura', 'BACHELOR'),
            ('ingenieria', 'ENGINEERING'),
            ('maestria', 'MASTER'),
            ('doctorado', 'DOCTORATE'),
        ],
        string='Studies',
    )
    profession_10 = fields.Char()
    marital_status_10 = fields.Selection(
        selection=[
            ('soltero', 'SINGLE'),
            ('casado_bienes_separados', 'MARRIED SEPARATE PROPERTY'),
            ('casado_sociedad_conyugal', 'MARRIED COMMUNITY PROPERTY'),
        ],
        string='Marital Status',
    )
    phone_number_10 = fields.Char()
    email_10 = fields.Char()
    nationality_10 = fields.Char()
    rfc_10 = fields.Char()
    rfc_file_10 = fields.Binary(attachment=True)
    rfc_file_name_10 = fields.Char()
    curp_10 = fields.Char()
    curp_file_10 = fields.Binary(attachment=True)
    curp_file_name_10 = fields.Char()
    occupation_10 = fields.Char()
    job_position_10 = fields.Char()
    seniority_10 = fields.Char()
    employer_name_10 = fields.Char()
    employer_phone_10 = fields.Char()
    employer_address_10 = fields.Char()
    place_of_birth_10 = fields.Char(string="Place of Birth")
    date_of_birth_10 = fields.Date(string="Date of Birth")
    applies_assets_10 = fields.Boolean(string="Applies Assets")

    # ========== SPOUSE 1 ==========
    spouse_full_name_1 = fields.Char(string='Spouse Full Name')
    spouse_full_name_file_1 = fields.Binary(string='Spouse Full Name Document', attachment=True)
    spouse_full_name_file_name_1 = fields.Char(string='Spouse Full Name Document Name')
    spouse_official_id_1 = fields.Char(string='Spouse Official ID')
    spouse_official_id_file_1 = fields.Binary(string='Spouse Official ID Document', attachment=True)
    spouse_official_id_file_name_1 = fields.Char(string='Spouse Official ID Document Name (1)')
    spouse_address_1 = fields.Text(string='Spouse Address')
    spouse_address_file_1 = fields.Binary(string='Spouse Address Document', attachment=True)
    spouse_address_file_name_1 = fields.Char(string='Spouse Address Document Name')
    spouse_lives_in_house_1 = fields.Boolean(string='Spouse Lives in House')
    spouse_studies_1 = fields.Char(string='Spouse Studies)')
    spouse_profession_1 = fields.Char(string='Spouse Profession')
    spouse_marital_status_1 = fields.Selection(
        selection=[
            ('soltero', 'SINGLE'),
            ('casado_bienes_separados', 'MARRIED SEPARATE PROPERTY'),
            ('casado_sociedad_conyugal', 'MARRIED COMMUNITY PROPERTY'),
        ],
        string='Spouse Marital Status'
    )
    spouse_phone_number_1 = fields.Char(string='Spouse Phone Number')
    spouse_email_1 = fields.Char(string='Spouse Email')
    spouse_nationality_1 = fields.Char(string='Spouse Nationality')
    spouse_rfc_1 = fields.Char(string='Spouse RFC')
    spouse_rfc_file_1 = fields.Binary(string='Spouse RFC Document', attachment=True)
    spouse_rfc_file_name_1 = fields.Char(string='Spouse RFC Document Name')
    spouse_curp_1 = fields.Char(string='Spouse CURP')
    spouse_curp_file_1 = fields.Binary(string='Spouse CURP Document', attachment=True)
    spouse_curp_file_name_1 = fields.Char(string='Spouse CURP Document Name')
    spouse_occupation_1 = fields.Char(string='Spouse Occupation')
    spouse_job_position_1 = fields.Char(string='Spouse Job Position')
    spouse_seniority_1 = fields.Char(string='Spouse Seniority (1)')
    spouse_employer_name_1 = fields.Char(string='Spouse Employer Name')
    spouse_employer_phone_1 = fields.Char(string='Spouse Employer Phone')
    spouse_employer_address_1 = fields.Char(string='Spouse Employer Address')
    spouse_place_of_birth_1 = fields.Char(string="Place of Birth")
    spouse_date_of_birth_1 = fields.Date(string="Date of Birth")
    spouse_applies_assets_1 = fields.Char(string="Applies Assets")

    spouse_full_name_2 = fields.Char(string='Spouse Full Name')
    spouse_full_name_file_2 = fields.Binary(string='Spouse Full Name Document', attachment=True)
    spouse_full_name_file_name_2 = fields.Char(string='Spouse Full Name Document Name')
    spouse_official_id_2 = fields.Char(string='Spouse Official ID')
    spouse_official_id_file_2 = fields.Binary(string='Spouse Official ID Document', attachment=True)
    spouse_official_id_file_name_2 = fields.Char(string='Spouse Official ID Document Name')
    spouse_address_2 = fields.Text(string='Spouse Address')
    spouse_address_file_2 = fields.Binary(string='Spouse Address Document', attachment=True)
    spouse_address_file_name_2 = fields.Char(string='Spouse Address Document Name')
    spouse_lives_in_house_2 = fields.Boolean(string='Spouse Lives in House')
    spouse_studies_2 = fields.Char(string='Spouse Studies')
    spouse_profession_2 = fields.Char(string='Spouse Profession')
    spouse_marital_status_2 = fields.Selection(
        selection=[
            ('soltero', 'SINGLE'),
            ('casado_bienes_separados', 'MARRIED SEPARATE PROPERTY'),
            ('casado_sociedad_conyugal', 'MARRIED COMMUNITY PROPERTY'),
        ],
        string='Spouse Marital Status'
    )
    spouse_phone_number_2 = fields.Char(string='Spouse Phone Number')
    spouse_email_2 = fields.Char(string='Spouse Email')
    spouse_nationality_2 = fields.Char(string='Spouse Nationality')
    spouse_rfc_2 = fields.Char(string='Spouse RFC')
    spouse_rfc_file_2 = fields.Binary(string='Spouse RFC Document', attachment=True)
    spouse_rfc_file_name_2 = fields.Char(string='Spouse RFC Document Name')
    spouse_curp_2 = fields.Char(string='Spouse CURP')
    spouse_curp_file_2 = fields.Binary(string='Spouse CURP Document', attachment=True)
    spouse_curp_file_name_2 = fields.Char(string='Spouse CURP Document Name')
    spouse_occupation_2 = fields.Char(string='Spouse Occupation')
    spouse_job_position_2 = fields.Char(string='Spouse Job Position')
    spouse_seniority_2 = fields.Char(string='Spouse Seniority')
    spouse_employer_name_2 = fields.Char(string='Spouse Employer Name')
    spouse_employer_phone_2 = fields.Char(string='Spouse Employer Phone')
    spouse_employer_address_2 = fields.Char(string='Spouse Employer Address')
    spouse_place_of_birth_2 = fields.Char(string="Place of Birth")
    spouse_date_of_birth_2 = fields.Date(string="Date of Birth")
    spouse_applies_assets_2 = fields.Boolean(string="Applies Assets")

    spouse_full_name_3 = fields.Char(string='Spouse Full Name')
    spouse_full_name_file_3 = fields.Binary(string='Spouse Full Name Document', attachment=True)
    spouse_full_name_file_name_3 = fields.Char(string='Spouse Full Name Document Name')
    spouse_official_id_3 = fields.Char(string='Spouse Official ID')
    spouse_official_id_file_3 = fields.Binary(string='Spouse Official ID Document', attachment=True)
    spouse_official_id_file_name_3 = fields.Char(string='Spouse Official ID Document Name')
    spouse_address_3 = fields.Text(string='Spouse Address')
    spouse_address_file_3 = fields.Binary(string='Spouse Address Document', attachment=True)
    spouse_address_file_name_3 = fields.Char(string='Spouse Address Document Name')
    spouse_lives_in_house_3 = fields.Boolean(string='Spouse Lives in House')
    spouse_studies_3 = fields.Char(string='Spouse Studies')
    spouse_profession_3 = fields.Char(string='Spouse Profession')
    spouse_marital_status_3 = fields.Selection(
        selection=[
            ('soltero', 'SINGLE'),
            ('casado_bienes_separados', 'MARRIED SEPARATE PROPERTY'),
            ('casado_sociedad_conyugal', 'MARRIED COMMUNITY PROPERTY'),
        ],
        string='Spouse Marital Status'
    )
    spouse_phone_number_3 = fields.Char(string='Spouse Phone Number')
    spouse_email_3 = fields.Char(string='Spouse Email')
    spouse_nationality_3 = fields.Char(string='Spouse Nationality')
    spouse_rfc_3 = fields.Char(string='Spouse RFC')
    spouse_rfc_file_3 = fields.Binary(string='Spouse RFC Document', attachment=True)
    spouse_rfc_file_name_3 = fields.Char(string='Spouse RFC Document Name')
    spouse_curp_3 = fields.Char(string='Spouse CURP')
    spouse_curp_file_3 = fields.Binary(string='Spouse CURP Document', attachment=True)
    spouse_curp_file_name_3 = fields.Char(string='Spouse CURP Document Name')
    spouse_occupation_3 = fields.Char(string='Spouse Occupation')
    spouse_job_position_3 = fields.Char(string='Spouse Job Position')
    spouse_seniority_3 = fields.Char(string='Spouse Seniority')
    spouse_employer_name_3 = fields.Char(string='Spouse Employer Name')
    spouse_employer_phone_3 = fields.Char(string='Spouse Employer Phone')
    spouse_employer_address_3 = fields.Char(string='Spouse Employer Address')
    spouse_place_of_birth_3 = fields.Char(string="Place of Birth")
    spouse_date_of_birth_3 = fields.Date(string="Date of Birth")
    spouse_applies_assets_3 = fields.Boolean(string="Applies Assets")

    spouse_full_name_4 = fields.Char(string='Spouse Full Name')
    spouse_full_name_file_4 = fields.Binary(string='Spouse Full Name Document', attachment=True)
    spouse_full_name_file_name_4 = fields.Char(string='Spouse Full Name Document Name')
    spouse_official_id_4 = fields.Char(string='Spouse Official ID')
    spouse_official_id_file_4 = fields.Binary(string='Spouse Official ID Document', attachment=True)
    spouse_official_id_file_name_4 = fields.Char(string='Spouse Official ID Document Name')
    spouse_address_4 = fields.Text(string='Spouse Address')
    spouse_address_file_4 = fields.Binary(string='Spouse Address Document', attachment=True)
    spouse_address_file_name_4 = fields.Char(string='Spouse Address Document Name')
    spouse_lives_in_house_4 = fields.Boolean(string='Spouse Lives in House')
    spouse_studies_4 = fields.Char(string='Spouse Studies')
    spouse_profession_4 = fields.Char(string='Spouse Profession')
    spouse_marital_status_4 = fields.Selection(
        selection=[
            ('soltero', 'SINGLE'),
            ('casado_bienes_separados', 'MARRIED SEPARATE PROPERTY'),
            ('casado_sociedad_conyugal', 'MARRIED COMMUNITY PROPERTY'),
        ],
        string='Spouse Marital Status'
    )
    spouse_phone_number_4 = fields.Char(string='Spouse Phone Number')
    spouse_email_4 = fields.Char(string='Spouse Email')
    spouse_nationality_4 = fields.Char(string='Spouse Nationality')
    spouse_rfc_4 = fields.Char(string='Spouse RFC')
    spouse_rfc_file_4 = fields.Binary(string='Spouse RFC Document', attachment=True)
    spouse_rfc_file_name_4 = fields.Char(string='Spouse RFC Document Name')
    spouse_curp_4 = fields.Char(string='Spouse CURP')
    spouse_curp_file_4 = fields.Binary(string='Spouse CURP Document', attachment=True)
    spouse_curp_file_name_4 = fields.Char(string='Spouse CURP Document Name')
    spouse_occupation_4 = fields.Char(string='Spouse Occupation')
    spouse_job_position_4 = fields.Char(string='Spouse Job Position')
    spouse_seniority_4 = fields.Char(string='Spouse Seniority')
    spouse_employer_name_4 = fields.Char(string='Spouse Employer Name')
    spouse_employer_phone_4 = fields.Char(string='Spouse Employer Phone')
    spouse_employer_address_4 = fields.Char(string='Spouse Employer Address')
    spouse_place_of_birth_4 = fields.Char(string="Place of Birth")
    spouse_date_of_birth_4 = fields.Date(string="Date of Birth")
    spouse_applies_assets_4 = fields.Boolean(string="Applies Assets")

    spouse_full_name_5 = fields.Char(string='Spouse Full Name')
    spouse_full_name_file_5 = fields.Binary(string='Spouse Full Name Document', attachment=True)
    spouse_full_name_file_name_5 = fields.Char(string='Spouse Full Name Document Name')
    spouse_official_id_5 = fields.Char(string='Spouse Official ID')
    spouse_official_id_file_5 = fields.Binary(string='Spouse Official ID Document', attachment=True)
    spouse_official_id_file_name_5 = fields.Char(string='Spouse Official ID Document Name')
    spouse_address_5 = fields.Text(string='Spouse Address')
    spouse_address_file_5 = fields.Binary(string='Spouse Address Document', attachment=True)
    spouse_address_file_name_5 = fields.Char(string='Spouse Address Document Name')
    spouse_lives_in_house_5 = fields.Boolean(string='Spouse Lives in House')
    spouse_studies_5 = fields.Char(string='Spouse Studies')
    spouse_profession_5 = fields.Char(string='Spouse Profession')
    spouse_marital_status_5 = fields.Selection(
        selection=[
            ('soltero', 'SINGLE'),
            ('casado_bienes_separados', 'MARRIED SEPARATE PROPERTY'),
            ('casado_sociedad_conyugal', 'MARRIED COMMUNITY PROPERTY'),
        ],
        string='Spouse Marital Status'
    )
    spouse_phone_number_5 = fields.Char(string='Spouse Phone Number')
    spouse_email_5 = fields.Char(string='Spouse Email')
    spouse_nationality_5 = fields.Char(string='Spouse Nationality')
    spouse_rfc_5 = fields.Char(string='Spouse RFC')
    spouse_rfc_file_5 = fields.Binary(string='Spouse RFC Document', attachment=True)
    spouse_rfc_file_name_5 = fields.Char(string='Spouse RFC Document Name')
    spouse_curp_5 = fields.Char(string='Spouse CURP')
    spouse_curp_file_5 = fields.Binary(string='Spouse CURP Document', attachment=True)
    spouse_curp_file_name_5 = fields.Char(string='Spouse CURP Document Name')
    spouse_occupation_5 = fields.Char(string='Spouse Occupation')
    spouse_job_position_5 = fields.Char(string='Spouse Job Position')
    spouse_seniority_5 = fields.Char(string='Spouse Seniority')
    spouse_employer_name_5 = fields.Char(string='Spouse Employer Name')
    spouse_employer_phone_5 = fields.Char(string='Spouse Employer Phone')
    spouse_employer_address_5 = fields.Char(string='Spouse Employer Address')
    spouse_place_of_birth_5 = fields.Char(string="Place of Birth")
    spouse_date_of_birth_5 = fields.Date(string="Date of Birth")
    spouse_applies_assets_5 = fields.Boolean(string="Applies Assets")

    spouse_full_name_6 = fields.Char(string='Spouse Full Name')
    spouse_full_name_file_6 = fields.Binary(string='Spouse Full Name Document', attachment=True)
    spouse_full_name_file_name_6 = fields.Char(string='Spouse Full Name Document Name')
    spouse_official_id_6 = fields.Char(string='Spouse Official ID')
    spouse_official_id_file_6 = fields.Binary(string='Spouse Official ID Document', attachment=True)
    spouse_official_id_file_name_6 = fields.Char(string='Spouse Official ID Document Name')
    spouse_address_6 = fields.Text(string='Spouse Address')
    spouse_address_file_6 = fields.Binary(string='Spouse Address Document', attachment=True)
    spouse_address_file_name_6 = fields.Char(string='Spouse Address Document Name')
    spouse_lives_in_house_6 = fields.Boolean(string='Spouse Lives in House')
    spouse_studies_6 = fields.Char(string='Spouse Studies')
    spouse_profession_6 = fields.Char(string='Spouse Profession')
    spouse_marital_status_6 = fields.Selection(
        selection=[
            ('soltero', 'SINGLE'),
            ('casado_bienes_separados', 'MARRIED SEPARATE PROPERTY'),
            ('casado_sociedad_conyugal', 'MARRIED COMMUNITY PROPERTY'),
        ],
        string='Spouse Marital Status'
    )
    spouse_phone_number_6 = fields.Char(string='Spouse Phone Number')
    spouse_email_6 = fields.Char(string='Spouse Email')
    spouse_nationality_6 = fields.Char(string='Spouse Nationality')
    spouse_rfc_6 = fields.Char(string='Spouse RFC')
    spouse_rfc_file_6 = fields.Binary(string='Spouse RFC Document', attachment=True)
    spouse_rfc_file_name_6 = fields.Char(string='Spouse RFC Document Name')
    spouse_curp_6 = fields.Char(string='Spouse CURP')
    spouse_curp_file_6 = fields.Binary(string='Spouse CURP Document', attachment=True)
    spouse_curp_file_name_6 = fields.Char(string='Spouse CURP Document Name')
    spouse_occupation_6 = fields.Char(string='Spouse Occupation')
    spouse_job_position_6 = fields.Char(string='Spouse Job Position')
    spouse_seniority_6 = fields.Char(string='Spouse Seniority')
    spouse_employer_name_6 = fields.Char(string='Spouse Employer Name')
    spouse_employer_phone_6 = fields.Char(string='Spouse Employer Phone')
    spouse_employer_address_6 = fields.Char(string='Spouse Employer Address')
    spouse_place_of_birth_6 = fields.Char(string="Place of Birth")
    spouse_date_of_birth_6 = fields.Date(string="Date of Birth")
    spouse_applies_assets_6 = fields.Boolean(string="Applies Assets")

    spouse_full_name_7 = fields.Char(string='Spouse Full Name')
    spouse_full_name_file_7 = fields.Binary(string='Spouse Full Name Document', attachment=True)
    spouse_full_name_file_name_7 = fields.Char(string='Spouse Full Name Document Name')
    spouse_official_id_7 = fields.Char(string='Spouse Official ID')
    spouse_official_id_file_7 = fields.Binary(string='Spouse Official ID Document', attachment=True)
    spouse_official_id_file_name_7 = fields.Char(string='Spouse Official ID Document Name')
    spouse_address_7 = fields.Text(string='Spouse Address')
    spouse_address_file_7 = fields.Binary(string='Spouse Address Document', attachment=True)
    spouse_address_file_name_7 = fields.Char(string='Spouse Address Document Name')
    spouse_lives_in_house_7 = fields.Boolean(string='Spouse Lives in House')
    spouse_studies_7 = fields.Char(string='Spouse Studies')
    spouse_profession_7 = fields.Char(string='Spouse Profession')
    spouse_marital_status_7 = fields.Selection(
        selection=[
            ('soltero', 'SINGLE'),
            ('casado_bienes_separados', 'MARRIED SEPARATE PROPERTY'),
            ('casado_sociedad_conyugal', 'MARRIED COMMUNITY PROPERTY'),
        ],
        string='Spouse Marital Status'
    )
    spouse_phone_number_7 = fields.Char(string='Spouse Phone Number')
    spouse_email_7 = fields.Char(string='Spouse Email')
    spouse_nationality_7 = fields.Char(string='Spouse Nationality')
    spouse_rfc_7 = fields.Char(string='Spouse RFC')
    spouse_rfc_file_7 = fields.Binary(string='Spouse RFC Document', attachment=True)
    spouse_rfc_file_name_7 = fields.Char(string='Spouse RFC Document Name')
    spouse_curp_7 = fields.Char(string='Spouse CURP')
    spouse_curp_file_7 = fields.Binary(string='Spouse CURP Document', attachment=True)
    spouse_curp_file_name_7 = fields.Char(string='Spouse CURP Document Name')
    spouse_occupation_7 = fields.Char(string='Spouse Occupation')
    spouse_job_position_7 = fields.Char(string='Spouse Job Position')
    spouse_seniority_7 = fields.Char(string='Spouse Seniority')
    spouse_employer_name_7 = fields.Char(string='Spouse Employer Name')
    spouse_employer_phone_7 = fields.Char(string='Spouse Employer Phone')
    spouse_employer_address_7 = fields.Char(string='Spouse Employer Address')
    spouse_place_of_birth_7 = fields.Char(string="Place of Birth")
    spouse_date_of_birth_7 = fields.Date(string="Date of Birth")
    spouse_applies_assets_7 = fields.Boolean(string="Applies Assets")

    spouse_full_name_8 = fields.Char(string='Spouse Full Name')
    spouse_full_name_file_8 = fields.Binary(string='Spouse Full Name Document', attachment=True)
    spouse_full_name_file_name_8 = fields.Char(string='Spouse Full Name Document Name')
    spouse_official_id_8 = fields.Char(string='Spouse Official ID')
    spouse_official_id_file_8 = fields.Binary(string='Spouse Official ID Document', attachment=True)
    spouse_official_id_file_name_8 = fields.Char(string='Spouse Official ID Document Name')
    spouse_address_8 = fields.Text(string='Spouse Address')
    spouse_address_file_8 = fields.Binary(string='Spouse Address Document', attachment=True)
    spouse_address_file_name_8 = fields.Char(string='Spouse Address Document Name')
    spouse_lives_in_house_8 = fields.Boolean(string='Spouse Lives in House')
    spouse_studies_8 = fields.Char(string='Spouse Studies')
    spouse_profession_8 = fields.Char(string='Spouse Profession')
    spouse_marital_status_8 = fields.Selection(
        selection=[
            ('soltero', 'SINGLE'),
            ('casado_bienes_separados', 'MARRIED SEPARATE PROPERTY'),
            ('casado_sociedad_conyugal', 'MARRIED COMMUNITY PROPERTY'),
        ],
        string='Spouse Marital Status'
    )
    spouse_phone_number_8 = fields.Char(string='Spouse Phone Number')
    spouse_email_8 = fields.Char(string='Spouse Email')
    spouse_nationality_8 = fields.Char(string='Spouse Nationality')
    spouse_rfc_8 = fields.Char(string='Spouse RFC')
    spouse_rfc_file_8 = fields.Binary(string='Spouse RFC Document', attachment=True)
    spouse_rfc_file_name_8 = fields.Char(string='Spouse RFC Document Name')
    spouse_curp_8 = fields.Char(string='Spouse CURP')
    spouse_curp_file_8 = fields.Binary(string='Spouse CURP Document', attachment=True)
    spouse_curp_file_name_8 = fields.Char(string='Spouse CURP Document Name')
    spouse_occupation_8 = fields.Char(string='Spouse Occupation')
    spouse_job_position_8 = fields.Char(string='Spouse Job Position')
    spouse_seniority_8 = fields.Char(string='Spouse Seniority')
    spouse_employer_name_8 = fields.Char(string='Spouse Employer Name')
    spouse_employer_phone_8 = fields.Char(string='Spouse Employer Phone')
    spouse_employer_address_8 = fields.Char(string='Spouse Employer Address')
    spouse_place_of_birth_8 = fields.Char(string="Place of Birth")
    spouse_date_of_birth_8 = fields.Date(string="Date of Birth")
    spouse_applies_assets_8 = fields.Boolean(string="Applies Assets")

    spouse_full_name_9 = fields.Char(string='Spouse Full Name')
    spouse_full_name_file_9 = fields.Binary(string='Spouse Full Name Document', attachment=True)
    spouse_full_name_file_name_9 = fields.Char(string='Spouse Full Name Document Name')
    spouse_official_id_9 = fields.Char(string='Spouse Official ID')
    spouse_official_id_file_9 = fields.Binary(string='Spouse Official ID Document', attachment=True)
    spouse_official_id_file_name_9 = fields.Char(string='Spouse Official ID Document Name')
    spouse_address_9 = fields.Text(string='Spouse Address')
    spouse_address_file_9 = fields.Binary(string='Spouse Address Document', attachment=True)
    spouse_address_file_name_9 = fields.Char(string='Spouse Address Document Name')
    spouse_lives_in_house_9 = fields.Boolean(string='Spouse Lives in House')
    spouse_studies_9 = fields.Char(string='Spouse Studies')
    spouse_profession_9 = fields.Char(string='Spouse Profession')
    spouse_marital_status_9 = fields.Selection(
        selection=[
            ('soltero', 'SINGLE'),
            ('casado_bienes_separados', 'MARRIED SEPARATE PROPERTY'),
            ('casado_sociedad_conyugal', 'MARRIED COMMUNITY PROPERTY'),
        ],
        string='Spouse Marital Status'
    )
    spouse_phone_number_9 = fields.Char(string='Spouse Phone Number')
    spouse_email_9 = fields.Char(string='Spouse Email')
    spouse_nationality_9 = fields.Char(string='Spouse Nationality')
    spouse_rfc_9 = fields.Char(string='Spouse RFC')
    spouse_rfc_file_9 = fields.Binary(string='Spouse RFC Document', attachment=True)
    spouse_rfc_file_name_9 = fields.Char(string='Spouse RFC Document Name')
    spouse_curp_9 = fields.Char(string='Spouse CURP')
    spouse_curp_file_9 = fields.Binary(string='Spouse CURP Document', attachment=True)
    spouse_curp_file_name_9 = fields.Char(string='Spouse CURP Document Name')
    spouse_occupation_9 = fields.Char(string='Spouse Occupation')
    spouse_job_position_9 = fields.Char(string='Spouse Job Position')
    spouse_seniority_9 = fields.Char(string='Spouse Seniority')
    spouse_employer_name_9 = fields.Char(string='Spouse Employer Name')
    spouse_employer_phone_9 = fields.Char(string='Spouse Employer Phone')
    spouse_employer_address_9 = fields.Char(string='Spouse Employer Address')
    spouse_place_of_birth_9 = fields.Char(string="Place of Birth")
    spouse_date_of_birth_9 = fields.Date(string="Date of Birth")
    spouse_applies_assets_9 = fields.Boolean(string="Applies Assets")

    spouse_full_name_10 = fields.Char(string='Spouse Full Name')
    spouse_full_name_file_10 = fields.Binary(string='Spouse Full Name Document', attachment=True)
    spouse_full_name_file_name_10 = fields.Char(string='Spouse Full Name Document Name')
    spouse_official_id_10 = fields.Char(string='Spouse Official ID')
    spouse_official_id_file_10 = fields.Binary(string='Spouse Official ID Document', attachment=True)
    spouse_official_id_file_name_10 = fields.Char(string='Spouse Official ID Document Name')
    spouse_address_10 = fields.Text(string='Spouse Address')
    spouse_address_file_10 = fields.Binary(string='Spouse Address Document', attachment=True)
    spouse_address_file_name_10 = fields.Char(string='Spouse Address Document Name')
    spouse_lives_in_house_10 = fields.Boolean(string='Spouse Lives in House')
    spouse_studies_10 = fields.Char(string='Spouse Studies')
    spouse_profession_10 = fields.Char(string='Spouse Profession')
    spouse_marital_status_10 = fields.Selection(
        selection=[
            ('soltero', 'SINGLE'),
            ('casado_bienes_separados', 'MARRIED SEPARATE PROPERTY'),
            ('casado_sociedad_conyugal', 'MARRIED COMMUNITY PROPERTY'),
        ],
        string='Spouse Marital Status'
    )
    spouse_phone_number_10 = fields.Char(string='Spouse Phone Number')
    spouse_email_10 = fields.Char(string='Spouse Email')
    spouse_nationality_10 = fields.Char(string='Spouse Nationality')
    spouse_rfc_10 = fields.Char(string='Spouse RFC')
    spouse_rfc_file_10 = fields.Binary(string='Spouse RFC Document', attachment=True)
    spouse_rfc_file_name_10 = fields.Char(string='Spouse RFC Document Name')
    spouse_curp_10 = fields.Char(string='Spouse CURP')
    spouse_curp_file_10 = fields.Binary(string='Spouse CURP Document', attachment=True)
    spouse_curp_file_name_10 = fields.Char(string='Spouse CURP Document Name')
    spouse_occupation_10 = fields.Char(string='Spouse Occupation')
    spouse_job_position_10 = fields.Char(string='Spouse Job Position')
    spouse_seniority_10 = fields.Char(string='Spouse Seniority')
    spouse_employer_name_10 = fields.Char(string='Spouse Employer Name')
    spouse_employer_phone_10 = fields.Char(string='Spouse Employer Phone')
    spouse_employer_address_10 = fields.Char(string='Spouse Employer Address')
    spouse_place_of_birth_10 = fields.Char(string="Place of Birth")
    spouse_date_of_birth_10 = fields.Date(string="Date of Birth")
    spouse_applies_assets_10 = fields.Boolean(string="Applies Assets")

    stockholder_full_name_1 = fields.Char(string="Full Name")
    stockholder_full_name_file_1 = fields.Binary(string="Full Name Attachment", attachment=True)
    stockholder_full_name_file_name_1 = fields.Char(string="Full Name File Name")
    stockholder_address_1 = fields.Text(string="Address")
    stockholder_address_file_1 = fields.Binary(string="Address Attachment", attachment=True)
    stockholder_address_file_name_1 = fields.Char(string="Address File Name")
    stockholder_lives_in_house_1 = fields.Boolean(string="Lives in House")
    stockholder_studies_1 = fields.Selection(
        selection=[
            ('primaria', 'PRIMARY'),
            ('secundaria', 'SECONDARY'),
            ('preparatoria', 'HIGH SCHOOL'),
            ('tsu', 'TSU'),
            ('licenciatura', 'BACHELOR'),
            ('ingenieria', 'ENGINEERING'),
            ('maestria', 'MASTER'),
            ('doctorado', 'DOCTORATE'),
        ],
        string='Studies',
    )
    stockholder_profession_1 = fields.Char(string="Profession")
    stockholder_marital_status_1 = fields.Selection(
        selection=[
            ('soltero', 'SINGLE'),
            ('casado_bienes_separados', 'MARRIED SEPARATE PROPERTY'),
            ('casado_sociedad_conyugal', 'MARRIED COMMUNITY PROPERTY'),
        ],
        string="Marital Status",
    )
    stockholder_phone_number_1 = fields.Char(string="Phone Number")
    stockholder_email_1 = fields.Char(string="Email")
    stockholder_nationality_1 = fields.Char(string="Nationality")
    stockholder_rfc_1 = fields.Char(string="RFC")
    stockholder_rfc_file_1 = fields.Binary(string="RFC Attachment", attachment=True)
    stockholder_rfc_file_name_1 = fields.Char(string="RFC File Name")
    stockholder_curp_1 = fields.Char(string="CURP")
    stockholder_curp_file_1 = fields.Binary(string="CURP Attachment", attachment=True)
    stockholder_curp_file_name_1 = fields.Char(string="CURP File Name")
    stockholder_occupation_1 = fields.Char(string="Occupation")
    stockholder_job_position_1 = fields.Char(string="Job Position")
    stockholder_seniority_1 = fields.Char(string="Seniority")
    stockholder_employer_name_1 = fields.Char(string="Employer Name")
    stockholder_employer_phone_1 = fields.Char(string="Employer Phone")
    stockholder_employer_address_1 = fields.Char(string="Employer Address")
    stockholder_applies_assets_1 = fields.Char(string="Applies Assets")
    stockholder_shares_percentage_1 = fields.Char(string="Shares Percentage")

    stockholder_full_name_2 = fields.Char(string="Full Name")
    stockholder_full_name_file_2 = fields.Binary(string="Full Name Attachment", attachment=True)
    stockholder_full_name_file_name_2 = fields.Char(string="Full Name File Name")
    stockholder_address_2 = fields.Text(string="Address")
    stockholder_address_file_2 = fields.Binary(string="Address Attachment", attachment=True)
    stockholder_address_file_name_2 = fields.Char(string="Address File Name")
    stockholder_lives_in_house_2 = fields.Boolean(string="Lives in House")
    stockholder_studies_2 = fields.Selection(
        selection=[
            ('primaria', 'PRIMARY'),
            ('secundaria', 'SECONDARY'),
            ('preparatoria', 'HIGH SCHOOL'),
            ('tsu', 'TSU'),
            ('licenciatura', 'BACHELOR'),
            ('ingenieria', 'ENGINEERING'),
            ('maestria', 'MASTER'),
            ('doctorado', 'DOCTORATE'),
        ],
        string='Studies',
    )
    stockholder_profession_2 = fields.Char(string="Profession")
    stockholder_marital_status_2 = fields.Selection(
        selection=[
            ('soltero', 'SINGLE'),
            ('casado_bienes_separados', 'MARRIED SEPARATE PROPERTY'),
            ('casado_sociedad_conyugal', 'MARRIED COMMUNITY PROPERTY'),
        ],
        string="Marital Status",
    )
    stockholder_phone_number_2 = fields.Char(string="Phone Number")
    stockholder_email_2 = fields.Char(string="Email")
    stockholder_nationality_2 = fields.Char(string="Nationality")
    stockholder_rfc_2 = fields.Char(string="RFC")
    stockholder_rfc_file_2 = fields.Binary(string="RFC Attachment", attachment=True)
    stockholder_rfc_file_name_2 = fields.Char(string="RFC File Name")
    stockholder_curp_2 = fields.Char(string="CURP")
    stockholder_curp_file_2 = fields.Binary(string="CURP Attachment", attachment=True)
    stockholder_curp_file_name_2 = fields.Char(string="CURP File Name")
    stockholder_occupation_2 = fields.Char(string="Occupation")
    stockholder_job_position_2 = fields.Char(string="Job Position")
    stockholder_seniority_2 = fields.Char(string="Seniority")
    stockholder_employer_name_2 = fields.Char(string="Employer Name")
    stockholder_employer_phone_2 = fields.Char(string="Employer Phone")
    stockholder_employer_address_2 = fields.Char(string="Employer Address")
    stockholder_applies_assets_2 = fields.Char(string="Applies Assets")
    stockholder_shares_percentage_2 = fields.Char(string="Shares Percentage")

    stockholder_full_name_3 = fields.Char(string="Full Name")
    stockholder_full_name_file_3 = fields.Binary(string="Full Name Attachment", attachment=True)
    stockholder_full_name_file_name_3 = fields.Char(string="Full Name File Name")
    stockholder_address_3 = fields.Text(string="Address")
    stockholder_address_file_3 = fields.Binary(string="Address Attachment", attachment=True)
    stockholder_address_file_name_3 = fields.Char(string="Address File Name")
    stockholder_lives_in_house_3 = fields.Boolean(string="Lives in House")
    stockholder_studies_3 = fields.Selection(
        selection=[
            ('primaria', 'PRIMARY'),
            ('secundaria', 'SECONDARY'),
            ('preparatoria', 'HIGH SCHOOL'),
            ('tsu', 'TSU'),
            ('licenciatura', 'BACHELOR'),
            ('ingenieria', 'ENGINEERING'),
            ('maestria', 'MASTER'),
            ('doctorado', 'DOCTORATE'),
        ],
        string='Studies',
    )
    stockholder_profession_3 = fields.Char(string="Profession")
    stockholder_marital_status_3 = fields.Selection(
        selection=[
            ('soltero', 'SINGLE'),
            ('casado_bienes_separados', 'MARRIED SEPARATE PROPERTY'),
            ('casado_sociedad_conyugal', 'MARRIED COMMUNITY PROPERTY'),
        ],
        string="Marital Status",
    )
    stockholder_phone_number_3 = fields.Char(string="Phone Number")
    stockholder_email_3 = fields.Char(string="Email")
    stockholder_nationality_3 = fields.Char(string="Nationality")
    stockholder_rfc_3 = fields.Char(string="RFC")
    stockholder_rfc_file_3 = fields.Binary(string="RFC Attachment", attachment=True)
    stockholder_rfc_file_name_3 = fields.Char(string="RFC File Name")
    stockholder_curp_3 = fields.Char(string="CURP")
    stockholder_curp_file_3 = fields.Binary(string="CURP Attachment", attachment=True)
    stockholder_curp_file_name_3 = fields.Char(string="CURP File Name")
    stockholder_occupation_3 = fields.Char(string="Occupation")
    stockholder_job_position_3 = fields.Char(string="Job Position")
    stockholder_seniority_3 = fields.Char(string="Seniority")
    stockholder_employer_name_3 = fields.Char(string="Employer Name")
    stockholder_employer_phone_3 = fields.Char(string="Employer Phone")
    stockholder_employer_address_3 = fields.Char(string="Employer Address")
    stockholder_applies_assets_3 = fields.Char(string="Applies Assets")
    stockholder_shares_percentage_3 = fields.Char(string="Shares Percentage")

    stockholder_full_name_4 = fields.Char(string="Full Name")
    stockholder_full_name_file_4 = fields.Binary(string="Full Name Attachment", attachment=True)
    stockholder_full_name_file_name_4 = fields.Char(string="Full Name File Name")
    stockholder_address_4 = fields.Text(string="Address")
    stockholder_address_file_4 = fields.Binary(string="Address Attachment", attachment=True)
    stockholder_address_file_name_4 = fields.Char(string="Address File Name")
    stockholder_lives_in_house_4 = fields.Boolean(string="Lives in House")
    stockholder_studies_4 = fields.Selection(
        selection=[
            ('primaria', 'PRIMARY'),
            ('secundaria', 'SECONDARY'),
            ('preparatoria', 'HIGH SCHOOL'),
            ('tsu', 'TSU'),
            ('licenciatura', 'BACHELOR'),
            ('ingenieria', 'ENGINEERING'),
            ('maestria', 'MASTER'),
            ('doctorado', 'DOCTORATE'),
        ],
        string='Studies',
    )
    stockholder_profession_4 = fields.Char(string="Profession")
    stockholder_marital_status_4 = fields.Selection(
        selection=[
            ('soltero', 'SINGLE'),
            ('casado_bienes_separados', 'MARRIED SEPARATE PROPERTY'),
            ('casado_sociedad_conyugal', 'MARRIED COMMUNITY PROPERTY'),
        ],
        string="Marital Status",
    )
    stockholder_phone_number_4 = fields.Char(string="Phone Number")
    stockholder_email_4 = fields.Char(string="Email")
    stockholder_nationality_4 = fields.Char(string="Nationality")
    stockholder_rfc_4 = fields.Char(string="RFC")
    stockholder_rfc_file_4 = fields.Binary(string="RFC Attachment", attachment=True)
    stockholder_rfc_file_name_4 = fields.Char(string="RFC File Name")
    stockholder_curp_4 = fields.Char(string="CURP")
    stockholder_curp_file_4 = fields.Binary(string="CURP Attachment", attachment=True)
    stockholder_curp_file_name_4 = fields.Char(string="CURP File Name")
    stockholder_occupation_4 = fields.Char(string="Occupation")
    stockholder_job_position_4 = fields.Char(string="Job Position")
    stockholder_seniority_4 = fields.Char(string="Seniority")
    stockholder_employer_name_4 = fields.Char(string="Employer Name")
    stockholder_employer_phone_4 = fields.Char(string="Employer Phone")
    stockholder_employer_address_4 = fields.Char(string="Employer Address")
    stockholder_applies_assets_4 = fields.Char(string="Applies Assets")
    stockholder_shares_percentage_4 = fields.Char(string="Shares Percentage")

    stockholder_full_name_5 = fields.Char(string="Full Name")
    stockholder_full_name_file_5 = fields.Binary(string="Full Name Attachment", attachment=True)
    stockholder_full_name_file_name_5 = fields.Char(string="Full Name File Name")
    stockholder_address_5 = fields.Text(string="Address")
    stockholder_address_file_5 = fields.Binary(string="Address Attachment", attachment=True)
    stockholder_address_file_name_5 = fields.Char(string="Address File Name")
    stockholder_lives_in_house_5 = fields.Boolean(string="Lives in House")
    stockholder_studies_5 = fields.Selection(
        selection=[
            ('primaria', 'PRIMARY'),
            ('secundaria', 'SECONDARY'),
            ('preparatoria', 'HIGH SCHOOL'),
            ('tsu', 'TSU'),
            ('licenciatura', 'BACHELOR'),
            ('ingenieria', 'ENGINEERING'),
            ('maestria', 'MASTER'),
            ('doctorado', 'DOCTORATE'),
        ],
        string='Studies',
    )
    stockholder_profession_5 = fields.Char(string="Profession")
    stockholder_marital_status_5 = fields.Selection(
        selection=[
            ('soltero', 'SINGLE'),
            ('casado_bienes_separados', 'MARRIED SEPARATE PROPERTY'),
            ('casado_sociedad_conyugal', 'MARRIED COMMUNITY PROPERTY'),
        ],
        string="Marital Status",
    )
    stockholder_phone_number_5 = fields.Char(string="Phone Number")
    stockholder_email_5 = fields.Char(string="Email")
    stockholder_nationality_5 = fields.Char(string="Nationality")
    stockholder_rfc_5 = fields.Char(string="RFC")
    stockholder_rfc_file_5 = fields.Binary(string="RFC Attachment", attachment=True)
    stockholder_rfc_file_name_5 = fields.Char(string="RFC File Name")
    stockholder_curp_5 = fields.Char(string="CURP")
    stockholder_curp_file_5 = fields.Binary(string="CURP Attachment", attachment=True)
    stockholder_curp_file_name_5 = fields.Char(string="CURP File Name")
    stockholder_occupation_5 = fields.Char(string="Occupation")
    stockholder_job_position_5 = fields.Char(string="Job Position")
    stockholder_seniority_5 = fields.Char(string="Seniority")
    stockholder_employer_name_5 = fields.Char(string="Employer Name")
    stockholder_employer_phone_5 = fields.Char(string="Employer Phone")
    stockholder_employer_address_5 = fields.Char(string="Employer Address")
    stockholder_applies_assets_5 = fields.Char(string="Applies Assets")
    stockholder_shares_percentage_5 = fields.Char(string="Shares Percentage")

    stockholder_full_name_6 = fields.Char(string="Full Name")
    stockholder_full_name_file_6 = fields.Binary(string="Full Name Attachment", attachment=True)
    stockholder_full_name_file_name_6 = fields.Char(string="Full Name File Name")
    stockholder_address_6 = fields.Text(string="Address")
    stockholder_address_file_6 = fields.Binary(string="Address Attachment", attachment=True)
    stockholder_address_file_name_6 = fields.Char(string="Address File Name")
    stockholder_lives_in_house_6 = fields.Boolean(string="Lives in House")
    stockholder_studies_6 = fields.Selection(
        selection=[
            ('primaria', 'PRIMARY'),
            ('secundaria', 'SECONDARY'),
            ('preparatoria', 'HIGH SCHOOL'),
            ('tsu', 'TSU'),
            ('licenciatura', 'BACHELOR'),
            ('ingenieria', 'ENGINEERING'),
            ('maestria', 'MASTER'),
            ('doctorado', 'DOCTORATE'),
        ],
        string='Studies',
    )
    stockholder_profession_6 = fields.Char(string="Profession")
    stockholder_marital_status_6 = fields.Selection(
        selection=[
            ('soltero', 'SINGLE'),
            ('casado_bienes_separados', 'MARRIED SEPARATE PROPERTY'),
            ('casado_sociedad_conyugal', 'MARRIED COMMUNITY PROPERTY'),
        ],
        string="Marital Status",
    )
    stockholder_phone_number_6 = fields.Char(string="Phone Number")
    stockholder_email_6 = fields.Char(string="Email")
    stockholder_nationality_6 = fields.Char(string="Nationality")
    stockholder_rfc_6 = fields.Char(string="RFC")
    stockholder_rfc_file_6 = fields.Binary(string="RFC Attachment", attachment=True)
    stockholder_rfc_file_name_6 = fields.Char(string="RFC File Name")
    stockholder_curp_6 = fields.Char(string="CURP")
    stockholder_curp_file_6 = fields.Binary(string="CURP Attachment", attachment=True)
    stockholder_curp_file_name_6 = fields.Char(string="CURP File Name")
    stockholder_occupation_6 = fields.Char(string="Occupation")
    stockholder_job_position_6 = fields.Char(string="Job Position")
    stockholder_seniority_6 = fields.Char(string="Seniority")
    stockholder_employer_name_6 = fields.Char(string="Employer Name")
    stockholder_employer_phone_6 = fields.Char(string="Employer Phone")
    stockholder_employer_address_6 = fields.Char(string="Employer Address")
    stockholder_applies_assets_6 = fields.Char(string="Applies Assets")
    stockholder_shares_percentage_6 = fields.Char(string="Shares Percentage")

    stockholder_full_name_7 = fields.Char(string="Full Name")
    stockholder_full_name_file_7 = fields.Binary(string="Full Name Attachment", attachment=True)
    stockholder_full_name_file_name_7 = fields.Char(string="Full Name File Name")
    stockholder_address_7 = fields.Text(string="Address")
    stockholder_address_file_7 = fields.Binary(string="Address Attachment", attachment=True)
    stockholder_address_file_name_7 = fields.Char(string="Address File Name")
    stockholder_lives_in_house_7 = fields.Boolean(string="Lives in House")
    stockholder_studies_7 = fields.Selection(
        selection=[
            ('primaria', 'PRIMARY'),
            ('secundaria', 'SECONDARY'),
            ('preparatoria', 'HIGH SCHOOL'),
            ('tsu', 'TSU'),
            ('licenciatura', 'BACHELOR'),
            ('ingenieria', 'ENGINEERING'),
            ('maestria', 'MASTER'),
            ('doctorado', 'DOCTORATE'),
        ],
        string='Studies',
    )
    stockholder_profession_7 = fields.Char(string="Profession")
    stockholder_marital_status_7 = fields.Selection(
        selection=[
            ('soltero', 'SINGLE'),
            ('casado_bienes_separados', 'MARRIED SEPARATE PROPERTY'),
            ('casado_sociedad_conyugal', 'MARRIED COMMUNITY PROPERTY'),
        ],
        string="Marital Status",
    )
    stockholder_phone_number_7 = fields.Char(string="Phone Number")
    stockholder_email_7 = fields.Char(string="Email")
    stockholder_nationality_7 = fields.Char(string="Nationality")
    stockholder_rfc_7 = fields.Char(string="RFC")
    stockholder_rfc_file_7 = fields.Binary(string="RFC Attachment", attachment=True)
    stockholder_rfc_file_name_7 = fields.Char(string="RFC File Name")
    stockholder_curp_7 = fields.Char(string="CURP")
    stockholder_curp_file_7 = fields.Binary(string="CURP Attachment", attachment=True)
    stockholder_curp_file_name_7 = fields.Char(string="CURP File Name")
    stockholder_occupation_7 = fields.Char(string="Occupation")
    stockholder_job_position_7 = fields.Char(string="Job Position")
    stockholder_seniority_7 = fields.Char(string="Seniority")
    stockholder_employer_name_7 = fields.Char(string="Employer Name")
    stockholder_employer_phone_7 = fields.Char(string="Employer Phone")
    stockholder_employer_address_7 = fields.Char(string="Employer Address")
    stockholder_applies_assets_7 = fields.Char(string="Applies Assets")
    stockholder_shares_percentage_7 = fields.Char(string="Shares Percentage")

    stockholder_full_name_8 = fields.Char(string="Full Name")
    stockholder_full_name_file_8 = fields.Binary(string="Full Name Attachment", attachment=True)
    stockholder_full_name_file_name_8 = fields.Char(string="Full Name File Name")
    stockholder_address_8 = fields.Text(string="Address")
    stockholder_address_file_8 = fields.Binary(string="Address Attachment", attachment=True)
    stockholder_address_file_name_8 = fields.Char(string="Address File Name")
    stockholder_lives_in_house_8 = fields.Boolean(string="Lives in House")
    stockholder_studies_8 = fields.Selection(
        selection=[
            ('primaria', 'PRIMARY'),
            ('secundaria', 'SECONDARY'),
            ('preparatoria', 'HIGH SCHOOL'),
            ('tsu', 'TSU'),
            ('licenciatura', 'BACHELOR'),
            ('ingenieria', 'ENGINEERING'),
            ('maestria', 'MASTER'),
            ('doctorado', 'DOCTORATE'),
        ],
        string='Studies',
    )
    stockholder_profession_8 = fields.Char(string="Profession")
    stockholder_marital_status_8 = fields.Selection(
        selection=[
            ('soltero', 'SINGLE'),
            ('casado_bienes_separados', 'MARRIED SEPARATE PROPERTY'),
            ('casado_sociedad_conyugal', 'MARRIED COMMUNITY PROPERTY'),
        ],
        string="Marital Status",
    )
    stockholder_phone_number_8 = fields.Char(string="Phone Number")
    stockholder_email_8 = fields.Char(string="Email")
    stockholder_nationality_8 = fields.Char(string="Nationality")
    stockholder_rfc_8 = fields.Char(string="RFC")
    stockholder_rfc_file_8 = fields.Binary(string="RFC Attachment", attachment=True)
    stockholder_rfc_file_name_8 = fields.Char(string="RFC File Name")
    stockholder_curp_8 = fields.Char(string="CURP")
    stockholder_curp_file_8 = fields.Binary(string="CURP Attachment", attachment=True)
    stockholder_curp_file_name_8 = fields.Char(string="CURP File Name")
    stockholder_occupation_8 = fields.Char(string="Occupation")
    stockholder_job_position_8 = fields.Char(string="Job Position")
    stockholder_seniority_8 = fields.Char(string="Seniority")
    stockholder_employer_name_8 = fields.Char(string="Employer Name")
    stockholder_employer_phone_8 = fields.Char(string="Employer Phone")
    stockholder_employer_address_8 = fields.Char(string="Employer Address")
    stockholder_applies_assets_8 = fields.Char(string="Applies Assets")
    stockholder_shares_percentage_8 = fields.Char(string="Shares Percentage")

    stockholder_full_name_9 = fields.Char(string="Full Name")
    stockholder_full_name_file_9 = fields.Binary(string="Full Name Attachment", attachment=True)
    stockholder_full_name_file_name_9 = fields.Char(string="Full Name File Name")
    stockholder_address_9 = fields.Text(string="Address")
    stockholder_address_file_9 = fields.Binary(string="Address Attachment", attachment=True)
    stockholder_address_file_name_9 = fields.Char(string="Address File Name")
    stockholder_lives_in_house_9 = fields.Boolean(string="Lives in House")
    stockholder_studies_9 =fields.Selection(
        selection=[
            ('primaria', 'PRIMARY'),
            ('secundaria', 'SECONDARY'),
            ('preparatoria', 'HIGH SCHOOL'),
            ('tsu', 'TSU'),
            ('licenciatura', 'BACHELOR'),
            ('ingenieria', 'ENGINEERING'),
            ('maestria', 'MASTER'),
            ('doctorado', 'DOCTORATE'),
        ],
        string='Studies',
    )
    stockholder_profession_9 = fields.Char(string="Profession")
    stockholder_marital_status_9 = fields.Selection(
        selection=[
            ('soltero', 'SINGLE'),
            ('casado_bienes_separados', 'MARRIED SEPARATE PROPERTY'),
            ('casado_sociedad_conyugal', 'MARRIED COMMUNITY PROPERTY'),
        ],
        string="Marital Status",
    )
    stockholder_phone_number_9 = fields.Char(string="Phone Number")
    stockholder_email_9 = fields.Char(string="Email")
    stockholder_nationality_9 = fields.Char(string="Nationality")
    stockholder_rfc_9 = fields.Char(string="RFC")
    stockholder_rfc_file_9 = fields.Binary(string="RFC Attachment", attachment=True)
    stockholder_rfc_file_name_9 = fields.Char(string="RFC File Name")
    stockholder_curp_9 = fields.Char(string="CURP")
    stockholder_curp_file_9 = fields.Binary(string="CURP Attachment", attachment=True)
    stockholder_curp_file_name_9 = fields.Char(string="CURP File Name")
    stockholder_occupation_9 = fields.Char(string="Occupation")
    stockholder_job_position_9 = fields.Char(string="Job Position")
    stockholder_seniority_9 = fields.Char(string="Seniority")
    stockholder_employer_name_9 = fields.Char(string="Employer Name")
    stockholder_employer_phone_9 = fields.Char(string="Employer Phone")
    stockholder_employer_address_9 = fields.Char(string="Employer Address")
    stockholder_applies_assets_9 = fields.Char(string="Applies Assets")
    stockholder_shares_percentage_9 = fields.Char(string="Shares Percentage")

    stockholder_full_name_10 = fields.Char(string="Full Name")
    stockholder_full_name_file_10 = fields.Binary(string="Full Name Attachment", attachment=True)
    stockholder_full_name_file_name_10 = fields.Char(string="Full Name File Name")
    stockholder_address_10 = fields.Text(string="Address")
    stockholder_address_file_10 = fields.Binary(string="Address Attachment", attachment=True)
    stockholder_address_file_name_10 = fields.Char(string="Address File Name")
    stockholder_lives_in_house_10 = fields.Boolean(string="Lives in House")
    stockholder_studies_10 = fields.Char(string="Studies")
    stockholder_profession_10 = fields.Char(string="Profession")
    stockholder_marital_status_10 = fields.Selection(
        selection=[
            ('soltero', 'SINGLE'),
            ('casado_bienes_separados', 'MARRIED SEPARATE PROPERTY'),
            ('casado_sociedad_conyugal', 'MARRIED COMMUNITY PROPERTY'),
        ],
        string="Marital Status",
    )
    stockholder_phone_number_10 = fields.Char(string="Phone Number")
    stockholder_email_10 = fields.Char(string="Email")
    stockholder_nationality_10 = fields.Char(string="Nationality")
    stockholder_rfc_10 = fields.Char(string="RFC")
    stockholder_rfc_file_10 = fields.Binary(string="RFC Attachment", attachment=True)
    stockholder_rfc_file_name_10 = fields.Char(string="RFC File Name")
    stockholder_curp_10 = fields.Char(string="CURP")
    stockholder_curp_file_10 = fields.Binary(string="CURP Attachment", attachment=True)
    stockholder_curp_file_name_10 = fields.Char(string="CURP File Name")
    stockholder_occupation_10 = fields.Char(string="Occupation")
    stockholder_job_position_10 = fields.Char(string="Job Position")
    stockholder_seniority_10 = fields.Char(string="Seniority")
    stockholder_employer_name_10 = fields.Char(string="Employer Name")
    stockholder_employer_phone_10 = fields.Char(string="Employer Phone")
    stockholder_employer_address_10 = fields.Char(string="Employer Address")
    stockholder_applies_assets_10 = fields.Char(string="Applies Assets")
    stockholder_shares_percentage_10 = fields.Char(string="Shares Percentage")

    stockholders_visible = fields.Integer(string="Visible Stockholders", default=1)
    capital_gain = fields.Char('Capital Gains')

    business_turn = fields.Char(string="Business Turn")
    activity = fields.Char(string="Activity")
    folio = fields.Char(string="Folio")
    registration_date = fields.Char(string="Registration Date")
    notary_number = fields.Char(string="Notary Number")
    notary_name = fields.Char(string="Notary Name")
    registration_city = fields.Char(string="Registration City")
    corporate_purpose = fields.Char(string="Corporate Purpose")
    commercial_folio = fields.Char(string="Commercial Folio")
    deed_Incorporation = fields.Char(string="Deed of Incorporation")

    stockholders_street_name_1 = fields.Char(string='Street Name')
    stockholders_external_number_1 = fields.Char(string='Exterior Number')
    stockholders_number_1 = fields.Char(string='Number')
    stockholders_internal_number_1 = fields.Char(string='Interior Number')
    stockholders_suburb_1 = fields.Char(string='Neighborhood / Suburb')
    stockholders_municipality_1 = fields.Char(string='Municipality / City')
    stockholders_state_name_1 = fields.Char(string='State')
    stockholders_zip_code_1 = fields.Char(string='ZIP Code')
    stockholders_lives_in_house_1 = fields.Boolean(string='Lives In House')
    stockholders_studies_1 = fields.Selection(
        selection=[
            ('primaria', 'PRIMARY'),
            ('secundaria', 'SECONDARY'),
            ('preparatoria', 'HIGH SCHOOL'),
            ('tsu', 'TSU'),
            ('licenciatura', 'BACHELOR'),
            ('ingenieria', 'ENGINEERING'),
            ('maestria', 'MASTER'),
            ('doctorado', 'DOCTORATE'),
        ],
        string='Studies',
    )
    stockholders_marital_status_1 = fields.Char(string='Marital Status')
    stockholders_place_of_birth_1 = fields.Char(string='Place Of Birth')
    stockholders_date_of_birth_1 = fields.Date(string='Date Of Birth')
    stockholders_employer_address_1 = fields.Char(string='Employer Address')
    stockholders_occupation_1 = fields.Char(string='Occupation')
    stockholders_job_position_1 = fields.Char(string='Job Position')
    stockholders_seniority_1 = fields.Char(string='Seniority')
    stockholders_employer_name_1 = fields.Char(string='Employer Name')
    stockholders_employer_phone_1 = fields.Char(string='Employer Phone')
    stockholders_address_file_1 = fields.Binary(string='Address File', attachment=True)
    stockholders_address_file_name_1 = fields.Char(string='Address File Name')

    stockholders_street_name_2 = fields.Char(string='Street Name')
    stockholders_external_number_2 = fields.Char(string='Exterior Number')
    stockholders_number_2 = fields.Char(string='Number')
    stockholders_internal_number_2 = fields.Char(string='Interior Number')
    stockholders_suburb_2 = fields.Char(string='Neighborhood / Suburb')
    stockholders_municipality_2 = fields.Char(string='Municipality / City')
    stockholders_state_name_2 = fields.Char(string='State')
    stockholders_zip_code_2 = fields.Char(string='ZIP Code')
    stockholders_lives_in_house_2 = fields.Boolean(string='Lives In House')
    stockholders_studies_2 = fields.Selection(
        selection=[
            ('primaria', 'PRIMARY'),
            ('secundaria', 'SECONDARY'),
            ('preparatoria', 'HIGH SCHOOL'),
            ('tsu', 'TSU'),
            ('licenciatura', 'BACHELOR'),
            ('ingenieria', 'ENGINEERING'),
            ('maestria', 'MASTER'),
            ('doctorado', 'DOCTORATE'),
        ],
        string='Studies',
    )
    stockholders_marital_status_2 = fields.Char(string='Marital Status')
    stockholders_place_of_birth_2 = fields.Char(string='Place Of Birth')
    stockholders_date_of_birth_2 = fields.Date(string='Date Of Birth')
    stockholders_employer_address_2 = fields.Char(string='Employer Address')
    stockholders_occupation_2 = fields.Char(string='Occupation')
    stockholders_job_position_2 = fields.Char(string='Job Position')
    stockholders_seniority_2 = fields.Char(string='Seniority')
    stockholders_employer_name_2 = fields.Char(string='Employer Name')
    stockholders_employer_phone_2 = fields.Char(string='Employer Phone')
    stockholders_address_file_2 = fields.Binary(string='Address File', attachment=True)
    stockholders_address_file_name_2 = fields.Char(string='Address File Name')

    stockholders_street_name_3 = fields.Char(string='Street Name')
    stockholders_external_number_3 = fields.Char(string='Exterior Number')
    stockholders_number_3 = fields.Char(string='Number')
    stockholders_internal_number_3 = fields.Char(string='Interior Number')
    stockholders_suburb_3 = fields.Char(string='Neighborhood / Suburb')
    stockholders_municipality_3 = fields.Char(string='Municipality / City')
    stockholders_state_name_3 = fields.Char(string='State')
    stockholders_zip_code_3 = fields.Char(string='ZIP Code')
    stockholders_lives_in_house_3 = fields.Boolean(string='Lives In House')
    stockholders_studies_3 = fields.Selection(
        selection=[
            ('primaria', 'PRIMARY'),
            ('secundaria', 'SECONDARY'),
            ('preparatoria', 'HIGH SCHOOL'),
            ('tsu', 'TSU'),
            ('licenciatura', 'BACHELOR'),
            ('ingenieria', 'ENGINEERING'),
            ('maestria', 'MASTER'),
            ('doctorado', 'DOCTORATE'),
        ],
        string='Studies',
    )
    stockholders_marital_status_3 = fields.Char(string='Marital Status')
    stockholders_place_of_birth_3 = fields.Char(string='Place Of Birth')
    stockholders_date_of_birth_3 = fields.Date(string='Date Of Birth')
    stockholders_employer_address_3 = fields.Char(string='Employer Address')
    stockholders_occupation_3 = fields.Char(string='Occupation')
    stockholders_job_position_3 = fields.Char(string='Job Position')
    stockholders_seniority_3 = fields.Char(string='Seniority')
    stockholders_employer_name_3 = fields.Char(string='Employer Name')
    stockholders_employer_phone_3 = fields.Char(string='Employer Phone')
    stockholders_address_file_3 = fields.Binary(string='Address File', attachment=True)
    stockholders_address_file_name_3 = fields.Char(string='Address File Name')

    stockholders_street_name_4 = fields.Char(string='Street Name')
    stockholders_external_number_4 = fields.Char(string='Exterior Number')
    stockholders_number_4 = fields.Char(string='Number')
    stockholders_internal_number_4 = fields.Char(string='Interior Number')
    stockholders_suburb_4 = fields.Char(string='Neighborhood / Suburb')
    stockholders_municipality_4 = fields.Char(string='Municipality / City')
    stockholders_state_name_4 = fields.Char(string='State')
    stockholders_zip_code_4 = fields.Char(string='ZIP Code')
    stockholders_lives_in_house_4 = fields.Boolean(string='Lives In House')
    stockholders_studies_4 = fields.Selection(
        selection=[
            ('primaria', 'PRIMARY'),
            ('secundaria', 'SECONDARY'),
            ('preparatoria', 'HIGH SCHOOL'),
            ('tsu', 'TSU'),
            ('licenciatura', 'BACHELOR'),
            ('ingenieria', 'ENGINEERING'),
            ('maestria', 'MASTER'),
            ('doctorado', 'DOCTORATE'),
        ],
        string='Studies',
    )
    stockholders_marital_status_4 = fields.Char(string='Marital Status')
    stockholders_place_of_birth_4 = fields.Char(string='Place Of Birth')
    stockholders_date_of_birth_4 = fields.Date(string='Date Of Birth')
    stockholders_employer_address_4 = fields.Char(string='Employer Address')
    stockholders_occupation_4 = fields.Char(string='Occupation')
    stockholders_job_position_4 = fields.Char(string='Job Position')
    stockholders_seniority_4 = fields.Char(string='Seniority')
    stockholders_employer_name_4 = fields.Char(string='Employer Name')
    stockholders_employer_phone_4 = fields.Char(string='Employer Phone')
    stockholders_address_file_4 = fields.Binary(string='Address File', attachment=True)
    stockholders_address_file_name_4 = fields.Char(string='Address File Name')

    stockholders_street_name_5 = fields.Char(string='Street Name')
    stockholders_external_number_5 = fields.Char(string='Exterior Number')
    stockholders_number_5 = fields.Char(string='Number')
    stockholders_internal_number_5 = fields.Char(string='Interior Number')
    stockholders_suburb_5 = fields.Char(string='Neighborhood / Suburb')
    stockholders_municipality_5 = fields.Char(string='Municipality / City')
    stockholders_state_name_5 = fields.Char(string='State')
    stockholders_zip_code_5 = fields.Char(string='ZIP Code')
    stockholders_lives_in_house_5 = fields.Boolean(string='Lives In House')
    stockholders_studies_5 =fields.Selection(
        selection=[
            ('primaria', 'PRIMARY'),
            ('secundaria', 'SECONDARY'),
            ('preparatoria', 'HIGH SCHOOL'),
            ('tsu', 'TSU'),
            ('licenciatura', 'BACHELOR'),
            ('ingenieria', 'ENGINEERING'),
            ('maestria', 'MASTER'),
            ('doctorado', 'DOCTORATE'),
        ],
        string='Studies',
    )
    stockholders_marital_status_5 = fields.Char(string='Marital Status')
    stockholders_place_of_birth_5 = fields.Char(string='Place Of Birth')
    stockholders_date_of_birth_5 = fields.Date(string='Date Of Birth')
    stockholders_employer_address_5 = fields.Char(string='Employer Address')
    stockholders_occupation_5 = fields.Char(string='Occupation')
    stockholders_job_position_5 = fields.Char(string='Job Position')
    stockholders_seniority_5 = fields.Char(string='Seniority')
    stockholders_employer_name_5 = fields.Char(string='Employer Name')
    stockholders_employer_phone_5 = fields.Char(string='Employer Phone')
    stockholders_address_file_5 = fields.Binary(string='Address File', attachment=True)
    stockholders_address_file_name_5 = fields.Char(string='Address File Name')

    stockholders_street_name_6 = fields.Char(string='Street Name')
    stockholders_external_number_6 = fields.Char(string='Exterior Number')
    stockholders_number_6 = fields.Char(string='Number')
    stockholders_internal_number_6 = fields.Char(string='Interior Number')
    stockholders_suburb_6 = fields.Char(string='Neighborhood / Suburb')
    stockholders_municipality_6 = fields.Char(string='Municipality / City')
    stockholders_state_name_6 = fields.Char(string='State')
    stockholders_zip_code_6 = fields.Char(string='ZIP Code')
    stockholders_lives_in_house_6 = fields.Boolean(string='Lives In House')
    stockholders_studies_6 = fields.Selection(
        selection=[
            ('primaria', 'PRIMARY'),
            ('secundaria', 'SECONDARY'),
            ('preparatoria', 'HIGH SCHOOL'),
            ('tsu', 'TSU'),
            ('licenciatura', 'BACHELOR'),
            ('ingenieria', 'ENGINEERING'),
            ('maestria', 'MASTER'),
            ('doctorado', 'DOCTORATE'),
        ],
        string='Studies',
    )
    stockholders_marital_status_6 = fields.Char(string='Marital Status')
    stockholders_place_of_birth_6 = fields.Char(string='Place Of Birth')
    stockholders_date_of_birth_6 = fields.Date(string='Date Of Birth')
    stockholders_employer_address_6 = fields.Char(string='Employer Address')
    stockholders_occupation_6 = fields.Char(string='Occupation')
    stockholders_job_position_6 = fields.Char(string='Job Position')
    stockholders_seniority_6 = fields.Char(string='Seniority')
    stockholders_employer_name_6 = fields.Char(string='Employer Name')
    stockholders_employer_phone_6 = fields.Char(string='Employer Phone')
    stockholders_address_file_6 = fields.Binary(string='Address File', attachment=True)
    stockholders_address_file_name_6 = fields.Char(string='Address File Name')

    stockholders_street_name_7 = fields.Char(string='Street Name')
    stockholders_external_number_7 = fields.Char(string='Exterior Number')
    stockholders_number_7 = fields.Char(string='Number')
    stockholders_internal_number_7 = fields.Char(string='Interior Number')
    stockholders_suburb_7 = fields.Char(string='Neighborhood / Suburb')
    stockholders_municipality_7 = fields.Char(string='Municipality / City')
    stockholders_state_name_7 = fields.Char(string='State')
    stockholders_zip_code_7 = fields.Char(string='ZIP Code')
    stockholders_lives_in_house_7 = fields.Boolean(string='Lives In House')
    stockholders_studies_7 = fields.Selection(
        selection=[
            ('primaria', 'PRIMARY'),
            ('secundaria', 'SECONDARY'),
            ('preparatoria', 'HIGH SCHOOL'),
            ('tsu', 'TSU'),
            ('licenciatura', 'BACHELOR'),
            ('ingenieria', 'ENGINEERING'),
            ('maestria', 'MASTER'),
            ('doctorado', 'DOCTORATE'),
        ],
        string='Studies',
    )
    stockholders_marital_status_7 = fields.Char(string='Marital Status')
    stockholders_place_of_birth_7 = fields.Char(string='Place Of Birth')
    stockholders_date_of_birth_7 = fields.Date(string='Date Of Birth')
    stockholders_employer_address_7 = fields.Char(string='Employer Address')
    stockholders_occupation_7 = fields.Char(string='Occupation')
    stockholders_job_position_7 = fields.Char(string='Job Position')
    stockholders_seniority_7 = fields.Char(string='Seniority')
    stockholders_employer_name_7 = fields.Char(string='Employer Name')
    stockholders_employer_phone_7 = fields.Char(string='Employer Phone')
    stockholders_address_file_7 = fields.Binary(string='Address File', attachment=True)
    stockholders_address_file_name_7 = fields.Char(string='Address File Name')

    stockholders_street_name_8 = fields.Char(string='Street Name')
    stockholders_external_number_8 = fields.Char(string='Exterior Number')
    stockholders_number_8 = fields.Char(string='Number')
    stockholders_internal_number_8 = fields.Char(string='Interior Number')
    stockholders_suburb_8 = fields.Char(string='Neighborhood / Suburb')
    stockholders_municipality_8 = fields.Char(string='Municipality / City')
    stockholders_state_name_8 = fields.Char(string='State')
    stockholders_zip_code_8 = fields.Char(string='ZIP Code')
    stockholders_lives_in_house_8 = fields.Boolean(string='Lives In House')
    stockholders_studies_8 = fields.Selection(
        selection=[
            ('primaria', 'PRIMARY'),
            ('secundaria', 'SECONDARY'),
            ('preparatoria', 'HIGH SCHOOL'),
            ('tsu', 'TSU'),
            ('licenciatura', 'BACHELOR'),
            ('ingenieria', 'ENGINEERING'),
            ('maestria', 'MASTER'),
            ('doctorado', 'DOCTORATE'),
        ],
        string='Studies',
    )
    stockholders_marital_status_8 = fields.Char(string='Marital Status')
    stockholders_place_of_birth_8 = fields.Char(string='Place Of Birth')
    stockholders_date_of_birth_8 = fields.Date(string='Date Of Birth')
    stockholders_employer_address_8 = fields.Char(string='Employer Address')
    stockholders_occupation_8 = fields.Char(string='Occupation')
    stockholders_job_position_8 = fields.Char(string='Job Position')
    stockholders_seniority_8 = fields.Char(string='Seniority')
    stockholders_employer_name_8 = fields.Char(string='Employer Name')
    stockholders_employer_phone_8 = fields.Char(string='Employer Phone')
    stockholders_address_file_8 = fields.Binary(string='Address File', attachment=True)
    stockholders_address_file_name_8 = fields.Char(string='Address File Name')

    stockholders_street_name_9 = fields.Char(string='Street Name')
    stockholders_external_number_9 = fields.Char(string='Exterior Number')
    stockholders_number_9 = fields.Char(string='Number')
    stockholders_internal_number_9 = fields.Char(string='Interior Number')
    stockholders_suburb_9 = fields.Char(string='Neighborhood / Suburb')
    stockholders_municipality_9 = fields.Char(string='Municipality / City')
    stockholders_state_name_9 = fields.Char(string='State')
    stockholders_zip_code_9 = fields.Char(string='ZIP Code')
    stockholders_lives_in_house_9 = fields.Boolean(string='Lives In House')
    stockholders_studies_9 = fields.Selection(
        selection=[
            ('primaria', 'PRIMARY'),
            ('secundaria', 'SECONDARY'),
            ('preparatoria', 'HIGH SCHOOL'),
            ('tsu', 'TSU'),
            ('licenciatura', 'BACHELOR'),
            ('ingenieria', 'ENGINEERING'),
            ('maestria', 'MASTER'),
            ('doctorado', 'DOCTORATE'),
        ],
        string='Studies',
    )
    stockholders_marital_status_9 = fields.Char(string='Marital Status')
    stockholders_place_of_birth_9 = fields.Char(string='Place Of Birth')
    stockholders_date_of_birth_9 = fields.Date(string='Date Of Birth')
    stockholders_employer_address_9 = fields.Char(string='Employer Address')
    stockholders_occupation_9 = fields.Char(string='Occupation')
    stockholders_job_position_9 = fields.Char(string='Job Position')
    stockholders_seniority_9 = fields.Char(string='Seniority')
    stockholders_employer_name_9 = fields.Char(string='Employer Name')
    stockholders_employer_phone_9 = fields.Char(string='Employer Phone')
    stockholders_address_file_9 = fields.Binary(string='Address File', attachment=True)
    stockholders_address_file_name_9 = fields.Char(string='Address File Name')

    stockholders_street_name_10 = fields.Char(string='Street Name')
    stockholders_external_number_10 = fields.Char(string='Exterior Number')
    stockholders_number_10 = fields.Char(string='Number')
    stockholders_internal_number_10 = fields.Char(string='Interior Number')
    stockholders_suburb_10 = fields.Char(string='Neighborhood / Suburb')
    stockholders_municipality_10 = fields.Char(string='Municipality / City')
    stockholders_state_name_10 = fields.Char(string='State')
    stockholders_zip_code_10 = fields.Char(string='ZIP Code')
    stockholders_lives_in_house_10 = fields.Boolean(string='Lives In House')
    stockholders_studies_10 = fields.Selection(
        selection=[
            ('primaria', 'PRIMARY'),
            ('secundaria', 'SECONDARY'),
            ('preparatoria', 'HIGH SCHOOL'),
            ('tsu', 'TSU'),
            ('licenciatura', 'BACHELOR'),
            ('ingenieria', 'ENGINEERING'),
            ('maestria', 'MASTER'),
            ('doctorado', 'DOCTORATE'),
        ],
        string='Studies',
    )
    stockholders_marital_status_10 = fields.Char(string='Marital Status')
    stockholders_place_of_birth_10 = fields.Char(string='Place Of Birth')
    stockholders_date_of_birth_10 = fields.Date(string='Date Of Birth')
    stockholders_employer_address_10 = fields.Char(string='Employer Address')
    stockholders_occupation_10 = fields.Char(string='Occupation')
    stockholders_job_position_10 = fields.Char(string='Job Position')
    stockholders_seniority_10 = fields.Char(string='Seniority')
    stockholders_employer_name_10 = fields.Char(string='Employer Name')
    stockholders_employer_phone_10 = fields.Char(string='Employer Phone')
    stockholders_address_file_10 = fields.Binary(string='Address File', attachment=True)
    stockholders_address_file_name_10 = fields.Char(string='Address File Name')




    full_name_file_file_extra_2 = fields.Binary(string="Full Name File File Extra 2")
    curp_file_file_extra_2 = fields.Binary(string="Curp File File Extra 2")
    rfc_file_file_extra_2 = fields.Binary(string="Rfc File File Extra 2")
    address_file_file_extra_2 = fields.Binary(string="Address File File Extra 2")
    official_id_file_file_extra_2 = fields.Binary(string="Official Id File File Extra 2")
    full_name_rl_file_file_extra_2 = fields.Binary(string="Full Name Rl File File Extra 2")
    curp_rl_file_file_extra_2 = fields.Binary(string="Curp Rl File File Extra 2")
    rfc_rl_file_file_extra_2 = fields.Binary(string="Rfc Rl File File Extra 2")
    address_rl_file_file_extra_2 = fields.Binary(string="Address Rl File File Extra 2")
    official_id_rl_file_file_extra_2 = fields.Binary(string="Official Id Rl File File Extra 2")

    full_name_file_2_file_extra_2 = fields.Binary(string="Full Name File 2 File Extra 2")
    official_id_file_2_file_extra_2 = fields.Binary(string="Official Id File 2 File Extra 2")
    address_file_2_file_extra_2 = fields.Binary(string="Address File 2 File Extra 2")
    rfc_file_2_file_extra_2 = fields.Binary(string="Rfc File 2 File Extra 2")
    curp_file_2_file_extra_2 = fields.Binary(string="Curp File 2 File Extra 2")

    full_name_file_3_file_extra_2 = fields.Binary(string="Full Name File 3 File Extra 2")
    official_id_file_3_file_extra_2 = fields.Binary(string="Official Id File 3 File Extra 2")
    address_file_3_file_extra_2 = fields.Binary(string="Address File 3 File Extra 2")
    rfc_file_3_file_extra_2 = fields.Binary(string="Rfc File 3 File Extra 2")
    curp_file_3_file_extra_2 = fields.Binary(string="Curp File 3 File Extra 2")

    full_name_file_4_file_extra_2 = fields.Binary(string="Full Name File 4 File Extra 2")
    official_id_file_4_file_extra_2 = fields.Binary(string="Official Id File 4 File Extra 2")
    address_file_4_file_extra_2 = fields.Binary(string="Address File 4 File Extra 2")
    rfc_file_4_file_extra_2 = fields.Binary(string="Rfc File 4 File Extra 2")
    curp_file_4_file_extra_2 = fields.Binary(string="Curp File 4 File Extra 2")

    full_name_file_5_file_extra_2 = fields.Binary(string="Full Name File 5 File Extra 2")
    official_id_file_5_file_extra_2 = fields.Binary(string="Official Id File 5 File Extra 2")
    address_file_5_file_extra_2 = fields.Binary(string="Address File 5 File Extra 2")
    rfc_file_5_file_extra_2 = fields.Binary(string="Rfc File 5 File Extra 2")
    curp_file_5_file_extra_2 = fields.Binary(string="Curp File 5 File Extra 2")

    full_name_file_6_file_extra_2 = fields.Binary(string="Full Name File 6 File Extra 2")
    official_id_file_6_file_extra_2 = fields.Binary(string="Official Id File 6 File Extra 2")
    address_file_6_file_extra_2 = fields.Binary(string="Address File 6 File Extra 2")
    rfc_file_6_file_extra_2 = fields.Binary(string="Rfc File 6 File Extra 2")
    curp_file_6_file_extra_2 = fields.Binary(string="Curp File 6 File Extra 2")

    full_name_file_7_file_extra_2 = fields.Binary(string="Full Name File 7 File Extra 2")
    official_id_file_7_file_extra_2 = fields.Binary(string="Official Id File 7 File Extra 2")
    address_file_7_file_extra_2 = fields.Binary(string="Address File 7 File Extra 2")
    rfc_file_7_file_extra_2 = fields.Binary(string="Rfc File 7 File Extra 2")
    curp_file_7_file_extra_2 = fields.Binary(string="Curp File 7 File Extra 2")

    full_name_file_8_file_extra_2 = fields.Binary(string="Full Name File 8 File Extra 2")
    official_id_file_8_file_extra_2 = fields.Binary(string="Official Id File 8 File Extra 2")
    address_file_8_file_extra_2 = fields.Binary(string="Address File 8 File Extra 2")
    rfc_file_8_file_extra_2 = fields.Binary(string="Rfc File 8 File Extra 2")
    curp_file_8_file_extra_2 = fields.Binary(string="Curp File 8 File Extra 2")

    full_name_file_9_file_extra_2 = fields.Binary(string="Full Name File 9 File Extra 2")
    official_id_file_9_file_extra_2 = fields.Binary(string="Official Id File 9 File Extra 2")
    address_file_9_file_extra_2 = fields.Binary(string="Address File 9 File Extra 2")
    rfc_file_9_file_extra_2 = fields.Binary(string="Rfc File 9 File Extra 2")
    curp_file_9_file_extra_2 = fields.Binary(string="Curp File 9 File Extra 2")

    full_name_file_10_file_extra_2 = fields.Binary(string="Full Name File 10 File Extra 2")
    official_id_file_10_file_extra_2 = fields.Binary(string="Official Id File 10 File Extra 2")
    address_file_10_file_extra_2 = fields.Binary(string="Address File 10 File Extra 2")
    rfc_file_10_file_extra_2 = fields.Binary(string="Rfc File 10 File Extra 2")
    curp_file_10_file_extra_2 = fields.Binary(string="Curp File 10 File Extra 2")

    spouse_full_name_file_1_file_extra_2 = fields.Binary(string="Spouse Full Name File 1 File Extra 2")
    spouse_official_id_file_1_file_extra_2 = fields.Binary(string="Spouse Official Id File 1 File Extra 2")
    spouse_address_file_1_file_extra_2 = fields.Binary(string="Spouse Address File 1 File Extra 2")
    spouse_rfc_file_1_file_extra_2 = fields.Binary(string="Spouse Rfc File 1 File Extra 2")
    spouse_curp_file_1_file_extra_2 = fields.Binary(string="Spouse Curp File 1 File Extra 2")

    spouse_full_name_file_2_file_extra_2 = fields.Binary(string="Spouse Full Name File 2 File Extra 2")
    spouse_official_id_file_2_file_extra_2 = fields.Binary(string="Spouse Official Id File 2 File Extra 2")
    spouse_address_file_2_file_extra_2 = fields.Binary(string="Spouse Address File 2 File Extra 2")
    spouse_rfc_file_2_file_extra_2 = fields.Binary(string="Spouse Rfc File 2 File Extra 2")
    spouse_curp_file_2_file_extra_2 = fields.Binary(string="Spouse Curp File 2 File Extra 2")

    spouse_full_name_file_3_file_extra_2 = fields.Binary(string="Spouse Full Name File 3 File Extra 2")
    spouse_official_id_file_3_file_extra_2 = fields.Binary(string="Spouse Official Id File 3 File Extra 2")
    spouse_address_file_3_file_extra_2 = fields.Binary(string="Spouse Address File 3 File Extra 2")
    spouse_rfc_file_3_file_extra_2 = fields.Binary(string="Spouse Rfc File 3 File Extra 2")
    spouse_curp_file_3_file_extra_2 = fields.Binary(string="Spouse Curp File 3 File Extra 2")

    spouse_full_name_file_4_file_extra_2 = fields.Binary(string="Spouse Full Name File 4 File Extra 2")
    spouse_official_id_file_4_file_extra_2 = fields.Binary(string="Spouse Official Id File 4 File Extra 2")
    spouse_address_file_4_file_extra_2 = fields.Binary(string="Spouse Address File 4 File Extra 2")
    spouse_rfc_file_4_file_extra_2 = fields.Binary(string="Spouse Rfc File 4 File Extra 2")
    spouse_curp_file_4_file_extra_2 = fields.Binary(string="Spouse Curp File 4 File Extra 2")

    spouse_full_name_file_5_file_extra_2 = fields.Binary(string="Spouse Full Name File 5 File Extra 2")
    spouse_official_id_file_5_file_extra_2 = fields.Binary(string="Spouse Official Id File 5 File Extra 2")
    spouse_address_file_5_file_extra_2 = fields.Binary(string="Spouse Address File 5 File Extra 2")
    spouse_rfc_file_5_file_extra_2 = fields.Binary(string="Spouse Rfc File 5 File Extra 2")
    spouse_curp_file_5_file_extra_2 = fields.Binary(string="Spouse Curp File 5 File Extra 2")

    spouse_full_name_file_6_file_extra_2 = fields.Binary(string="Spouse Full Name File 6 File Extra 2")
    spouse_official_id_file_6_file_extra_2 = fields.Binary(string="Spouse Official Id File 6 File Extra 2")
    spouse_address_file_6_file_extra_2 = fields.Binary(string="Spouse Address File 6 File Extra 2")
    spouse_rfc_file_6_file_extra_2 = fields.Binary(string="Spouse Rfc File 6 File Extra 2")
    spouse_curp_file_6_file_extra_2 = fields.Binary(string="Spouse Curp File 6 File Extra 2")

    spouse_full_name_file_7_file_extra_2 = fields.Binary(string="Spouse Full Name File 7 File Extra 2")
    spouse_official_id_file_7_file_extra_2 = fields.Binary(string="Spouse Official Id File 7 File Extra 2")
    spouse_address_file_7_file_extra_2 = fields.Binary(string="Spouse Address File 7 File Extra 2")
    spouse_rfc_file_7_file_extra_2 = fields.Binary(string="Spouse Rfc File 7 File Extra 2")
    spouse_curp_file_7_file_extra_2 = fields.Binary(string="Spouse Curp File 7 File Extra 2")

    spouse_full_name_file_8_file_extra_2 = fields.Binary(string="Spouse Full Name File 8 File Extra 2")
    spouse_official_id_file_8_file_extra_2 = fields.Binary(string="Spouse Official Id File 8 File Extra 2")
    spouse_address_file_8_file_extra_2 = fields.Binary(string="Spouse Address File 8 File Extra 2")
    spouse_rfc_file_8_file_extra_2 = fields.Binary(string="Spouse Rfc File 8 File Extra 2")
    spouse_curp_file_8_file_extra_2 = fields.Binary(string="Spouse Curp File 8 File Extra 2")

    spouse_full_name_file_9_file_extra_2 = fields.Binary(string="Spouse Full Name File 9 File Extra 2")
    spouse_official_id_file_9_file_extra_2 = fields.Binary(string="Spouse Official Id File 9 File Extra 2")
    spouse_address_file_9_file_extra_2 = fields.Binary(string="Spouse Address File 9 File Extra 2")
    spouse_rfc_file_9_file_extra_2 = fields.Binary(string="Spouse Rfc File 9 File Extra 2")
    spouse_curp_file_9_file_extra_2 = fields.Binary(string="Spouse Curp File 9 File Extra 2")

    spouse_full_name_file_10_file_extra_2 = fields.Binary(string="Spouse Full Name File 10 File Extra 2")
    spouse_official_id_file_10_file_extra_2 = fields.Binary(string="Spouse Official Id File 10 File Extra 2")
    spouse_address_file_10_file_extra_2 = fields.Binary(string="Spouse Address File 10 File Extra 2")
    spouse_rfc_file_10_file_extra_2 = fields.Binary(string="Spouse Rfc File 10 File Extra 2")
    spouse_curp_file_10_file_extra_2 = fields.Binary(string="Spouse Curp File 10 File Extra 2")

    stockholder_full_name_file_1_file_extra_2 = fields.Binary(string="Stockholder Full Name File 1 File Extra 2")
    stockholder_address_file_1_file_extra_2 = fields.Binary(string="Stockholder Address File 1 File Extra 2")
    stockholder_rfc_file_1_file_extra_2 = fields.Binary(string="Stockholder Rfc File 1 File Extra 2")
    stockholder_curp_file_1_file_extra_2 = fields.Binary(string="Stockholder Curp File 1 File Extra 2")

    stockholder_full_name_file_2_file_extra_2 = fields.Binary(string="Stockholder Full Name File 2 File Extra 2")
    stockholder_address_file_2_file_extra_2 = fields.Binary(string="Stockholder Address File 2 File Extra 2")
    stockholder_rfc_file_2_file_extra_2 = fields.Binary(string="Stockholder Rfc File 2 File Extra 2")
    stockholder_curp_file_2_file_extra_2 = fields.Binary(string="Stockholder Curp File 2 File Extra 2")

    stockholder_full_name_file_3_file_extra_2 = fields.Binary(string="Stockholder Full Name File 3 File Extra 2")
    stockholder_address_file_3_file_extra_2 = fields.Binary(string="Stockholder Address File 3 File Extra 2")
    stockholder_rfc_file_3_file_extra_2 = fields.Binary(string="Stockholder Rfc File 3 File Extra 2")
    stockholder_curp_file_3_file_extra_2 = fields.Binary(string="Stockholder Curp File 3 File Extra 2")

    stockholder_full_name_file_4_file_extra_2 = fields.Binary(string="Stockholder Full Name File 4 File Extra 2")
    stockholder_address_file_4_file_extra_2 = fields.Binary(string="Stockholder Address File 4 File Extra 2")
    stockholder_rfc_file_4_file_extra_2 = fields.Binary(string="Stockholder Rfc File 4 File Extra 2")
    stockholder_curp_file_4_file_extra_2 = fields.Binary(string="Stockholder Curp File 4 File Extra 2")

    stockholder_full_name_file_5_file_extra_2 = fields.Binary(string="Stockholder Full Name File 5 File Extra 2")
    stockholder_address_file_5_file_extra_2 = fields.Binary(string="Stockholder Address File 5 File Extra 2")
    stockholder_rfc_file_5_file_extra_2 = fields.Binary(string="Stockholder Rfc File 5 File Extra 2")
    stockholder_curp_file_5_file_extra_2 = fields.Binary(string="Stockholder Curp File 5 File Extra 2")

    stockholder_full_name_file_6_file_extra_2 = fields.Binary(string="Stockholder Full Name File 6 File Extra 2")
    stockholder_address_file_6_file_extra_2 = fields.Binary(string="Stockholder Address File 6 File Extra 2")
    stockholder_rfc_file_6_file_extra_2 = fields.Binary(string="Stockholder Rfc File 6 File Extra 2")
    stockholder_curp_file_6_file_extra_2 = fields.Binary(string="Stockholder Curp File 6 File Extra 2")

    stockholder_full_name_file_7_file_extra_2 = fields.Binary(string="Stockholder Full Name File 7 File Extra 2")
    stockholder_address_file_7_file_extra_2 = fields.Binary(string="Stockholder Address File 7 File Extra 2")
    stockholder_rfc_file_7_file_extra_2 = fields.Binary(string="Stockholder Rfc File 7 File Extra 2")
    stockholder_curp_file_7_file_extra_2 = fields.Binary(string="Stockholder Curp File 7 File Extra 2")

    stockholder_full_name_file_8_file_extra_2 = fields.Binary(string="Stockholder Full Name File 8 File Extra 2")
    stockholder_address_file_8_file_extra_2 = fields.Binary(string="Stockholder Address File 8 File Extra 2")
    stockholder_rfc_file_8_file_extra_2 = fields.Binary(string="Stockholder Rfc File 8 File Extra 2")
    stockholder_curp_file_8_file_extra_2 = fields.Binary(string="Stockholder Curp File 8 File Extra 2")

    stockholder_full_name_file_9_file_extra_2 = fields.Binary(string="Stockholder Full Name File 9 File Extra 2")
    stockholder_address_file_9_file_extra_2 = fields.Binary(string="Stockholder Address File 9 File Extra 2")
    stockholder_rfc_file_9_file_extra_2 = fields.Binary(string="Stockholder Rfc File 9 File Extra 2")
    stockholder_curp_file_9_file_extra_2 = fields.Binary(string="Stockholder Curp File 9 File Extra 2")

    stockholder_full_name_file_10_file_extra_2 = fields.Binary(string="Stockholder Full Name File 10 File Extra 2")
    stockholder_address_file_10_file_extra_2 = fields.Binary(string="Stockholder Address File 10 File Extra 2")
    stockholder_rfc_file_10_file_extra_2 = fields.Binary(string="Stockholder Rfc File 10 File Extra 2")
    stockholder_curp_file_10_file_extra_2 = fields.Binary(string="Stockholder Curp File 10 File Extra 2")

    stockholders_address_file_1_file_extra_2 = fields.Binary(string="Stockholders Address File 1 File Extra 2")
    stockholders_address_file_2_file_extra_2 = fields.Binary(string="Stockholders Address File 2 File Extra 2")
    stockholders_address_file_3_file_extra_2 = fields.Binary(string="Stockholders Address File 3 File Extra 2")
    stockholders_address_file_4_file_extra_2 = fields.Binary(string="Stockholders Address File 4 File Extra 2")
    stockholders_address_file_5_file_extra_2 = fields.Binary(string="Stockholders Address File 5 File Extra 2")
    stockholders_address_file_6_file_extra_2 = fields.Binary(string="Stockholders Address File 6 File Extra 2")
    stockholders_address_file_7_file_extra_2 = fields.Binary(string="Stockholders Address File 7 File Extra 2")
    stockholders_address_file_8_file_extra_2 = fields.Binary(string="Stockholders Address File 8 File Extra 2")
    stockholders_address_file_9_file_extra_2 = fields.Binary(string="Stockholders Address File 9 File Extra 2")
    stockholders_address_file_10_file_extra_2 = fields.Binary(string="Stockholders Address File 10 File Extra 2")

    full_name_file_file_extra_2_name = fields.Char()
    curp_file_file_extra_2_name = fields.Char()
    rfc_file_file_extra_2_name = fields.Char()
    address_file_file_extra_2_name = fields.Char()
    official_id_file_file_extra_2_name = fields.Char()
    full_name_rl_file_file_extra_2_name = fields.Char()
    curp_rl_file_file_extra_2_name = fields.Char()
    rfc_rl_file_file_extra_2_name = fields.Char()
    address_rl_file_file_extra_2_name = fields.Char()
    official_id_rl_file_file_extra_2_name = fields.Char()

    full_name_file_2_file_extra_2_name = fields.Char()
    official_id_file_2_file_extra_2_name = fields.Char()
    address_file_2_file_extra_2_name = fields.Char()
    rfc_file_2_file_extra_2_name = fields.Char()
    curp_file_2_file_extra_2_name = fields.Char()

    full_name_file_3_file_extra_2_name = fields.Char()
    official_id_file_3_file_extra_2_name = fields.Char()
    address_file_3_file_extra_2_name = fields.Char()
    rfc_file_3_file_extra_2_name = fields.Char()
    curp_file_3_file_extra_2_name = fields.Char()

    full_name_file_4_file_extra_2_name = fields.Char()
    official_id_file_4_file_extra_2_name = fields.Char()
    address_file_4_file_extra_2_name = fields.Char()
    rfc_file_4_file_extra_2_name = fields.Char()
    curp_file_4_file_extra_2_name = fields.Char()

    full_name_file_5_file_extra_2_name = fields.Char()
    official_id_file_5_file_extra_2_name = fields.Char()
    address_file_5_file_extra_2_name = fields.Char()
    rfc_file_5_file_extra_2_name = fields.Char()
    curp_file_5_file_extra_2_name = fields.Char()

    full_name_file_6_file_extra_2_name = fields.Char()
    official_id_file_6_file_extra_2_name = fields.Char()
    address_file_6_file_extra_2_name = fields.Char()
    rfc_file_6_file_extra_2_name = fields.Char()
    curp_file_6_file_extra_2_name = fields.Char()

    full_name_file_7_file_extra_2_name = fields.Char()
    official_id_file_7_file_extra_2_name = fields.Char()
    address_file_7_file_extra_2_name = fields.Char()
    rfc_file_7_file_extra_2_name = fields.Char()
    curp_file_7_file_extra_2_name = fields.Char()

    full_name_file_8_file_extra_2_name = fields.Char()
    official_id_file_8_file_extra_2_name = fields.Char()
    address_file_8_file_extra_2_name = fields.Char()
    rfc_file_8_file_extra_2_name = fields.Char()
    curp_file_8_file_extra_2_name = fields.Char()

    full_name_file_9_file_extra_2_name = fields.Char()
    official_id_file_9_file_extra_2_name = fields.Char()
    address_file_9_file_extra_2_name = fields.Char()
    rfc_file_9_file_extra_2_name = fields.Char()
    curp_file_9_file_extra_2_name = fields.Char()

    full_name_file_10_file_extra_2_name = fields.Char()
    official_id_file_10_file_extra_2_name = fields.Char()
    address_file_10_file_extra_2_name = fields.Char()
    rfc_file_10_file_extra_2_name = fields.Char()
    curp_file_10_file_extra_2_name = fields.Char()

    spouse_full_name_file_1_file_extra_2_name = fields.Char()
    spouse_official_id_file_1_file_extra_2_name = fields.Char()
    spouse_address_file_1_file_extra_2_name = fields.Char()
    spouse_rfc_file_1_file_extra_2_name = fields.Char()
    spouse_curp_file_1_file_extra_2_name = fields.Char()

    spouse_full_name_file_2_file_extra_2_name = fields.Char()
    spouse_official_id_file_2_file_extra_2_name = fields.Char()
    spouse_address_file_2_file_extra_2_name = fields.Char()
    spouse_rfc_file_2_file_extra_2_name = fields.Char()
    spouse_curp_file_2_file_extra_2_name = fields.Char()

    spouse_full_name_file_3_file_extra_2_name = fields.Char()
    spouse_official_id_file_3_file_extra_2_name = fields.Char()
    spouse_address_file_3_file_extra_2_name = fields.Char()
    spouse_rfc_file_3_file_extra_2_name = fields.Char()
    spouse_curp_file_3_file_extra_2_name = fields.Char()

    spouse_full_name_file_4_file_extra_2_name = fields.Char()
    spouse_official_id_file_4_file_extra_2_name = fields.Char()
    spouse_address_file_4_file_extra_2_name = fields.Char()
    spouse_rfc_file_4_file_extra_2_name = fields.Char()
    spouse_curp_file_4_file_extra_2_name = fields.Char()

    spouse_full_name_file_5_file_extra_2_name = fields.Char()
    spouse_official_id_file_5_file_extra_2_name = fields.Char()
    spouse_address_file_5_file_extra_2_name = fields.Char()
    spouse_rfc_file_5_file_extra_2_name = fields.Char()
    spouse_curp_file_5_file_extra_2_name = fields.Char()

    spouse_full_name_file_6_file_extra_2_name = fields.Char()
    spouse_official_id_file_6_file_extra_2_name = fields.Char()
    spouse_address_file_6_file_extra_2_name = fields.Char()
    spouse_rfc_file_6_file_extra_2_name = fields.Char()
    spouse_curp_file_6_file_extra_2_name = fields.Char()

    spouse_full_name_file_7_file_extra_2_name = fields.Char()
    spouse_official_id_file_7_file_extra_2_name = fields.Char()
    spouse_address_file_7_file_extra_2_name = fields.Char()
    spouse_rfc_file_7_file_extra_2_name = fields.Char()
    spouse_curp_file_7_file_extra_2_name = fields.Char()

    spouse_full_name_file_8_file_extra_2_name = fields.Char()
    spouse_official_id_file_8_file_extra_2_name = fields.Char()
    spouse_address_file_8_file_extra_2_name = fields.Char()
    spouse_rfc_file_8_file_extra_2_name = fields.Char()
    spouse_curp_file_8_file_extra_2_name = fields.Char()

    spouse_full_name_file_9_file_extra_2_name = fields.Char()
    spouse_official_id_file_9_file_extra_2_name = fields.Char()
    spouse_address_file_9_file_extra_2_name = fields.Char()
    spouse_rfc_file_9_file_extra_2_name = fields.Char()
    spouse_curp_file_9_file_extra_2_name = fields.Char()

    spouse_full_name_file_10_file_extra_2_name = fields.Char()
    spouse_official_id_file_10_file_extra_2_name = fields.Char()
    spouse_address_file_10_file_extra_2_name = fields.Char()
    spouse_rfc_file_10_file_extra_2_name = fields.Char()
    spouse_curp_file_10_file_extra_2_name = fields.Char()

    stockholder_full_name_file_1_file_extra_2_name = fields.Char()
    stockholder_address_file_1_file_extra_2_name = fields.Char()
    stockholder_rfc_file_1_file_extra_2_name = fields.Char()
    stockholder_curp_file_1_file_extra_2_name = fields.Char()

    stockholder_full_name_file_2_file_extra_2_name = fields.Char()
    stockholder_address_file_2_file_extra_2_name = fields.Char()
    stockholder_rfc_file_2_file_extra_2_name = fields.Char()
    stockholder_curp_file_2_file_extra_2_name = fields.Char()

    stockholder_full_name_file_3_file_extra_2_name = fields.Char()
    stockholder_address_file_3_file_extra_2_name = fields.Char()
    stockholder_rfc_file_3_file_extra_2_name = fields.Char()
    stockholder_curp_file_3_file_extra_2_name = fields.Char()

    stockholder_full_name_file_4_file_extra_2_name = fields.Char()
    stockholder_address_file_4_file_extra_2_name = fields.Char()
    stockholder_rfc_file_4_file_extra_2_name = fields.Char()
    stockholder_curp_file_4_file_extra_2_name = fields.Char()

    stockholder_full_name_file_5_file_extra_2_name = fields.Char()
    stockholder_address_file_5_file_extra_2_name = fields.Char()
    stockholder_rfc_file_5_file_extra_2_name = fields.Char()
    stockholder_curp_file_5_file_extra_2_name = fields.Char()

    stockholder_full_name_file_6_file_extra_2_name = fields.Char()
    stockholder_address_file_6_file_extra_2_name = fields.Char()
    stockholder_rfc_file_6_file_extra_2_name = fields.Char()
    stockholder_curp_file_6_file_extra_2_name = fields.Char()

    stockholder_full_name_file_7_file_extra_2_name = fields.Char()
    stockholder_address_file_7_file_extra_2_name = fields.Char()
    stockholder_rfc_file_7_file_extra_2_name = fields.Char()
    stockholder_curp_file_7_file_extra_2_name = fields.Char()

    stockholder_full_name_file_8_file_extra_2_name = fields.Char()
    stockholder_address_file_8_file_extra_2_name = fields.Char()
    stockholder_rfc_file_8_file_extra_2_name = fields.Char()
    stockholder_curp_file_8_file_extra_2_name = fields.Char()

    stockholder_full_name_file_9_file_extra_2_name = fields.Char()
    stockholder_address_file_9_file_extra_2_name = fields.Char()
    stockholder_rfc_file_9_file_extra_2_name = fields.Char()
    stockholder_curp_file_9_file_extra_2_name = fields.Char()

    stockholder_full_name_file_10_file_extra_2_name = fields.Char()
    stockholder_address_file_10_file_extra_2_name = fields.Char()
    stockholder_rfc_file_10_file_extra_2_name = fields.Char()
    stockholder_curp_file_10_file_extra_2_name = fields.Char()

    stockholders_address_file_1_file_extra_2_name = fields.Char()
    stockholders_address_file_2_file_extra_2_name = fields.Char()
    stockholders_address_file_3_file_extra_2_name = fields.Char()
    stockholders_address_file_4_file_extra_2_name = fields.Char()
    stockholders_address_file_5_file_extra_2_name = fields.Char()
    stockholders_address_file_6_file_extra_2_name = fields.Char()
    stockholders_address_file_7_file_extra_2_name = fields.Char()
    stockholders_address_file_8_file_extra_2_name = fields.Char()
    stockholders_address_file_9_file_extra_2_name = fields.Char()
    stockholders_address_file_10_file_extra_2_name = fields.Char()



    bank_statement = fields.Char(string='Bank statement')
    bank_statement_file = fields.Binary(string='bank_statement Document')
    bank_statement_file_name = fields.Char()

    file_file_extra_2 = fields.Binary(string="File File Extra 2")

    have_contract = fields.Boolean()
    have_commission = fields.Boolean(string='Have Commission', default=False)

    gender = fields.Selection(
        selection=[
            ('male', 'Él'),
            ('female', 'Ella'),
        ],
        string='Género',
        required=True,
        default='male',
    )

    def action_open_send_contract_email_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Send Contract Email"),
            "res_model": "contract.send.email.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_rev_id": self.id,
            },
        }

    def action_send_missing_documents_email(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Send missing documents email"),
            "res_model": "missing.documents.email.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_rev_id": self.id,
            },
        }

    @api.model
    def cron_contract_brief_followups(self):
        today = fields.Date.context_today(self)
        ICP = self.env['ir.config_parameter'].sudo()
        deadline_days = 10
        try:
            deadline_days = int(ICP.get_param('rev.deposit.deadline_days', default='10'))
        except Exception:
            deadline_days = 10

        def _already_sent(rec, code):
            return bool(self.env['mail.message'].sudo().search_count([
                ('model', '=', rec._name),
                ('res_id', '=', rec.id),
                ('subject', 'ilike', code),
            ]))

        def _send_email(rec, subject, body_html):
            email_to = rec.email or (
                        rec.sale_order_id and rec.sale_order_id.partner_id and rec.sale_order_id.partner_id.email) or False
            if not email_to:
                return
            mail = self.env['mail.mail'].sudo().create({
                'subject': subject,
                'email_to': email_to,
                'body_html': body_html,
                'auto_delete': True,
            })
            mail.send()

        drafts = self.search([('state', '=', 'draft')])
        for rec in drafts:
            if not rec.create_date:
                continue
            created_local = fields.Datetime.context_timestamp(rec, rec.create_date).date()
            if (today - created_local).days >= 2 and not _already_sent(rec, '[CB-D2]'):
                dev_name = rec.worksite_id.name or 'tu desarrollo'
                subject = 'Recordatorio: Envío de documentos [CB-D2]'
                body = f"""
                        <p>Hola {rec.full_name},</p>
                        <p>Queremos asegurarnos de que conserves tu unidad en {dev_name}.</p>
                        <p>Aún no recibimos tus documentos, y el plazo para entregarlos está por finalizar. Recuerda
                        que sin ellos no podremos generar tu contrato.</p>
                        <p>Si necesitas apoyo para enviarlos, contáctanos ahora mismo.</p>
                    """
                _send_email(rec, subject, body)

        valids = self.search([('state', '=', 'validated'), ('validated_date', '!=', False)])
        for rec in valids:
            days = (today - rec.validated_date).days
            if days < 1:
                continue

            amount_txt = rec.total_down_payment or ''
            try:
                amount_num = float(str(amount_txt).replace(',', '').replace('$', '').replace('MXN', '').strip())
                amount_fmt = f"${amount_num:,.2f} MXN"
            except Exception:
                amount_fmt = amount_txt or '$0.00 MXN'

            payment_details = ICP.get_param('rev.payment.details', default='')
            if not payment_details:
                payment_details = f"{self.env.company.name}<br/>Cuenta: —<br/>CLABE: —<br/>Banco: —"

            deadline_date = rec.validated_date + relativedelta(days=deadline_days)
            deadline_txt = f"{deadline_date.day:02d}/{deadline_date.month:02d}/{deadline_date.year}"

            if days >= 8 and not _already_sent(rec, '[CB-V8]'):
                subject = 'Último aviso: liberación de unidad [CB-V8]'
                body = f"""
                        <p>Hola {rec.full_name},</p>
                        <p>Quedan pocos días para realizar el pago de tu enganche.</p>
                        <p>Si no se recibe antes del <strong>{deadline_txt}</strong>, lamentablemente la unidad será liberada.</p>
                    """
                _send_email(rec, subject, body)
                continue

            if days >= 5 and not _already_sent(rec, '[CB-V5]'):
                subject = 'Recordatorio de pago de enganche [CB-V5]'
                body = f"""
                        <p>Hola {rec.full_name},</p>
                        <p>Queremos recordarte que aún está pendiente el pago de tu enganche por <strong>{amount_fmt}</strong>.</p>
                        <p>El plazo para completar el proceso vence el <strong>{deadline_txt}</strong>, y sin este pago no podremos
                        firmar tu contrato.</p>
                    """
                _send_email(rec, subject, body)
                continue

            if days >= 1 and not _already_sent(rec, '[CB-V1]'):
                subject = 'Solicitud de pago de enganche [CB-V1]'
                body = f"""
                        <p>Hola {rec.full_name},</p>
                        <p>Ya tenemos listos tus documentos. El siguiente paso es realizar el pago de tu enganche por
                        <strong>{amount_fmt}</strong> para poder continuar con la formalización del contrato.</p>
                        <p>Te compartimos nuevamente los datos de pago:</p>
                        <p>{payment_details}</p>
                        <p>Una vez realizado, envíanos el comprobante en PDF.</p>
                    """
                _send_email(rec, subject, body)


    def _find_contract_with_advance_payment(self):
        self.ensure_one()

        Contract = self.env['property.contract'].sudo()

        contract_id = self.env.context.get('contract_id')
        if contract_id:
            c = Contract.browse(int(contract_id))
            if c and c.exists() and getattr(c, 'advance_payment_payment_id', False):
                return c
            return Contract.browse()

        con = Contract.search([
            ('reservation_id.order_id.opportunity_id', '=', self.lead_id.id),
            ('advance_payment_payment_id', '!=', False),
        ], limit=1)

        return con

    def _get_promotion_from_sale_order(self, order):
        if not order:
            return False

        finance_plan = getattr(order, 'finance_id', False)
        financial_lines = getattr(order, 'financial_lines', False)

        if not finance_plan or not financial_lines:
            return False

        match = financial_lines.filtered(lambda l: (l.name or '') == (finance_plan.name or ''))[:1]
        if not match:
            return False

        promo = getattr(match, 'promotion_id', False)
        return promo if promo else False

    def action_create_commission(self):
        if not self:
            return False

        if len(self) == 1:
            rec = self

            if rec.have_commission:
                return False

            if not rec.lead_id:
                return False


            lead = rec.lead_id

            property_name = lead.property_id.name if getattr(lead, 'property_id', False) else False
            ref_name = lead.property_id.default_code if getattr(lead, 'property_id', False) else False
            commission_name = 'comisiones ' + (property_name or (lead.name or ''))


            deposit = 0.0
            deposit_date = False

            related_contract = rec.env['property.contract'].sudo().search(
                [('reservation_id.order_id.opportunity_id', '=', lead.id)],
                limit=1
            )

            if not related_contract:
                print(f"[COMMISSION][INFO] No related contract found for lead {lead.id}")
            elif not getattr(related_contract, 'reservation_id', False):
                print(f"[COMMISSION][INFO] Contract {related_contract.id} has no reservation")
            else:
                deposit = related_contract.reservation_id.deposit or 0.0
                deposit_date = related_contract.reservation_id.date

            sale_order = rec.env['sale.order'].search(
                [('opportunity_id', '=', lead.id)],
                limit=1,
                order='id desc',
            )

            if not sale_order:
                print(f"[COMMISSION][INFO] No sale order found for lead {lead.id}")
            else:
                print(f"[COMMISSION] Sale Order {sale_order.name} ({sale_order.id})")

            promo = rec._get_promotion_from_sale_order(sale_order)
            promo_name = promo.name if promo else ''

            vals = {
                'lead_id': lead.id,
                'name': commission_name,
                'reference': ref_name,
                'promotion_name': promo_name,
                'deposit': deposit,
                'deposit_date': deposit_date,
            }


            commission = rec.env['ccima.commissions'].create(vals)


            commission._onchange_lead_id()

            commission.action_calculate_lines()

            rec.sudo().write({'have_commission': True})

            return commission

        created = self.env['ccima.commissions']
        for rec in self:
            commission = rec.action_create_commission()
            if commission:
                created |= commission

        return created

    def action_validate(self):
        for rec in self:
            rec.write({
                'state': 'validated',
                'validated_date': fields.Date.context_today(self),
            })

    def action_generate_contract(self):
        self.ensure_one()
        if not self.lead_id:
            raise UserError(_("No related Opportunity found."))
        activity_types = self.env['mail.activity.type'].search([
            ('name', 'in', ['Request Signature', 'Solicitar firma'])
        ])
        activity = self.env['mail.activity'].search([
            ('res_model', '=', 'crm.lead'),
            ('res_id', '=', self.lead_id.id),
            ('activity_type_id', 'in', activity_types.ids),
        ], limit=1)
        if not activity:
            raise UserError(_("No 'Request Signature' activity found on the related lead."))

        ctx = {
            'default_res_model': 'crm.lead',
            'default_res_id': self.lead_id.id,
            'default_template_id': False,
            'search_default_no_template': 1,
        }

        if self.lead_id:
            ctx.update({
                'default_opportunity_id': self.lead_id.id,
                'default_oportunity_id': self.lead_id.id,
            })

        if getattr(self, 'sale_order_id', False):

            reservation = self.env['property.reservation'].search([ ('order_id', '=', self.sale_order_id.id)], limit=1)

            contract = False
            if reservation:
                contract = self.env['property.contract'].search([ ('reservation_id', '=', reservation.id)], limit=1)

            if contract:
                found_contract = contract
                ctx.update({
                    'default_property_contract_id': found_contract.id,
                })
            else:
                found_contract = False


            ctx.update({
                'default_sale_order_id': self.sale_order_id.id,
            })

        try:
            term_months = None
            if getattr(self, 'sale_order_id', False) and getattr(self.sale_order_id, 'finance_id', False):
                term_months = getattr(self.sale_order_id.finance_id, 'duration_month', None)

            if isinstance(term_months, (int, float)) and term_months > 0:
                if term_months % 12 == 0:
                    years = int(term_months // 12)
                    allowed = {'10', '15', '20'}
                    key = str(years)
                    if key in allowed:
                        ctx.update({'default_finance_time': key})
        except Exception:
            pass




        return {
            'type': 'ir.actions.act_window',
            'name': _('Request Signature'),
            'res_model': 'sign.send.request',
            'view_mode': 'form',
            'target': 'new',
            'context': ctx,
        }

    def _sync_partner_company_type(self):
        self.ensure_one()

        lead = self.lead_id
        partner = lead and lead.partner_id or False
        if not partner:
            return

        if self.person_type == 'fisica':
            company_type = 'person'
        elif self.person_type in ('morial', 'coopropiedad'):
            company_type = 'company'
        else:
            return

        if partner.company_type != company_type:
            partner.sudo().with_context(tracking_disable=True).write({
                'company_type': company_type
            })

    def _compute_company_legal_name(self):
        for record in self:
            record.company_legal_name = record.company_id.name or ''

    def action_open_upload_wizard(self):
        self.ensure_one()
        target_field = self.env.context.get('target_field')
        filename_field = self.env.context.get('filename_field')
        dialog_title = self.env.context.get('title') or _("Upload file")
        if not target_field or not filename_field or not hasattr(self, target_field) or not hasattr(self, filename_field):
            raise UserError(_("Invalid upload target."))
        return {
            'type': 'ir.actions.act_window',
            'name': dialog_title,
            'res_model': 'rev.crm.brief.file.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_brief_id': self.id,
                'default_target_field': target_field,
                'default_filename_field': filename_field,
                'default_file': getattr(self, target_field),
                'default_file_name': getattr(self, filename_field),
            },
        }

    def action_add_person_section(self):
        for rec in self:
            if rec.persons_visible < 10:
                rec.persons_visible += 1
        return True

    def action_add_stockholder_section(self):
        for rec in self:
            if rec.stockholders_visible < 10:
                rec.stockholders_visible += 1

    def action_open_upload_contract(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Upload contract"),
            'res_model': 'rev.crm.brief.file.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_brief_id': self.id,
                'default_target_field': 'contract_file',
                'default_filename_field': 'contract_file_name',
                'default_file_name': self.contract_file_name or '',
                'title': _("Upload contract"),
            },
        }

    def _sync_binary_to_documents(self, changed_fields):
        import traceback

        Attachment = self.env["ir.attachment"].sudo()


        root_user = self.env.ref("base.user_root", raise_if_not_found=False)
        table = self.env["documents.document"]._table

        for rec in self:
            target_folder = rec.brief_folder_id or False
            if not target_folder:
                continue

            Doc = self.env["documents.document"].with_context(
                mm_force_folder_id=target_folder.id,
                mm_force_parent_id=target_folder.id,
            ).sudo()

            for fname in changed_fields:
                field = rec._fields.get(fname)
                if not field:
                    continue

                if field.type != "binary":
                    continue

                domain = [
                    ("res_model", "=", rec._name),
                    ("res_id", "=", rec.id),
                    ("res_field", "=", fname),
                ]

                att = Attachment.search(domain, order="id desc", limit=1)
                if not att:
                    continue


                doc = Doc.search([("attachment_id", "=", att.id)], limit=1)

                name_field = fname.replace("_file", "_file_name")
                document_name = getattr(rec, name_field, False) or att.name or fname

                vals = {
                    "name": document_name,
                    "type": "binary",
                    "folder_id": target_folder.id,
                    "attachment_id": att.id,
                    "access_internal": "view",
                    "owner_id": (root_user.id if root_user else self.env.user.id),
                }


                try:
                    if doc:
                        doc.write(vals)
                        self.env.cr.flush()

                        doc_db = self.env["documents.document"].sudo().browse(doc.id)

                        self.env.cr.execute(f"SELECT folder_id FROM {table} WHERE id=%s", (doc.id,))

                    else:
                        new_doc = Doc.create(vals)
                        self.env.cr.flush()

                        doc_db = self.env["documents.document"].sudo().browse(new_doc.id)

                        self.env.cr.execute(f"SELECT folder_id FROM {table} WHERE id=%s", (new_doc.id,))

                except Exception as e:
                    print("[SYNC] ERROR:", e)

                try:
                    check = Doc.search([("attachment_id", "=", att.id)], limit=1)
                except Exception as e:
                    print("[SYNC] ERROR on re-check search:", e)

    @api.onchange('person_type')
    def _onchange_person_type_fill_from_partner(self):
        for rec in self:

            partner = rec.lead_id.partner_id if getattr(rec, 'lead_id', False) else False
            if not partner:
                continue

            if rec.person_type in ('fisica', 'coopropiedad'):
                studies_map = {
                    'primary': 'primaria',
                    'secondary': 'secundaria',
                    'high_school': 'preparatoria',
                    'tsu': 'tsu',
                    'bachelors_degree': 'licenciatura',
                    'engineering': 'ingenieria',
                    'master_degree': 'maestria',
                    'phd': 'doctorado',
                }
                mapped_study = studies_map.get(getattr(partner, 'individual_marital_status', False), False)

                rec.update({
                    'suburb': getattr(partner, 'colony', False) or False,
                    'external_number': getattr(partner, 'colony_number', False) or False,
                    'nationality': getattr(partner, 'individual_nationality', False).name
                    if getattr(partner, 'individual_nationality', False) else False,
                    'studies': mapped_study,
                    'applies_assets': getattr(partner, 'individual_apply_goods', False) or False,
                    'place_of_birth': getattr(partner, 'individual_birth_place_nationality', False).name
                    if getattr(partner, 'individual_birth_place_nationality', False) else False,
                    'date_of_birth': getattr(partner, 'individual_date_birth', False) or False,
                    'employer_name': getattr(partner, 'individual_company_work', False) or False,
                    'occupation': getattr(partner, 'individual_company_job_position', False) or False,
                    'seniority': getattr(partner, 'individual_company_seniority', False) or False,
                    'employer_phone': getattr(partner, 'individual_company_mobile', False) or False,
                })

            elif rec.person_type == 'morial':
                rec.update({
                    'suburb': getattr(partner, 'colony', False) or False,
                    'external_number': getattr(partner, 'colony_number', False) or False,
                    'business_turn': getattr(partner, 'company_type_business', False) or False,
                    'activity': getattr(partner, 'company_activity', False) or False,
                    'folio': getattr(partner, 'company_registry_number', False) or False,
                    'registration_date': getattr(partner, 'company_date_registration', False) or False,
                    'notary_number': getattr(partner, 'company_notary_number', False) or False,
                    'notary_name': getattr(partner, 'company_notary_name', False) or False,
                    'registration_city': getattr(partner, 'company_city_registration', False) or False,
                    'corporate_purpose': getattr(partner, 'company_purpose', False) or False,
                    'commercial_folio': getattr(partner, 'company_commercial_registry_number', False) or False,
                })

    @staticmethod
    def _normalize_name(name):
        if not name:
            return False
        return ' '.join(str(name).strip().split())

    def _collect_spouse_names(self):
        names = []
        for i in range(1, 10 + 1):
            raw = getattr(self, f'spouse_full_name_{i}', False)
            norm = self._normalize_name(raw)
            if norm and norm not in names:
                names.append(norm)
        return names

    def _ensure_related_contact(self, main_partner, name, email, phone, label='Related Contact'):
        Partner = self.env['res.partner']

        name = (name or '').strip()
        email = (email or '').strip()
        phone = (phone or '').strip()

        if not (name and email and phone):
            return


        related = Partner.search([
            ('name', '=', name),
            ('email', '=', email),
            ('phone', '=', phone),
        ], limit=1)

        if related:
            if related.id != main_partner.id:
                vals = {
                    'parent_id': main_partner.id,
                    'type': 'contact',
                }
                if main_partner.company_id:
                    vals['company_id'] = main_partner.company_id.id
                related.write(vals)
            return

        partial_domain = []
        if name:
            partial_domain = expression.OR([partial_domain, [('name', '=', name)]]) if partial_domain else [
                ('name', '=', name)]
        if email:
            partial_domain = expression.OR([partial_domain, [('email', '=', email)]]) if partial_domain else [
                ('email', '=', email)]

        partial_matches = Partner.search(partial_domain) if partial_domain else Partner.browse()
        if partial_matches:
            related = partial_matches[0]
            if related.id != main_partner.id:
                vals = {
                    'parent_id': main_partner.id,
                    'type': 'contact',
                }
                if main_partner.company_id:
                    vals['company_id'] = main_partner.company_id.id
                related.write(vals)
            return

        vals = {
            'name': name,
            'parent_id': main_partner.id,
            'type': 'contact',
            'is_company': False,
        }
        if main_partner.company_id:
            vals['company_id'] = main_partner.company_id.id
        vals['email'] = email
        vals['phone'] = phone

        Partner.create(vals)

    def _create_spouse_contacts(self):
        for rec in self:
            main_partner = rec.lead_id.partner_id if getattr(rec, 'lead_id', False) else False
            if not main_partner:
                continue

            rec._ensure_related_contact(
                main_partner=main_partner,
                name=rec.spouse_full_name_1,
                email=rec.spouse_email_1,
                phone=rec.spouse_phone_number_1,
                label='Spouse 1',
            )

            for i in (2, 3, 4):
                rec._ensure_related_contact(
                    main_partner=main_partner,
                    name=getattr(rec, f'full_name_{i}', False),
                    email=getattr(rec, f'email_{i}', False),
                    phone=getattr(rec, f'phone_number_{i}', False),
                    label=f'Person {i}',
                )

    def _create_stockholder_contacts(self):
        for rec in self:
            main_partner = rec.lead_id.partner_id if getattr(rec, 'lead_id', False) else False
            if not main_partner:
                continue

            for i in (1, 2, 3, 4):
                rec._ensure_related_contact(
                    main_partner=main_partner,
                    name=getattr(rec, f'stockholder_full_name_{i}', False),
                    email=getattr(rec, f'stockholder_email_{i}', False),
                    phone=getattr(rec, f'stockholder_phone_number_{i}', False),
                    label=f'Stockholder {i}',
                )

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        rec._sync_partner_company_type()
        rec._create_spouse_contacts()
        rec._create_stockholder_contacts()
        changed = [k for k, v in vals.items() if k in rec._fields and rec._fields[k].type == 'binary' and v]
        if changed:
            rec._sync_binary_to_documents(changed)
        return rec

    def write(self, vals):

        field_name_map = {
            "full_name_file": ("full_name_file_name", "Name document"),
            "official_id_file": ("official_id_file_name", "Official ID document"),
            "address_file": ("address_file_name", "Address document"),
            "bank_statement_file": ("bank_statement_file_name", "Bank statement document"),
            "rfc_file": ("rfc_file_name", "RFC document"),
            "curp_file": ("curp_file_name", "CURP document"),
        }

        vals_to_write = dict(vals)

        for binary_field_name, (filename_field_name, fallback_filename) in field_name_map.items():
            if binary_field_name not in vals_to_write:
                continue

            binary_value = vals_to_write.get(binary_field_name)
            if not binary_value:
                continue

            incoming_filename_value = vals_to_write.get(filename_field_name)
            if isinstance(incoming_filename_value, str) and incoming_filename_value.strip():
                continue

            vals_to_write[filename_field_name] = fallback_filename

        if 'state' in vals_to_write and vals_to_write.get('state') == 'draft':
            res = super().write(vals_to_write)
        else:
            if self.state == 'draft':
                res = super().write(vals_to_write)
                self._create_spouse_contacts()
                self._create_stockholder_contacts()
                changed = [key for key, value in vals_to_write.items()
                           if key in self._fields and self._fields[key].type == 'binary' and value]
                if changed:
                    self._sync_binary_to_documents(changed)

                self._sync_partner_from_rev(vals=vals_to_write)
                self._sync_partner_company_type()
                return res
            else:
                raise UserError('Can not change data in validated status')
        return res

    def _sync_partner_from_rev(self, vals=None):
        self.ensure_one()
        lead = self.lead_id
        partner = lead and lead.partner_id or False
        if not partner:
            return

        field_map = {
            'full_name': 'name',
            'street_name': 'street',
            'zip_code': 'zip',
            'rfc': 'vat',
            'phone_number': 'phone',
            'email': 'email',
            'suburb': 'colony',
            'external_number': 'colony_number',
            'applies_assets': 'individual_apply_goods',
            'employer_name': 'individual_company_work',
            'job_position': 'individual_company_job_position',
            'employer_phone': 'individual_company_mobile',
            'nationality_person': 'individual_birth_place_nationality',
            'studies': 'individual_level_education',
            'marital_status': 'individual_marital_status',
            'spouse_full_name_1': 'individual_spouses_name',
            'date_of_birth': 'individual_date_birth',
            'curp': 'individual_curp',
            'employer_name': 'individual_company_work',
            'job_position': 'individual_company_job_position',
            'seniority': 'individual_company_seniority_tx',
            'employer_phone': 'individual_company_mobile',
            'applies_assets_person': 'individual_apply_goods',
            'city_rev': 'city',
            'state_rev': 'state_id',
            'curp': 'individual_curp',
            'job_position': 'function',



        }

        def _get_incoming(field_name):
            if vals and field_name in vals:
                return vals[field_name]
            return getattr(self, field_name, False)

        updates = {}

        for src, dst in field_map.items():
            val = _get_incoming(src)
            if val not in (False, None, '', []):
                updates[dst] = val

        state_name = _get_incoming('state_name')
        if state_name and isinstance(state_name, str) and state_name.strip():
            State = self.env['res.country.state']
            state = State.search([('name', 'ilike', state_name.strip())], limit=1)
            if state:
                updates['state_id'] = state.id

        seniority_raw = _get_incoming('seniority')
        if seniority_raw not in (False, None, '', []):
            try:
                updates['individual_company_seniority'] = int(str(seniority_raw).strip())
            except Exception:
                pass

        if not updates:
            return

        def _norm(txt):
            return str(txt or '').strip().lower()

        lives_raw = _get_incoming('lives_in_house')
        if lives_raw not in (False, None, '', []):
            key = _norm(lives_raw)
            LIVES_MAP = {
                'propia': 'own',
                'rentada': 'rented',
                'familiar': 'borrowed',
                'propio': 'own',
                'propietario': 'own',
                'rentado': 'rented',
                'prestado': 'borrowed',
                'family': 'borrowed',
                'familiar (prestada)': 'borrowed',
            }
            mapped = LIVES_MAP.get(key)
            if not mapped:
                if 'prop' in key:
                    mapped = 'own'
                elif 'rent' in key:
                    mapped = 'rented'
                elif 'fam' in key or 'prest' in key:
                    mapped = 'borrowed'
            if mapped:
                updates['individual_dwelling_type'] = mapped

        studies_raw = _get_incoming('studies')
        if studies_raw not in (False, None, '', []):
            key = str(studies_raw).strip().lower()
            STUDIES_MAP = {
                'primaria': 'primary',
                'secundaria': 'secondary',
                'preparatoria': 'high_school',
                'tsu': 'tsu',
                'licenciatura': 'bachelors_degree',
                'ingenieria': 'engineering',
                'maestria': 'masters_degree',
                'doctorado': 'phd',
            }
            mapped = STUDIES_MAP.get(key)
            if mapped:
                updates['individual_level_education'] = mapped

        marital_raw = _get_incoming('marital_status')
        if marital_raw not in (False, None, '', []):
            key = str(marital_raw).strip().lower()
            MARITAL_MAP = {
                'soltero': 'single',
                'casado_bienes_separados': 'married',
                'casado_sociedad_conyugal': 'married',
                'divorciado': 'divorced',
                'viudo': 'widower',
            }
            mapped = MARITAL_MAP.get(key)
            if mapped:
                updates['individual_marital_status'] = mapped

        partner.sudo().with_context(tracking_disable=True).write(updates)

    def action_clear_information(self):
        for rec in self:
            keep_fields = {
                'full_name', 'full_name_file', 'full_name_file_name',
                'curp', 'curp_file', 'curp_file_name',
                'rfc', 'rfc_file', 'rfc_file_name',
                'marital_status', 'nationality', 'address', 'street_name',
                'external_number', 'number', 'internal_number', 'suburb',
                'municipality', 'state_name', 'zip_code',
                'address_file', 'address_file_name',
                'phone_number', 'email', 'official_id', 'official_id_file',
                'official_id_file_name', 'lives_in_house', 'studies', 'profession',
                'occupation', 'employer_name', 'job_position', 'seniority',
                'employer_phone', 'employer_address', 'place_of_birth',
                'date_of_birth', 'applies_assets',
                'company_id', 'company_legal_name', 'company_legal_rep',
                'company_constitutive_act', 'company_notary', 'company_address',
                'company_email', 'worksite_id', 'municipality', 'lot',
                'condominium_id', 'surface', 'related_public_deeds',
                'recent_public_deed', 'total_price', 'total_down_payment',
                'financing', 'term', 'payments_no_interest',
                'payments_interest_1', 'payments_interest_1_25', 'contract_date',
                'special_authorizations', 'internal_fee', 'external_fee',
                'main_amenities', 'additional_amenities',
                'appreciation_on_time', 'appreciation_late',
                'lead_id', 'sale_order_id', 'state','gender',

                'persons_visible', 'stockholders_visible',
            }

            vals_to_clear = {}
            for fname, field in rec._fields.items():
                if fname in keep_fields or fname in ('id', 'create_date', 'write_date'):
                    continue

                if field.store and not field.compute:
                    if field.type in ('char', 'text', 'selection'):
                        vals_to_clear[fname] = False
                    elif field.type in ('boolean', 'many2one', 'binary', 'date'):
                        vals_to_clear[fname] = False
                    elif field.type in ('integer', 'float'):
                        vals_to_clear[fname] = 0

            vals_to_clear.update({
                'persons_visible': 1,
                'stockholders_visible': 1,
                'state': 'draft',
            })

            rec.write(vals_to_clear)


class ContractBriefFileWizard(models.TransientModel):
    _name = 'rev.crm.brief.file.wizard'
    _description = 'Upload file for Contract Brief field'

    brief_id = fields.Many2one('rev.crm.contract.brief', required=True, readonly=True)
    target_field = fields.Char(required=True, readonly=True)
    filename_field = fields.Char(required=True, readonly=True)
    file = fields.Binary(string='File', attachment=True)
    file_name = fields.Char(string='File Name')
    preview_html = fields.Html(string='Preview', sanitize=False, readonly=True)
    preview_attachment_id = fields.Many2one('ir.attachment', readonly=True)

    @api.onchange('file', 'file_name')
    def _onchange_file_preview(self):
        attachment_model = self.env['ir.attachment'].sudo()
        for wizard in self:
            wizard.preview_html = False
            if not wizard.file:
                continue
            mimetype, _ = mimetypes.guess_type(wizard.file_name or '')
            if not mimetype and (wizard.file_name or '').lower().endswith('.pdf'):
                mimetype = 'application/pdf'
            if not mimetype:
                mimetype = 'image/*'
            data_b64 = wizard.file if isinstance(wizard.file, str) else wizard.file.decode()
            if mimetype.startswith('image/'):
                data_uri = f"data:{mimetype};base64,{data_b64}"
                wizard.preview_html = f'<img src="{data_uri}" style="max-width:100%;max-height:480px"/>'
            elif mimetype == 'application/pdf':
                attachment_vals = {
                    'name': wizard.file_name or 'file.pdf',
                    'type': 'binary',
                    'datas': data_b64,
                    'mimetype': 'application/pdf',
                    'res_model': wizard._name,
                    'res_id': wizard.id or 0,
                }
                if wizard.preview_attachment_id:
                    wizard.preview_attachment_id.write(attachment_vals)
                    attachment = wizard.preview_attachment_id
                else:
                    attachment = attachment_model.create(attachment_vals)
                    wizard.preview_attachment_id = attachment
                preview_url = f"/web/content/{attachment.id}?download=false#toolbar=0"
                wizard.preview_html = f'<iframe src="{preview_url}" width="100%" height="480" style="border:0"></iframe>'
            else:
                data_uri = f"data:{mimetype};base64,{data_b64}"
                wizard.preview_html = f'<a href="{data_uri}" target="_blank">{wizard.file_name or "File"}</a>'

    def _get_or_create_base_folder(self, contract):
        Folder = self.env["documents.document"].sudo()  # folders are documents.document with type='folder'

        base = Folder.search([
            ("type", "=", "folder"),
            ("name", "=", "Contracts"),
            ("folder_id", "=", False),
        ], limit=1)

        if not base:
            vals = {
                "name": "Contracts",
                "type": "folder",
                "folder_id": False,
            }
            if "company_id" in Folder._fields and contract.company_id:
                vals["company_id"] = contract.company_id.id
            if "owner_id" in Folder._fields:
                vals["owner_id"] = self.env.user.id
            if "access_internal" in Folder._fields:
                vals["access_internal"] = "edit"

            base = Folder.create(vals)

        return base

    def _get_or_create_contract_folder(self, contract, base_folder):
        Folder = self.env["documents.document"].sudo()

        folder_name = f"Contract {contract.id}"

        f = Folder.search([
            ("type", "=", "folder"),
            ("name", "=", folder_name),
            ("folder_id", "=", base_folder.id),
        ], limit=1)

        if not f:
            vals = {
                "name": folder_name,
                "type": "folder",
                "folder_id": base_folder.id,
            }
            if "company_id" in Folder._fields and contract.company_id:
                vals["company_id"] = contract.company_id.id
            if "owner_id" in Folder._fields:
                vals["owner_id"] = self.env.user.id
            if "access_internal" in Folder._fields:
                vals["access_internal"] = "edit"

            f = Folder.create(vals)

        return f

    def action_save_wizard(self):
        self.ensure_one()

        if not self.file:
            raise UserError(_("Please upload a file."))

        Attachment = self.env["ir.attachment"].sudo()
        Doc = self.env["documents.document"].sudo()

        vals_write = {
            self.target_field: self.file,
            self.filename_field: self.file_name or _("file"),
            "have_contract": True,
        }
        self.brief_id.write(vals_write)

        att = Attachment.search([
            ("res_model", "=", self.brief_id._name),
            ("res_id", "=", self.brief_id.id),
            ("res_field", "=", self.target_field),
        ], order="id desc", limit=1)

        if not att:
            return {"type": "ir.actions.act_window_close"}

        if self.target_field == "contract_file":
            # A) ORIGINAL -> contract_folder_id (MOVE existing doc, don't create duplicate)
            target_folder = self.brief_id.contract_folder_id
            if not target_folder:
                return {"type": "ir.actions.act_window_close"}

            doc_original = Doc.search([("attachment_id", "=", att.id)], limit=1)
            if not doc_original:
                # If not created yet by other logic, create it ONCE
                doc_original = Doc.create({
                    "name": (self.file_name or att.name or "Contract"),
                    "type": "binary",
                    "folder_id": target_folder.id,
                    "attachment_id": att.id,
                    "access_internal": "view",
                    "owner_id": self.env.user.id,
                })
            else:
                doc_original.write({
                    "name": (self.file_name or att.name or doc_original.name),
                    "folder_id": target_folder.id,
                    "access_internal": "view",
                    "owner_id": self.env.user.id,
                })

            sale_order = self.brief_id.sale_order_id
            if not sale_order:
                return {"type": "ir.actions.act_window_close"}

            reservation = self.env["property.reservation"].sudo().search(
                [("order_id", "=", sale_order.id)], limit=1
            )
            if not reservation:
                return {"type": "ir.actions.act_window_close"}

            contract = self.env["property.contract"].sudo().search(
                [("reservation_id", "=", reservation.id)], limit=1
            )
            if not contract:
                return {"type": "ir.actions.act_window_close"}

            base_folder = self._get_or_create_base_folder(contract)
            contract_folder = self._get_or_create_contract_folder(contract, base_folder)

            new_att = att.copy({
                "res_model": "property.contract",
                "res_id": contract.id,
                "res_field": False,
            })

            Doc.create({
                "name": self.file_name or new_att.name or att.name,
                "type": "binary",
                "folder_id": contract_folder.id,
                "attachment_id": new_att.id,
                "owner_id": self.env.user.id,
                "access_internal": "edit",
            })

            return {"type": "ir.actions.act_window_close"}

        self.brief_id._sync_binary_to_documents([self.target_field])
        return {"type": "ir.actions.act_window_close"}

    def unlink(self):
        attachments = self.sudo().mapped('preview_attachment_id')
        result = super().unlink()
        attachments.unlink()
        return result



class DocumentsDocument(models.Model):
    _inherit = "documents.document"

    def _mm_dbg_dump(self, label):
        for r in self:
            try:
                vals = {
                    "id": r.id,
                    "name": r.name,
                    "type": getattr(r, "type", None),
                    "folder_id": r.folder_id.id if getattr(r, "folder_id", False) else None,
                    "folder_name": r.folder_id.name if getattr(r, "folder_id", False) else None,
                    "parent_id": r.parent_id.id if "parent_id" in r._fields and r.parent_id else None,
                    "parent_name": r.parent_id.name if "parent_id" in r._fields and r.parent_id else None,
                    "owner_id": r.owner_id.id if getattr(r, "owner_id", False) else None,
                    "owner_name": r.owner_id.name if getattr(r, "owner_id", False) else None,
                    "company_id": r.company_id.id if "company_id" in r._fields and r.company_id else None,
                    "company_name": r.company_id.name if "company_id" in r._fields and r.company_id else None,
                    "active": r.active if "active" in r._fields else None,
                    "access_internal": getattr(r, "access_internal", None),
                    "attachment_id": r.attachment_id.id if getattr(r, "attachment_id", False) else None,
                    "attachment_name": r.attachment_id.name if getattr(r, "attachment_id", False) else None,
                    "attachment_res_model": r.attachment_id.res_model if getattr(r, "attachment_id", False) else None,
                    "attachment_res_id": r.attachment_id.res_id if getattr(r, "attachment_id", False) else None,
                }
                print(f"[DOCDBG] {label} -> {vals}")
            except Exception as e:
                print("[DOCDBG] dump error:", e)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._mm_dbg_dump("AFTER super().create")

        force_folder_id = self.env.context.get("mm_force_folder_id")
        force_parent_id = self.env.context.get("mm_force_parent_id")

        if force_folder_id:
            write_vals = {}
            if "folder_id" in self._fields:
                write_vals["folder_id"] = force_folder_id
            if force_parent_id and "parent_id" in self._fields:
                write_vals["parent_id"] = force_parent_id

            if write_vals:
                records.sudo().write(write_vals)

                # reload + dump
                records2 = self.sudo().browse(records.ids)
                records2._mm_dbg_dump("AFTER FORCE write (sudo reload)")

                # SQL check
                table = self._table
                for rid in records.ids:
                    self.env.cr.execute(f"SELECT folder_id FROM {table} WHERE id=%s", (rid,))

        return records

    def write(self, vals):
        self._mm_dbg_dump("BEFORE super().write")
        res = super().write(vals)

        self._mm_dbg_dump("AFTER super().write")

        force_folder_id = self.env.context.get("mm_force_folder_id")
        force_parent_id = self.env.context.get("mm_force_parent_id")

        if force_folder_id:
            write_vals = {}
            if "folder_id" in self._fields:
                write_vals["folder_id"] = force_folder_id
            if force_parent_id and "parent_id" in self._fields:
                write_vals["parent_id"] = force_parent_id


            if write_vals:
                super(DocumentsDocument, self.sudo()).write(write_vals)

                # reload + dump
                rec2 = self.sudo().browse(self.ids)
                rec2._mm_dbg_dump("AFTER FORCE write (sudo reload)")

                # SQL check
                table = self._table
                for rid in self.ids:
                    self.env.cr.execute(f"SELECT folder_id FROM {table} WHERE id=%s", (rid,))

        return res


