import hashlib
from google.cloud.firestore import FieldFilter, AsyncClient, Query
import logging
import traceback
from typing import Literal
from fastapi import HTTPException

from auth import get_credentials_filepath
from shared_types.app_types import BLDocument
from shared_types.bl_schema import DbBL, DbRetrievedBL


logger = logging.getLogger(__name__)

cred_file = str(get_credentials_filepath("firestore-service-account.json"))
db = AsyncClient.from_service_account_json(cred_file)

if not db or not cred_file:
    raise HTTPException(status_code=500, detail="Database not initialized")


def get_dedupe_key_from_bl_number(bl_number: str, email_id: str):
    raw_string = f"{bl_number}_{email_id}"
    return hashlib.sha256(raw_string.encode('utf-8')).hexdigest()


def get_dedupe_key_from_page_range(email_id: str, attachment_id: str, page_range: tuple[int, int]):
    raw_string = f"{email_id}_{attachment_id}_{page_range}"
    return hashlib.sha256(raw_string.encode('utf-8')).hexdigest()


async def is_bl_exist(attachment: BLDocument) -> bool:
    async def db_query(collection_name: str):
        dedupe_key = get_dedupe_key_from_bl_number(
            attachment.bl_number, 
            attachment.email_id
        )
        return await db.collection(collection_name).where(filter=FieldFilter("dedupe_key", "==", dedupe_key)).limit(1).get()
    
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
            update_time, doc_ref = await db.collection(bill.doc_type).add(doc_data)
            logger.debug(f"BL is saved {bill.doc_type.upper()} | Doc ID: {doc_ref.id}")
            
    except Exception as e:
        logger.error("Firestore failed in saving documents")
        logger.error(traceback.format_exc()) 
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")


async def get_paginated_documents(doc_type: Literal["hbl", "mbl"], limit: int, cursor: str | None):
    coll = db.collection(doc_type)
    query = coll.order_by("created_at", direction=Query.DESCENDING)
    
    
    if cursor:
        cursor_doc = await coll.document(cursor).get()
        if not cursor_doc.exists:
            raise HTTPException(status_code=400, detail="Invalid cursor")
        
        query = query.start_after(cursor_doc)
    
    docs = query.limit(limit).stream()
    
    results: list[DbRetrievedBL] = []
    next_cursor = None
    async for doc in docs:
        doc_data = doc.to_dict()
        if not doc_data: continue
        doc_data['doc_id'] = doc.id
        results.append(DbRetrievedBL(**doc_data))
        next_cursor = doc.id
    
    if len(results) < limit: next_cursor = None
    return (results, next_cursor)