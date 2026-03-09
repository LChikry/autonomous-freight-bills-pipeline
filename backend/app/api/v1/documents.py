from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.schemas.db import BLRecord
from app.models.bill_of_lading import DocType
import app.services.repository as repository

router = APIRouter(prefix="/api/v1")

class GetBlListRequestBase(BaseModel):
    limit: int = Field(10, ge=1, le=100)
    next_cursor: str | None = None
    prev_cursor: str | None = None
    
    @model_validator(mode="after")
    def check_mutual_exclusivity_of_cursors(self):
        if self.next_cursor and self.prev_cursor:
            raise HTTPException(status_code=422, detail="Provide either next_cursor or prev_cursor but not both.")
        return self

class GetHblListRequest(GetBlListRequestBase):
    pass

class GetMblListRequest(GetBlListRequestBase):
    pass


class GetBlListResponseBase(BaseModel):
    documents: list[BLRecord]
    next_cursor: str | None = None
    prev_cursor: str | None = None

class GetHblListResponse(GetBlListResponseBase):
    pass

class GetMblListResponse(GetBlListResponseBase):
    pass


@router.get("/hbl", response_model=GetHblListResponse)
async def fetch_hbl(params: GetHblListRequest = Depends()):
    if params.prev_cursor:
        docs, prev_cursor, next_cursor = await repository.get_prev_page_documents(
            DocType.HBL,
            params.limit,
            params.prev_cursor,
        )
    else:
        docs, prev_cursor, next_cursor = await repository.get_next_page_documents(
            DocType.HBL,
            params.limit,
            params.next_cursor,
        )       
    
    return GetHblListResponse(
        documents=docs,
        prev_cursor=prev_cursor,
        next_cursor=next_cursor,
    )


@router.get("/mbl", response_model=GetMblListResponse)
async def fetch_mbl(params: GetMblListRequest = Depends()):
    if params.prev_cursor:
        docs, prev_cursor, next_cursor = await repository.get_prev_page_documents(
            DocType.MBL,
            params.limit,
            params.prev_cursor,
        )
    else:
        docs, prev_cursor, next_cursor = await repository.get_next_page_documents(
            DocType.MBL,
            params.limit,
            params.next_cursor,
        )
    
    return GetHblListResponse(
        documents=docs,
        prev_cursor=prev_cursor,
        next_cursor=next_cursor,
    )