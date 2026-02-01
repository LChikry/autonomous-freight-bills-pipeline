import hashlib
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter, Or
import logging
import traceback

from fastapi import HTTPException

from auth import get_credentials_filepath
from backend.src.types.my_types import BLDocument
from types.bl_schema import DbBL

logger = logging.getLogger(__name__)

cred_file = str(get_credentials_filepath("firestore-service-account.json"))
db = firestore.Client.from_service_account_json(cred_file)

if not db or not cred_file:
    raise HTTPException(status_code=500, detail="Database not initialized")


def get_dedupe_key_from_bl_number(bl_number: str, email_id: str):
    raw_string = f"{bl_number}_{email_id}"
    return hashlib.sha256(raw_string.encode('utf-8')).hexdigest()


def get_dedupe_key_from_page_range(email_id: str, attachment_id: str, page_range: tuple[int, int]):
    raw_string = f"{email_id}_{attachment_id}_{page_range}"
    return hashlib.sha256(raw_string.encode('utf-8')).hexdigest()


def is_bl_exist(attachment: BLDocument) -> bool:
    def db_query(collection_name: str):
        dedupe_key = get_dedupe_key_from_bl_number(
            attachment.bl_number, 
            attachment.email_id
        )
        return db.collection(collection_name).where("dedupe_key", "==", dedupe_key).limit(1).get()
    
    if attachment.doc_type == "hbl" and len(db_query("hbl")) > 0: 
        return True
        
    return attachment.doc_type == "mbl" and len(db_query("mbl")) > 0


def save_bls(bls: list[DbBL]):
    if not bls:
        logger.info("No BL to save in database")
        return
    
    logger.info(f"Saving {len(bls)} Bill(s) of Lading...")
    
    try:
        for bill in bls:
            logger.info(f"Attempting to save BL: {bill.bl_number}") 
            doc_data = bill.model_dump(mode='json', exclude_none=True, exclude={'attachment': {'content': True}}) 
            update_time, doc_ref = db.collection(bill.doc_type).add(doc_data)
            logger.info(f"BL is saved {bill.doc_type.upper()} | Doc ID: {doc_ref.id}")
            
    except Exception as e:
        logger.error("❌ CRITICAL FIRESTORE ERROR:")
        logger.error(traceback.format_exc()) 
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")


def get_documents(doc_type: str):
    if doc_type not in ["hbl", "mbl"]:
        raise HTTPException(status_code=400, detail="Type must be 'hbl' or 'mbl'")

    docs_ref = db.collection(doc_type).stream()
    
    results = []
    for doc in docs_ref:
        doc_data = doc.to_dict()
        if not doc_data: continue
        doc_data['id'] = doc.id
        results.append(doc_data)
        
    return results