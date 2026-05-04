from pydantic import BaseModel
from typing import List, Union
from datetime import date

# -------------------------------------------------------------------------
# INTERFACES RESPONSE
# -------------------------------------------------------------------------

class AmenityInfo(BaseModel):
    name: str
    code: Union[str, bool]

class AddressInfo(BaseModel):
    street: Union[str, bool]
    street2: Union[str, bool]
    city: Union[str, bool]
    zip: Union[str, bool]
    state: Union[str, bool]
    full: Union[str, bool]

class RangeInfo(BaseModel):
    min: float
    max: float

class DepartmentInfo(BaseModel):
    id: int
    code: Union[str, bool]
    name: str
    bathrooms: float
    bedrooms: int
    # price: int
    default_code: str
    address: Union[str, bool]
    property_date: Union[date, bool]
    estimated_date: Union[date, bool]
    worksite_id: Union[str, bool]
    project_worksite_id: Union[str, bool]
    project_type: Union[str, bool]
    company_id: Union[str, bool]
    # promotion_ids: str
    price_per_m: float
    property_area: float
    net_price: float
    address: Union[str, bool]
    note: Union[str, bool]
    state: Union[str, bool]
    

class DevelopmentInfo(BaseModel):
    id: int
    code: Union[str, bool]
    name: str
    # url: Union[str, bool]
    address: AddressInfo
    latitude: Union[str, bool]
    longitude: Union[str, bool]
    zone: Union[str, bool]
    image: Union[str, bool]
    departments: List[DepartmentInfo]
    amenities: List[AmenityInfo]
    area_range: RangeInfo
    price_range: RangeInfo
    bedrooms_range: RangeInfo
    bathrooms_range: RangeInfo
    # description: Union[str, bool]
    company: str
    attachment_line_ids: List[int]
    property_plan_ids: List[int]
    launch_date: Union[date, bool]
    partner_id: Union[str, bool]
    company_id: str
    
    
# -------------------------------------------------------------------------
# INTERFACES RECEIVE
# -------------------------------------------------------------------------

class LeadCreateRequest(BaseModel):
    name: str
    description: str = False
    email: str = False
    phone: str = False
    user_id: int = False
    team_id: int = False
    medium: str = False
    property_id: int = False
