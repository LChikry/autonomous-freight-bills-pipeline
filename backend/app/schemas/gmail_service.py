from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator
from typing import Optional


class GmailMessageBlueprint(BaseModel):
    id: str

class GmailHeader(BaseModel):
    name: str
    value: str
    
    @property
    def is_subject(self) -> bool:
        return self.name.lower() == "subject"
    
    @property
    def is_sender(self) -> bool:
        return self.name.lower() == "from"

class GmailBody(BaseModel):
    data: str | None = None
    attachmentId: str | None = None

class GmailPart(BaseModel):
    mimeType: str
    headers: list[GmailHeader] = Field(default_factory=list)
    parts: list['GmailPart'] = Field(default_factory=list)
    filename: str | None = None
    body: Optional[GmailBody] = None
    
    @property
    def is_text(self) -> bool:
        return self.body != None and self.mimeType.lower() == "text/plain"
    
    @property
    def is_pdf(self):
        return self.mimeType.lower() == "application/pdf"
    
    @property
    def is_attachment(self):
        return (
            self.filename != None and 
            self.body != None and 
            self.body.attachmentId != None
        )

class GmailMessageResponse(BaseModel):
    id: str
    payload: GmailPart
    internalDate: datetime
    
    @property
    def has_attachments(self) -> bool:
        return "multipart" in self.payload.mimeType.lower()

    @field_validator('internalDate', mode='before')
    @classmethod
    def unix_to_datetime(cls, v: str) -> datetime:
        return datetime.fromtimestamp(float(v) / 1000.0, tz=timezone.utc)