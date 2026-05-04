# -*- coding: utf-8 -*-

from odoo.api import Environment
from odoo.addons.fastapi.dependencies import paging, odoo_env
from odoo.addons.fastapi.schemas import PagedCollection, Paging
from odoo.addons.real_estate_bits_api.routers.interfaces import AmenityInfo, AddressInfo, DepartmentInfo, DevelopmentInfo, LeadCreateRequest, RangeInfo
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security.api_key import APIKeyHeader
from typing import Annotated
import logging

_logger = logging.getLogger(__name__)

API_KEY_NAME = 'X-API-Key'
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

router = APIRouter(tags=['real_estate'])

def validate_api_key(request: Request, api_key: str = Depends(api_key_header), env: Environment = Depends(odoo_env)):
    endpoint_identifier = request.url.path.split('/')[-1]
    endpoint = env['fastapi.endpoint'].search([
        ('app', '=', 'real_estate'),
        ('root_path', '=', endpoint_identifier),
    ], limit=1)
    endpoint = env['fastapi.endpoint'].search([('app', '=', 'real_estate')], limit=1)
    if not endpoint or not api_key or api_key != endpoint.real_estate_api_key:
        raise HTTPException(
            status_code=403,
            detail="Could not validate API key"
        )
    return api_key

@router.get('/developments', response_model=PagedCollection[DevelopmentInfo])
def get_developments(
    paging: Annotated[Paging, Depends(paging)],
    env: Annotated[Environment, Depends(odoo_env)],
    api_key: str = Depends(validate_api_key),
):
    domain = [
        ('is_demo_worksite', '=', False),
        ('company_id', '!=', False),
        ('parent_id', '=', False),
    ]
    allowed_ids = env.context.get('allowed_company_ids') or env.user.company_ids.ids
    developments = (
        env['project.worksite']
        .with_context(allowed_company_ids=allowed_ids)
        .search(domain, limit=paging.limit, offset=paging.offset)
    )

    count = len(developments)
    records = []

    if developments:
        Condo = env['condominium.worksite']
        for development in developments:
            condos = Condo.search([
                ('parent_id.parent_id', '=', development.id),
                ('property_ids', '!=', False),
            ])
            condo_props = condos.mapped('property_ids')
            units = condo_props.filtered(lambda u: u.state == 'free').sorted('list_price')

            if units:
                latitude = False
                longitude = False
                try:
                    if development.address:
                        if ';' not in development.address:
                            raise ValueError("invalid coords")
                        coords = development.address.split(';')
                        if len(coords) != 2:
                            raise ValueError("invalid coords")
                        latitude = float(coords[0])
                        longitude = float(coords[1])
                except ValueError:
                    pass

                departments = []
                for unit in units:
                    departments.append(DepartmentInfo(
                        id=unit.id,
                        code=unit.default_code,
                        name=unit.name,
                        bathrooms=unit.number_bathrooms,
                        bedrooms=unit.number_bedrooms,
                        default_code=unit.default_code,
                        address=unit.address,
                        property_date=unit.property_date,
                        estimated_date=unit.estimated_date,
                        worksite_id=unit.worksite_id.name,
                        project_worksite_id=unit.project_worksite_id.name,
                        project_type=unit.project_type,
                        company_id=unit.company_id.name,
                        price_per_m=unit.price_per_m,
                        property_area=unit.property_area,
                        net_price=unit.net_price,
                        note=unit.note,
                        state=unit.state
                    ))
                address_parts = [
                    development.street,
                    development.city,
                    development.street2,
                    development.zip,
                    development.state_id.name
                ]
                records.append(DevelopmentInfo(
                    id=development.id,
                    code=development.default_code,
                    name=development.name,
                    address=AddressInfo(
                        street=development.street,
                        street2=development.street2,
                        city=development.city,
                        zip=development.zip,
                        state=development.state_id.name if development.state_id else False,
                        full=', '.join([part for part in address_parts if part]),
                    ),
                    latitude=str(latitude) if latitude else False,
                    longitude=str(longitude) if longitude else False,
                    zone=development.region_id.name if development.region_id else False,
                    image=development.image_1920,
                    departments=departments,
                    amenities=[
                        AmenityInfo(
                            name=amenity.name,
                            code=amenity.code,
                        ) for amenity in development.amenities_ids
                    ],
                    area_range=RangeInfo(
                        min=min(units.mapped('converted_area')),
                        max=max(units.mapped('converted_area')),
                    ),
                    price_range=RangeInfo(
                        min=min(units.mapped('list_price')),
                        max=max(units.mapped('list_price')),
                    ),
                    bedrooms_range=RangeInfo(
                        min=float(min(units.mapped('number_bedrooms'))),
                        max=float(max(units.mapped('number_bedrooms'))),
                    ),
                    bathrooms_range=RangeInfo(
                        min=min(units.mapped('number_bathrooms')),
                        max=max(units.mapped('number_bathrooms')),
                    ),
                    company=development.company_id.name,
                    attachment_line_ids=development.attachment_line_ids.ids if development.attachment_line_ids else [],
                    property_plan_ids=development.property_plan_ids.ids if development.property_plan_ids else [],
                    launch_date=development.launch_date,
                    partner_id=development.partner_id.sudo().name if development.partner_id else False,
                    company_id=development.company_id.name,
                ))
            else:
                count -= 1

    return PagedCollection[DevelopmentInfo](
        count=count,
        items=records,
    )

@router.post('/create_lead', response_model=bool, )
def create_lead(
    lead_data: LeadCreateRequest,
    env: Annotated[Environment, Depends(odoo_env)],
    api_key: str = Depends(validate_api_key),
):
    try:
        medium = False
        if lead_data.medium:
            medium = env['utm.medium'].search([('name', '=', 'Website')], limit=1)
        env['crm.lead'].create({
            'name': lead_data.name,
            'description': lead_data.description,
            'contact_name': lead_data.name,
            'bci_name': lead_data.name,
            'email_from': lead_data.email,
            'phone': lead_data.phone,
            'team_id': lead_data.team_id,
            'user_id': lead_data.user_id,
            'medium_id': medium.id if medium else False,
            'property_id': lead_data.property_id,
        })
        return True
    except Exception:
        return False
