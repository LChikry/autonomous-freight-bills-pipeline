from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from datetime import date
from enum import StrEnum

class DocType(StrEnum):
    HBL = "hbl"
    MBL = "mbl"

class Container(BaseModel):
    number: str = Field(..., description="The container ID (e.g., XEBL5869714)")
    seal_number: Optional[str] = Field(None, description="The seal number (e.g., 9966195)")
    type: Optional[str] = Field(None, description="Container type code, e.g., 40'GP, 40'HC")
    
    # You asked for weight/volume. In your docs, these are KGS and CBM.
    weight_kg: Optional[float] = Field(None, description="Gross weight of container content in KGS")
    volume_cbm: Optional[float] = Field(None, description="Volume of container content in CBM")
    package_count: Optional[int] = Field(None, description="Number of packages inside this specific container")

class CargoDescription(BaseModel):
    """Details about the actual goods being shipped"""
    description: str = Field(..., description="Description of goods (e.g., Aluminium profiles, Cotton T-shirts)")
    hs_code: Optional[str] = Field(None, description="Harmonized System Code (e.g., 7604, 6109)")
    gross_weight_kg: Optional[float] = Field(None, description="Total weight for this line item")
    volume_cbm: Optional[float] = Field(None, description="Total volume for this line item")

class BillOfLading(BaseModel):
    # --- Identifiers ---
    doc_type: DocType = Field(..., description="Classify based on document title: 'hbl' for House Bill of Lading, 'mbl' for Master Bill of Lading")
    bl_number: str = Field(..., description="The main B/L number (e.g., MBL-3135534, HBL-5437923)")
    booking_number: Optional[str] = Field(None, description="Booking Reference number (e.g., BK37053918)")
    generated_at: str = Field(..., description="The date the billing is generated at in ISO8601 format")
    issuer_name: str = Field(..., description="The name of the company that issued the document. This is often found at the top of the document next to 'Issued by:'. E.g., 'Hapag-Lloyd' or 'Nordic Freight Solutions (NVOCC)'")
    
    # --- Entities ---
    shipper_name: str = Field(..., description="Name of the shipper")
    shipper_address: Optional[str] = Field(None, description="Full address of the shipper")
    
    consignee_name: str = Field(..., description="Name of the consignee")
    consignee_address: Optional[str] = Field(None, description="Full address of the consignee")
    
    notify_party_name: Optional[str] = Field(None, description="Name of the notify party")
    carrier_name: Optional[str] = Field(None, description="Name of the carrier (e.g., CMA CGM)")

    # --- Route & Logistics ---
    vessel_name: Optional[str] = Field(None, description="Vessel Name (e.g., MV Ever Zenith)")
    voyage_number: Optional[str] = Field(None, description="Voyage Number (e.g., EZ123E)")
    
    port_of_loading: str = Field(..., description="POL - Port of Loading")
    port_of_discharge: str = Field(..., description="POD - Port of Discharge")
    place_of_receipt: Optional[str] = Field(None, description="Place of Receipt (e.g., Ningbo, CN)")
    place_of_delivery: Optional[str] = Field(None, description="Place of Delivery")

    # --- Dates (ISO8601) ---
    etd: Optional[date] = Field(None, description="Estimated Time of Departure (ETD) in YYYY-MM-DD format")
    eta: Optional[date] = Field(None, description="Estimated Time of Arrival (ETA) in YYYY-MM-DD format")
    issue_date: Optional[date] = Field(None, description="Date of Issue in in YYYY-MM-DD format")

    # --- Cargo Details ---
    containers: List[Container] = Field(default_factory=list, description="List of all containers")
    goods_summary: List[CargoDescription] = Field(default_factory=list, description="Summary of goods description and HS codes")

    # --- Financials ---
    freight_terms: Optional[Literal["Prepaid", "Collect"]] = Field(None, description="Freight payment terms")