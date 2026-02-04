from fastapi import APIRouter, Depends

import services.db as db
from shared_types.api_types import GetHblListRequest, GetMblListRequest, GetHblListResponse, GetMblListResponse


router = APIRouter(prefix="/api/v1")

@router.get("/hbl", response_model=GetHblListResponse)
async def fetch_hbl(params: GetHblListRequest = Depends()):
    limit, cursor = params.limit, params.cursor or None
    docs, cursor = await db.get_paginated_documents("hbl", limit, cursor)
    
    return GetHblListResponse(
        documents=docs,
        next_cursor=cursor
    )


@router.get("/mbl", response_model=GetMblListResponse)
async def fetch_mbl(params: GetMblListRequest = Depends()):
    limit, cursor = params.limit, params.cursor or None
    docs, cursor = await db.get_paginated_documents("mbl", limit, cursor)
    
    return GetMblListResponse(
        documents=docs,
        next_cursor=cursor
    )