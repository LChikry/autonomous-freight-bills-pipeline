import hashlib
from google.cloud.firestore import FieldFilter, AsyncClient, Query
import logging
import traceback
from typing import Literal
from fastapi import HTTPException

from core import settings
from shared_types.app_types import BLDocument
from shared_types.bl_schema import DbBL, DbRetrievedBL


logger = logging.getLogger(__name__)
db_client = AsyncClient.from_service_account_json(settings.firestore_client_path)

if not db_client:
    raise HTTPException(status_code=500, detail="Database not initialized")


def get_dedupe_key_from_bl_number(bl_number: str, file_name: str):
    raw_string = f"{bl_number}_{file_name}"
    return hashlib.sha256(raw_string.encode('utf-8')).hexdigest()


def get_dedupe_key_from_page_range(email_id: str, filename: str, page_range: tuple[int, int]):
    raw_string = f"{email_id}_{filename}_{page_range}"
    return hashlib.sha256(raw_string.encode('utf-8')).hexdigest()


async def is_bl_exist(attachment: BLDocument) -> bool:
    async def db_query(collection_name: str):
        dedupe_key = get_dedupe_key_from_bl_number(
            attachment.bl_number, 
            attachment.filename
        )
        return await db_client.collection(collection_name).where(filter=FieldFilter("dedupe_key", "==", dedupe_key)).limit(1).get()
    
    if attachment.doc_type == "hbl" and len(await db_query("hbl")) > 0: 
        return True
        
    return attachment.doc_type == "mbl" and len(await db_query("mbl")) > 0


async def save_bls(bls: list[DbBL]):
    if not bls:
        logger.info("No BL to save in database")
        return
    
    logger.info(f"Saving {len(bls)} Bill(s) of Lading...")
    
    try:
        for bill in bls:
            logger.debug(f"Attempting to save BL: {bill.bl_number}") 
            doc_data = bill.model_dump(mode='json', exclude_none=True, exclude={'attachment': {'content': True}}) 
            update_time, doc_ref = await db_client.collection(bill.doc_type).add(doc_data)
            logger.debug(f"BL is saved {bill.doc_type.upper()} | Doc ID: {doc_ref.id}")
            
    except Exception as e:
        logger.error("Firestore failed in saving documents")
        logger.error(traceback.format_exc()) 
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")


async def get_next_page_documents(
    doc_type: Literal["hbl", "mbl"],
    limit: int,
    next_cursor: str | None
):
    ref = db_client.collection(doc_type)
    query = ref.order_by("created_at", direction=Query.DESCENDING)
    
    if next_cursor:
        cursor_doc = await ref.document(next_cursor).get()
        if not cursor_doc.exists:
            raise HTTPException(status_code=400, detail="Invalid next_cursor")
        
        query = query.start_after(cursor_doc)
    
    docs = query.limit(limit + 1).stream()
    
    results: list[DbRetrievedBL] = []
    async for doc in docs:
        doc_data = doc.to_dict()
        if not doc_data: continue
        doc_data['doc_id'] = doc.id
        results.append(DbRetrievedBL(**doc_data))
    
    new_next_cursor = results.pop().doc_id if len(results) > limit else None
    new_prev_cursor = results[0].doc_id if results else None
    return (results, new_prev_cursor, new_next_cursor)


async def get_prev_page_documents(
    doc_type: Literal["hbl", "mbl"],
    limit: int,
    prev_cursor: str,
):
    ref = db_client.collection(doc_type)
    
    anchor_doc = await ref.document(prev_cursor).get()
    if not anchor_doc.exists:
        raise HTTPException(status_code=400, detail="Invalid prev_cursor")
    
    docs = await (
        ref.order_by("created_at", direction=Query.DESCENDING)
        .end_before(anchor_doc)
        .limit_to_last(limit+1)
        .get()
    )
    has_prev = len(docs) > limit # since we modify the len of results
    
    new_prev_cursor = None
    results: list[DbRetrievedBL] = []
    for i, doc in enumerate(docs):
        doc_data = doc.to_dict()
        
        if not doc_data or i == 0: continue
        if i == 1: new_prev_cursor = doc.id
        
        doc_data["doc_id"] = doc.id
        results.append(DbRetrievedBL(**doc_data))
    
    new_prev_cursor = new_prev_cursor if has_prev > limit else None
    new_next_cursor = results[-1].doc_id if results else None
    return (results, new_prev_cursor, new_next_cursor)