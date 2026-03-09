from google.cloud.firestore import AsyncClient, Query, FieldFilter, And
from loguru import logger
import traceback
from fastapi import HTTPException

from app.core import settings
from app.models.emails import AttachmentTransformed
from app.models.bill_of_lading import DocType
from app.schemas.db import BLRecordCreate, BLRecord

db_client = AsyncClient.from_service_account_json(settings.firestore_client_path)

if not db_client:
    raise HTTPException(status_code=500, detail="Database not initialized")


async def is_bl_attachment_exist(original_content_sha256: str, page_range: tuple[int ,int], doc_type: DocType | None) -> bool:
    
    async def db_query(collection_name: str):
        f1 = FieldFilter("attachment.original_content_sha256", "==", original_content_sha256)
        f2 = FieldFilter("attachment.page_range", "==", list(page_range))
        return (
            await db_client.collection(collection_name)
            .where(filter=And([f1, f2]))
            .limit(1)
            .get()
        )
    
    if not doc_type:
        hbl_found = len(await db_query(DocType.HBL)) != 0
        mbl_found = len(await db_query(DocType.MBL)) != 0
        return True if mbl_found or hbl_found else False
    
    return len(await db_query(doc_type)) != 0


async def is_bl_record_exist(bl_number: str, issuer_name: str, doc_type: DocType | None) -> bool:
    async def db_query(collection_name: str):
        f1 = FieldFilter("bl_number", "==", bl_number)
        f2 = FieldFilter("issuer_name", "==", issuer_name)
        return (
            await db_client.collection(collection_name)
            .where(filter=And([f1, f2]))
            .limit(1)
            .get()
        )
    
    if not doc_type:
        hbl_found = len(await db_query(DocType.HBL)) != 0
        mbl_found = len(await db_query(DocType.MBL)) != 0
        return True if mbl_found or hbl_found else False
    
    return len(await db_query(doc_type)) != 0



async def save_bl_documents(bls: list[BLRecordCreate]):
    if not bls:
        logger.info("No BL to save in database")
        return
    
    logger.info(f"Saving {len(bls)} Bill(s) of Lading...")
    
    try:
        for bill in bls:
            logger.debug(f"Attempting to save BL: {bill.bl_number}")
            
            doc_data = bill.model_dump(
                mode='json',
                exclude_none=True,
                context= {"reveal_secret_types": True},
            )
            _, doc_ref = await db_client.collection(bill.doc_type).add(doc_data)
            
            logger.debug(f"BL is saved {bill.doc_type.upper()} | Doc ID: {doc_ref.id}")
            
    except Exception as e:
        logger.error("Firestore failed in saving documents")
        logger.error(traceback.format_exc()) 
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")


async def get_next_page_documents(
    doc_type: DocType,
    limit: int,
    next_cursor: str | None
):
    ref = db_client.collection(doc_type)
    query = ref.order_by("created_at", direction=Query.DESCENDING)
    
    if next_cursor:
        cursor_doc = await ref.document(next_cursor).get()
        if not cursor_doc.exists:
            raise HTTPException(status_code=422, detail="Invalid next_cursor")
        
        query = query.start_after(cursor_doc)
    
    docs = query.limit(limit + 1).stream()
    
    results: list[BLRecord] = []
    async for doc in docs:
        doc_data = doc.to_dict()
        if not doc_data: continue
        doc_data['doc_id'] = doc.id
        results.append(BLRecord(**doc_data))
    
    new_next_cursor = results.pop().doc_id if len(results) > limit else None
    new_prev_cursor = results[0].doc_id if results else None
    return (results, new_prev_cursor, new_next_cursor)


async def get_prev_page_documents(
    doc_type: DocType,
    limit: int,
    prev_cursor: str,
):
    ref = db_client.collection(doc_type)
    
    anchor_doc = await ref.document(prev_cursor).get()
    if not anchor_doc.exists:
        raise HTTPException(status_code=422, detail="Invalid prev_cursor")
    
    docs = await (
        ref.order_by("created_at", direction=Query.DESCENDING)
        .end_before(anchor_doc)
        .limit_to_last(limit+1)
        .get()
    )
    has_prev = len(docs) > limit # since we modify the len of results
    
    new_prev_cursor = None
    results: list[BLRecord] = []
    for i, doc in enumerate(docs):
        doc_data = doc.to_dict()
        
        if not doc_data or i == 0: continue
        if i == 1: new_prev_cursor = doc.id
        
        doc_data["doc_id"] = doc.id
        results.append(BLRecord(**doc_data))
    
    new_prev_cursor = new_prev_cursor if has_prev > limit else None
    new_next_cursor = results[-1].doc_id if results else None
    return (results, new_prev_cursor, new_next_cursor)