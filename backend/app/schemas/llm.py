from pydantic import BaseModel, Field
from typing import List

from app.models.bill_of_lading import BillOfLading
from app.models.emails import EmailStatus

class LLMRequest(BaseModel):
    request_id: str
    content: bytes
    email_body: str

class LLMResponse(BillOfLading):
    request_id: str = Field(..., description="the request id using ULID, it is provided with the prompt")
    
    email_status: EmailStatus = Field(..., description="An email is status is classified either as pre_alert or draft. To know which one it is, we use the newest body (recent_body) since it will contain wording indicating pre-alert or draft.")