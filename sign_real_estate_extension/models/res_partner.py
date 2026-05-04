# -*- coding: utf-8 -*-
from odoo import models, fields  # type: ignore


class SignRealEstateResPartner(models.Model):
    _inherit = 'res.partner'

    property_name = fields.Char(string='Property name')
    property_lot = fields.Char(string='Lot of property')
    property_footage = fields.Char(string='Property footage')
    property_amount = fields.Char(string='Property sale price')
    monthly_payments_1_to_48 = fields.Char(string='monthly payments from month 1 to 48')
    monthly_payments_49_to_120 = fields.Char(
        string='monthly payments from month 49 to 120'
    )
    monthly_payments_121_to_180 = fields.Char(
        string='monthly payments from month 121 to 180'
    )
    monthly_payments_181_to_240 = fields.Char(
        string='monthly payments from month 181 to 240'
    )
    property_internal_code = fields.Char(string='Property default code')
    amount_finance = fields.Float(string="Amount Financed")
    hitch = fields.Float(string="Hitch")
    condominium_name = fields.Char(string='Condominium')
    hitch_text = fields.Char(string="Hitch text")
    finance_months = fields.Integer(string="finance months")
    total_sale_amount = fields.Float(string="Total Sale Amount")
    condominium_name = fields.Char(string='Condominium')
    monthly_payments_1_to_48_text = fields.Char(string='monthly payments 1 to 48 (text)')
    monthly_payments_49_to_120_text = fields.Char(string='monthly payments 49 to 120 (text)')
    monthly_payments_121_to_180_text = fields.Char(string='monthly payments 121 to 180 (text)')
    monthly_payments_181_to_240_text = fields.Char(string='monthly payments 181 to 240 (text)')
    loan_lines_text = fields.Text(string='Loan lines (text)')
    property_attachment_1_name = fields.Char(string="Property Attachment #1 (Name)")
    property_attachment_1_url = fields.Char(string="Property Attachment #1 (URL)")
    vat_amount = fields.Float(string="VAT Amount")
    vat_amount_text = fields.Char(string="VAT Amount (Text)")
    total_without_tax = fields.Float(string="Total Without VAT")
    total_without_tax_text = fields.Char(string="Total Without VAT (Text)")
    maintenance_fee = fields.Float(string="Maintenance Fee")
    maintenance_fee_text = fields.Char(string="Maintenance Fee (Text)")
    property_footage_text = fields.Char(string="Property Footage (Text)")
    property_lot_text = fields.Char(string="Property Lot (Text)")
    property_pricing = fields.Float(string="Property Pricing")
    property_pricing_text = fields.Char(string="Property Pricing (Text)")
    related_public_deeds = fields.Char(string="Related Public Deeds")
    recent_public_deed = fields.Char(string="Recent Public Deed")
    otherwise_clause = fields.Char(string="Otherwise Clause")
    compliance_clause = fields.Char(string="If Payment is Made According to the Scheme and All Receipts are Delivered")
    company_legal_name = fields.Char(string="Legal Name")
    company_legal_rep = fields.Char(string="Legal Representative")
    company_constitutive_act = fields.Char(string="Constitutive Deed")
    company_notary = fields.Char(string="Current Notary")
    company_address = fields.Char(string="Address")
    company_email = fields.Char(string="Email")
    partner_related_public_deeds = fields.Char(string=" partnerRelated Public Deeds")
    partner_recent_public_deed = fields.Char(string=" partnerMost Recent Public Deed")
    partner_legal_name = fields.Char(string="Partner Legal Name")
    partner_legal_representative = fields.Char(string="Partner Legal Representative")
    partner_constitutive_deed = fields.Char(string=" partnerConstitutive Deed")
    partner_current_notary = fields.Char(string="partner Current Notary")
    partner_registered_address = fields.Char(string="Registered Address")
    partner_contact_email = fields.Char(string="Partner Contact Email")
    person_type_client = fields.Selection(
        selection=[
            ('fisica', 'Natural Person'),
            ('morial', 'Legal Entity'),
            ('coopropiedad', 'Co-Ownership'),
        ],
        string='Person Type (Client)',
    )

    full_name_client = fields.Char(string='Full Name (Client)')
    curp_client = fields.Char(string='CURP (Client)')
    rfc_client = fields.Char(string='RFC (Client)')
    marital_status_client = fields.Selection(
        selection=[
            ('soltero', 'SINGLE'),
            ('casado_bienes_separados', 'MARRIED SEPARATE PROPERTY'),
            ('casado_sociedad_conyugal', 'MARRIED COMMUNITY PROPERTY'),
        ],
        string='Marital Status (Client)',
    )
    nationality_client = fields.Char(string='Nationality (Client)')
    address_client = fields.Text(string='Address (Client)')
    phone_number_client = fields.Char(string='Phone Number (Client)')
    email_client = fields.Char(string='Email (Client)')
    official_id_client = fields.Char(string='Official ID (Client)')
    lives_in_house_client = fields.Selection(
        selection=[
            ('propia', 'OWNED'),
            ('rentada', 'RENTED'),
            ('familiar', 'FAMILY'),
        ],
        string='Lives in a house (Client)',
    )
    studies_client = fields.Selection(
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
        string='Studies (Client)',
    )
    profession_client = fields.Char(string='Profession (Client)')
    occupation_client = fields.Char(string='Occupation (Client)')
    employer_name_client = fields.Char(string='Employer Name (Client)')
    job_position_client = fields.Char(string='Job Position (Client)')
    seniority_client = fields.Char(string='Seniority (Client)')
    employer_phone_client = fields.Char(string='Employer Phone (Client)')
    employer_address_client = fields.Text(string='Employer Address (Client)')
    place_of_birth_client = fields.Char(string='Place of Birth (Client)')
    date_of_birth_client = fields.Date(string='Date of Birth (Client)')
    applies_assets_client = fields.Char(string='Applies Assets (Client)')
    first_names_client = fields.Char(string='First Names (Client)')
    last_name_materno_client = fields.Char(string='Maternal Last Name (Client)')
    last_name_paterno_client = fields.Char(string='Paternal Last Name (Client)')

    stockholder_full_name_1 = fields.Char(string="Stockholder Full Name 1")
    stockholder_address_1 = fields.Text(string="Stockholder Address 1")
    stockholder_lives_in_house_1 = fields.Boolean(string="Stockholder Lives in House 1")
    stockholder_studies_1 = fields.Char(string="Stockholder Studies 1")
    stockholder_profession_1 = fields.Char(string="Stockholder Profession 1")
    stockholder_marital_status_1 = fields.Selection(
        selection=[
            ("single", "SINGLE"),
            ("married_separate_property", "MARRIED SEPARATE PROPERTY"),
            ("married_community_property", "MARRIED COMMUNITY PROPERTY"),
        ],
        string="Stockholder Marital Status 1",
    )
    stockholder_phone_number_1 = fields.Char(string="Stockholder Phone Number 1")
    stockholder_email_1 = fields.Char(string="Stockholder Email 1")
    stockholder_nationality_1 = fields.Char(string="Stockholder Nationality 1")
    stockholder_rfc_1 = fields.Char(string="Stockholder RFC 1")
    stockholder_curp_1 = fields.Char(string="Stockholder CURP 1")
    stockholder_occupation_1 = fields.Char(string="Stockholder Occupation 1")
    stockholder_job_position_1 = fields.Char(string="Stockholder Job Position 1")
    stockholder_seniority_1 = fields.Char(string="Stockholder Seniority 1")
    stockholder_employer_name_1 = fields.Char(string="Stockholder Employer Name 1")
    stockholder_employer_phone_1 = fields.Char(string="Stockholder Employer Phone 1")
    stockholder_employer_address_1 = fields.Char(string="Stockholder Employer Address 1")
    stockholder_applies_assets_1 = fields.Char(string="Stockholder Applies Assets 1")
    stockholder_shares_percentage_1 = fields.Char(string="Stockholder Shares Percentage 1")

    stockholder_full_name_2 = fields.Char(string="Stockholder Full Name 2")
    stockholder_address_2 = fields.Text(string="Stockholder Address 2")
    stockholder_lives_in_house_2 = fields.Boolean(string="Stockholder Lives in House 2")
    stockholder_studies_2 = fields.Char(string="Stockholder Studies 2")
    stockholder_profession_2 = fields.Char(string="Stockholder Profession 2")
    stockholder_marital_status_2 = fields.Selection(
        selection=[
            ("single", "SINGLE"),
            ("married_separate_property", "MARRIED SEPARATE PROPERTY"),
            ("married_community_property", "MARRIED COMMUNITY PROPERTY"),
        ],
        string="Stockholder Marital Status 2",
    )
    stockholder_phone_number_2 = fields.Char(string="Stockholder Phone Number 2")
    stockholder_email_2 = fields.Char(string="Stockholder Email 2")
    stockholder_nationality_2 = fields.Char(string="Stockholder Nationality 2")
    stockholder_rfc_2 = fields.Char(string="Stockholder RFC 2")
    stockholder_curp_2 = fields.Char(string="Stockholder CURP 2")
    stockholder_occupation_2 = fields.Char(string="Stockholder Occupation 2")
    stockholder_job_position_2 = fields.Char(string="Stockholder Job Position 2")
    stockholder_seniority_2 = fields.Char(string="Stockholder Seniority 2")
    stockholder_employer_name_2 = fields.Char(string="Stockholder Employer Name 2")
    stockholder_employer_phone_2 = fields.Char(string="Stockholder Employer Phone 2")
    stockholder_employer_address_2 = fields.Char(string="Stockholder Employer Address 2")
    stockholder_applies_assets_2 = fields.Char(string="Stockholder Applies Assets 2")
    stockholder_shares_percentage_2 = fields.Char(string="Stockholder Shares Percentage 2")

    stockholder_full_name_3 = fields.Char(string="Stockholder Full Name 3")
    stockholder_address_3 = fields.Text(string="Stockholder Address 3")
    stockholder_lives_in_house_3 = fields.Boolean(string="Stockholder Lives in House 3")
    stockholder_studies_3 = fields.Char(string="Stockholder Studies 3")
    stockholder_profession_3 = fields.Char(string="Stockholder Profession 3")
    stockholder_marital_status_3 = fields.Selection(
        selection=[
            ("single", "SINGLE"),
            ("married_separate_property", "MARRIED SEPARATE PROPERTY"),
            ("married_community_property", "MARRIED COMMUNITY PROPERTY"),
        ],
        string="Stockholder Marital Status 3",
    )
    stockholder_phone_number_3 = fields.Char(string="Stockholder Phone Number 3")
    stockholder_email_3 = fields.Char(string="Stockholder Email 3")
    stockholder_nationality_3 = fields.Char(string="Stockholder Nationality 3")
    stockholder_rfc_3 = fields.Char(string="Stockholder RFC 3")
    stockholder_curp_3 = fields.Char(string="Stockholder CURP 3")
    stockholder_occupation_3 = fields.Char(string="Stockholder Occupation 3")
    stockholder_job_position_3 = fields.Char(string="Stockholder Job Position 3")
    stockholder_seniority_3 = fields.Char(string="Stockholder Seniority 3")
    stockholder_employer_name_3 = fields.Char(string="Stockholder Employer Name 3")
    stockholder_employer_phone_3 = fields.Char(string="Stockholder Employer Phone 3")
    stockholder_employer_address_3 = fields.Char(string="Stockholder Employer Address 3")
    stockholder_applies_assets_3 = fields.Char(string="Stockholder Applies Assets 3")
    stockholder_shares_percentage_3 = fields.Char(string="Stockholder Shares Percentage 3")

    stockholder_full_name_4 = fields.Char(string="Stockholder Full Name 4")
    stockholder_address_4 = fields.Text(string="Stockholder Address 4")
    stockholder_lives_in_house_4 = fields.Boolean(string="Stockholder Lives in House 4")
    stockholder_studies_4 = fields.Char(string="Stockholder Studies 4")
    stockholder_profession_4 = fields.Char(string="Stockholder Profession 4")
    stockholder_marital_status_4 = fields.Selection(
        selection=[
            ("single", "SINGLE"),
            ("married_separate_property", "MARRIED SEPARATE PROPERTY"),
            ("married_community_property", "MARRIED COMMUNITY PROPERTY"),
        ],
        string="Stockholder Marital Status 4",
    )
    stockholder_phone_number_4 = fields.Char(string="Stockholder Phone Number 4")
    stockholder_email_4 = fields.Char(string="Stockholder Email 4")
    stockholder_nationality_4 = fields.Char(string="Stockholder Nationality 4")
    stockholder_rfc_4 = fields.Char(string="Stockholder RFC 4")
    stockholder_curp_4 = fields.Char(string="Stockholder CURP 4")
    stockholder_occupation_4 = fields.Char(string="Stockholder Occupation 4")
    stockholder_job_position_4 = fields.Char(string="Stockholder Job Position 4")
    stockholder_seniority_4 = fields.Char(string="Stockholder Seniority 4")
    stockholder_employer_name_4 = fields.Char(string="Stockholder Employer Name 4")
    stockholder_employer_phone_4 = fields.Char(string="Stockholder Employer Phone 4")
    stockholder_employer_address_4 = fields.Char(string="Stockholder Employer Address 4")
    stockholder_applies_assets_4 = fields.Char(string="Stockholder Applies Assets 4")
    stockholder_shares_percentage_4 = fields.Char(string="Stockholder Shares Percentage 4")

    stockholder_full_name_5 = fields.Char(string="Stockholder Full Name 5")
    stockholder_address_5 = fields.Text(string="Stockholder Address 5")
    stockholder_lives_in_house_5 = fields.Boolean(string="Stockholder Lives in House 5")
    stockholder_studies_5 = fields.Char(string="Stockholder Studies 5")
    stockholder_profession_5 = fields.Char(string="Stockholder Profession 5")
    stockholder_marital_status_5 = fields.Selection(
        selection=[
            ("single", "SINGLE"),
            ("married_separate_property", "MARRIED SEPARATE PROPERTY"),
            ("married_community_property", "MARRIED COMMUNITY PROPERTY"),
        ],
        string="Stockholder Marital Status 5",
    )
    stockholder_phone_number_5 = fields.Char(string="Stockholder Phone Number 5")
    stockholder_email_5 = fields.Char(string="Stockholder Email 5")
    stockholder_nationality_5 = fields.Char(string="Stockholder Nationality 5")
    stockholder_rfc_5 = fields.Char(string="Stockholder RFC 5")
    stockholder_curp_5 = fields.Char(string="Stockholder CURP 5")
    stockholder_occupation_5 = fields.Char(string="Stockholder Occupation 5")
    stockholder_job_position_5 = fields.Char(string="Stockholder Job Position 5")
    stockholder_seniority_5 = fields.Char(string="Stockholder Seniority 5")
    stockholder_employer_name_5 = fields.Char(string="Stockholder Employer Name 5")
    stockholder_employer_phone_5 = fields.Char(string="Stockholder Employer Phone 5")
    stockholder_employer_address_5 = fields.Char(string="Stockholder Employer Address 5")
    stockholder_applies_assets_5 = fields.Char(string="Stockholder Applies Assets 5")
    stockholder_shares_percentage_5 = fields.Char(string="Stockholder Shares Percentage 5")

    stockholder_full_name_6 = fields.Char(string="Stockholder Full Name 6")
    stockholder_address_6 = fields.Text(string="Stockholder Address 6")
    stockholder_lives_in_house_6 = fields.Boolean(string="Stockholder Lives in House 6")
    stockholder_studies_6 = fields.Char(string="Stockholder Studies 6")
    stockholder_profession_6 = fields.Char(string="Stockholder Profession 6")
    stockholder_marital_status_6 = fields.Selection(
        selection=[
            ("single", "SINGLE"),
            ("married_separate_property", "MARRIED SEPARATE PROPERTY"),
            ("married_community_property", "MARRIED COMMUNITY PROPERTY"),
        ],
        string="Stockholder Marital Status 6",
    )
    stockholder_phone_number_6 = fields.Char(string="Stockholder Phone Number 6")
    stockholder_email_6 = fields.Char(string="Stockholder Email 6")
    stockholder_nationality_6 = fields.Char(string="Stockholder Nationality 6")
    stockholder_rfc_6 = fields.Char(string="Stockholder RFC 6")
    stockholder_curp_6 = fields.Char(string="Stockholder CURP 6")
    stockholder_occupation_6 = fields.Char(string="Stockholder Occupation 6")
    stockholder_job_position_6 = fields.Char(string="Stockholder Job Position 6")
    stockholder_seniority_6 = fields.Char(string="Stockholder Seniority 6")
    stockholder_employer_name_6 = fields.Char(string="Stockholder Employer Name 6")
    stockholder_employer_phone_6 = fields.Char(string="Stockholder Employer Phone 6")
    stockholder_employer_address_6 = fields.Char(string="Stockholder Employer Address 6")
    stockholder_applies_assets_6 = fields.Char(string="Stockholder Applies Assets 6")
    stockholder_shares_percentage_6 = fields.Char(string="Stockholder Shares Percentage 6")

    stockholder_full_name_7 = fields.Char(string="Stockholder Full Name 7")
    stockholder_address_7 = fields.Text(string="Stockholder Address 7")
    stockholder_lives_in_house_7 = fields.Boolean(string="Stockholder Lives in House 7")
    stockholder_studies_7 = fields.Char(string="Stockholder Studies 7")
    stockholder_profession_7 = fields.Char(string="Stockholder Profession 7")
    stockholder_marital_status_7 = fields.Selection(
        selection=[
            ("single", "SINGLE"),
            ("married_separate_property", "MARRIED SEPARATE PROPERTY"),
            ("married_community_property", "MARRIED COMMUNITY PROPERTY"),
        ],
        string="Stockholder Marital Status 7",
    )
    stockholder_phone_number_7 = fields.Char(string="Stockholder Phone Number 7")
    stockholder_email_7 = fields.Char(string="Stockholder Email 7")
    stockholder_nationality_7 = fields.Char(string="Stockholder Nationality 7")
    stockholder_rfc_7 = fields.Char(string="Stockholder RFC 7")
    stockholder_curp_7 = fields.Char(string="Stockholder CURP 7")
    stockholder_occupation_7 = fields.Char(string="Stockholder Occupation 7")
    stockholder_job_position_7 = fields.Char(string="Stockholder Job Position 7")
    stockholder_seniority_7 = fields.Char(string="Stockholder Seniority 7")
    stockholder_employer_name_7 = fields.Char(string="Stockholder Employer Name 7")
    stockholder_employer_phone_7 = fields.Char(string="Stockholder Employer Phone 7")
    stockholder_employer_address_7 = fields.Char(string="Stockholder Employer Address 7")
    stockholder_applies_assets_7 = fields.Char(string="Stockholder Applies Assets 7")
    stockholder_shares_percentage_7 = fields.Char(string="Stockholder Shares Percentage 7")

    stockholder_full_name_8 = fields.Char(string="Stockholder Full Name 8")
    stockholder_address_8 = fields.Text(string="Stockholder Address 8")
    stockholder_lives_in_house_8 = fields.Boolean(string="Stockholder Lives in House 8")
    stockholder_studies_8 = fields.Char(string="Stockholder Studies 8")
    stockholder_profession_8 = fields.Char(string="Stockholder Profession 8")
    stockholder_marital_status_8 = fields.Selection(
        selection=[
            ("single", "SINGLE"),
            ("married_separate_property", "MARRIED SEPARATE PROPERTY"),
            ("married_community_property", "MARRIED COMMUNITY PROPERTY"),
        ],
        string="Stockholder Marital Status 8",
    )
    stockholder_phone_number_8 = fields.Char(string="Stockholder Phone Number 8")
    stockholder_email_8 = fields.Char(string="Stockholder Email 8")
    stockholder_nationality_8 = fields.Char(string="Stockholder Nationality 8")
    stockholder_rfc_8 = fields.Char(string="Stockholder RFC 8")
    stockholder_curp_8 = fields.Char(string="Stockholder CURP 8")
    stockholder_occupation_8 = fields.Char(string="Stockholder Occupation 8")
    stockholder_job_position_8 = fields.Char(string="Stockholder Job Position 8")
    stockholder_seniority_8 = fields.Char(string="Stockholder Seniority 8")
    stockholder_employer_name_8 = fields.Char(string="Stockholder Employer Name 8")
    stockholder_employer_phone_8 = fields.Char(string="Stockholder Employer Phone 8")
    stockholder_employer_address_8 = fields.Char(string="Stockholder Employer Address 8")
    stockholder_applies_assets_8 = fields.Char(string="Stockholder Applies Assets 8")
    stockholder_shares_percentage_8 = fields.Char(string="Stockholder Shares Percentage 8")

    stockholder_full_name_9 = fields.Char(string="Stockholder Full Name 9")
    stockholder_address_9 = fields.Text(string="Stockholder Address 9")
    stockholder_lives_in_house_9 = fields.Boolean(string="Stockholder Lives in House 9")
    stockholder_studies_9 = fields.Char(string="Stockholder Studies 9")
    stockholder_profession_9 = fields.Char(string="Stockholder Profession 9")
    stockholder_marital_status_9 = fields.Selection(
        selection=[
            ("single", "SINGLE"),
            ("married_separate_property", "MARRIED SEPARATE PROPERTY"),
            ("married_community_property", "MARRIED COMMUNITY PROPERTY"),
        ],
        string="Stockholder Marital Status 9",
    )
    stockholder_phone_number_9 = fields.Char(string="Stockholder Phone Number 9")
    stockholder_email_9 = fields.Char(string="Stockholder Email 9")
    stockholder_nationality_9 = fields.Char(string="Stockholder Nationality 9")
    stockholder_rfc_9 = fields.Char(string="Stockholder RFC 9")
    stockholder_curp_9 = fields.Char(string="Stockholder CURP 9")
    stockholder_occupation_9 = fields.Char(string="Stockholder Occupation 9")
    stockholder_job_position_9 = fields.Char(string="Stockholder Job Position 9")
    stockholder_seniority_9 = fields.Char(string="Stockholder Seniority 9")
    stockholder_employer_name_9 = fields.Char(string="Stockholder Employer Name 9")
    stockholder_employer_phone_9 = fields.Char(string="Stockholder Employer Phone 9")
    stockholder_employer_address_9 = fields.Char(string="Stockholder Employer Address 9")
    stockholder_applies_assets_9 = fields.Char(string="Stockholder Applies Assets 9")
    stockholder_shares_percentage_9 = fields.Char(string="Stockholder Shares Percentage 9")

    stockholder_full_name_10 = fields.Char(string="Stockholder Full Name 10")
    stockholder_address_10 = fields.Text(string="Stockholder Address 10")
    stockholder_lives_in_house_10 = fields.Boolean(string="Stockholder Lives in House 10")
    stockholder_studies_10 = fields.Char(string="Stockholder Studies 10")
    stockholder_profession_10 = fields.Char(string="Stockholder Profession 10")
    stockholder_marital_status_10 = fields.Selection(
        selection=[
            ("single", "SINGLE"),
            ("married_separate_property", "MARRIED SEPARATE PROPERTY"),
            ("married_community_property", "MARRIED COMMUNITY PROPERTY"),
        ],
        string="Stockholder Marital Status 10",
    )
    stockholder_phone_number_10 = fields.Char(string="Stockholder Phone Number 10")
    stockholder_email_10 = fields.Char(string="Stockholder Email 10")
    stockholder_nationality_10 = fields.Char(string="Stockholder Nationality 10")
    stockholder_rfc_10 = fields.Char(string="Stockholder RFC 10")
    stockholder_curp_10 = fields.Char(string="Stockholder CURP 10")
    stockholder_occupation_10 = fields.Char(string="Stockholder Occupation 10")
    stockholder_job_position_10 = fields.Char(string="Stockholder Job Position 10")
    stockholder_seniority_10 = fields.Char(string="Stockholder Seniority 10")
    stockholder_employer_name_10 = fields.Char(string="Stockholder Employer Name 10")
    stockholder_employer_phone_10 = fields.Char(string="Stockholder Employer Phone 10")
    stockholder_employer_address_10 = fields.Char(string="Stockholder Employer Address 10")
    stockholder_applies_assets_10 = fields.Char(string="Stockholder Applies Assets 10")
    stockholder_shares_percentage_10 = fields.Char(string="Stockholder Shares Percentage 10")

    street_name_1 = fields.Char(string='Street 1')
    external_number_1 = fields.Char(string='Exterior Number 1')
    number_1 = fields.Char(string='Number 1')
    internal_number_1 = fields.Char(string='Interior Number 1')
    suburb_1 = fields.Char(string='Neighborhood / Suburb 1')
    municipality_1 = fields.Char(string='Municipality / City 1')
    state_name_1 = fields.Char(string='State 1')
    zip_code_1 = fields.Char(string='ZIP Code 1')

    street_name_2 = fields.Char(string='Street 2')
    external_number_2 = fields.Char(string='Exterior Number 2')
    number_2 = fields.Char(string='Number 2')
    internal_number_2 = fields.Char(string='Interior Number 2')
    suburb_2 = fields.Char(string='Neighborhood / Suburb 2')
    municipality_2 = fields.Char(string='Municipality / City 2')
    state_name_2 = fields.Char(string='State 2')
    zip_code_2 = fields.Char(string='ZIP Code 2')

    street_name_3 = fields.Char(string='Street 3')
    external_number_3 = fields.Char(string='Exterior Number 3')
    number_3 = fields.Char(string='Number 3')
    internal_number_3 = fields.Char(string='Interior Number 3')
    suburb_3 = fields.Char(string='Neighborhood / Suburb 3')
    municipality_3 = fields.Char(string='Municipality / City 3')
    state_name_3 = fields.Char(string='State 3')
    zip_code_3 = fields.Char(string='ZIP Code 3')

    street_name_4 = fields.Char(string='Street 4')
    external_number_4 = fields.Char(string='Exterior Number 4')
    number_4 = fields.Char(string='Number 4')
    internal_number_4 = fields.Char(string='Interior Number 4')
    suburb_4 = fields.Char(string='Neighborhood / Suburb 4')
    municipality_4 = fields.Char(string='Municipality / City 4')
    state_name_4 = fields.Char(string='State 4')
    zip_code_4 = fields.Char(string='ZIP Code 4')

    street_name_5 = fields.Char(string='Street 5')
    external_number_5 = fields.Char(string='Exterior Number 5')
    number_5 = fields.Char(string='Number 5')
    internal_number_5 = fields.Char(string='Interior Number 5')
    suburb_5 = fields.Char(string='Neighborhood / Suburb 5')
    municipality_5 = fields.Char(string='Municipality / City 5')
    state_name_5 = fields.Char(string='State 5')
    zip_code_5 = fields.Char(string='ZIP Code 5')

    street_name_6 = fields.Char(string='Street 6')
    external_number_6 = fields.Char(string='Exterior Number 6')
    number_6 = fields.Char(string='Number 6')
    internal_number_6 = fields.Char(string='Interior Number 6')
    suburb_6 = fields.Char(string='Neighborhood / Suburb 6')
    municipality_6 = fields.Char(string='Municipality / City 6')
    state_name_6 = fields.Char(string='State 6')
    zip_code_6 = fields.Char(string='ZIP Code 6')

    street_name_7 = fields.Char(string='Street 7')
    external_number_7 = fields.Char(string='Exterior Number 7')
    number_7 = fields.Char(string='Number 7')
    internal_number_7 = fields.Char(string='Interior Number 7')
    suburb_7 = fields.Char(string='Neighborhood / Suburb 7')
    municipality_7 = fields.Char(string='Municipality / City 7')
    state_name_7 = fields.Char(string='State 7')
    zip_code_7 = fields.Char(string='ZIP Code 7')

    street_name_8 = fields.Char(string='Street 8')
    external_number_8 = fields.Char(string='Exterior Number 8')
    number_8 = fields.Char(string='Number 8')
    internal_number_8 = fields.Char(string='Interior Number 8')
    suburb_8 = fields.Char(string='Neighborhood / Suburb 8')
    municipality_8 = fields.Char(string='Municipality / City 8')
    state_name_8 = fields.Char(string='State 8')
    zip_code_8 = fields.Char(string='ZIP Code 8')

    street_name_9 = fields.Char(string='Street 9')
    external_number_9 = fields.Char(string='Exterior Number 9')
    number_9 = fields.Char(string='Number 9')
    internal_number_9 = fields.Char(string='Interior Number 9')
    suburb_9 = fields.Char(string='Neighborhood / Suburb 9')
    municipality_9 = fields.Char(string='Municipality / City 9')
    state_name_9 = fields.Char(string='State 9')
    zip_code_9 = fields.Char(string='ZIP Code 9')

    street_name_10 = fields.Char(string='Street 10')
    external_number_10 = fields.Char(string='Exterior Number 10')
    number_10 = fields.Char(string='Number 10')
    internal_number_10 = fields.Char(string='Interior Number 10')
    suburb_10 = fields.Char(string='Neighborhood / Suburb 10')
    municipality_10 = fields.Char(string='Municipality / City 10')
    state_name_10 = fields.Char(string='State 10')
    zip_code_10 = fields.Char(string='ZIP Code 10')

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


