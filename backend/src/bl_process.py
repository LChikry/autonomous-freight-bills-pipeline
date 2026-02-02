import logging

import db
from shared_types.app_types import BLDocument, BaseEmail, Email
from shared_types.bl_schema import BillOfLading, DbBL

logger = logging.getLogger(__name__)

async def check_duplicates(bls: list[BLDocument]):
    if not bls: return []

    num_all_bls = len(bls)
    # 1. Dedupe against co-fetched Documents
    seen_keys1 = set()
    seen_keys2 = set()
    unique_in_batch = []

    for b in bls:
        dedupe_key1 = db.get_dedupe_key_from_bl_number(b.bl_number, b.email_id)
        dedupe_key2 = db.get_dedupe_key_from_page_range(b.email_id, b.attachment_id, b.page_range)

        if dedupe_key1 in seen_keys1 or dedupe_key2 in seen_keys2: continue
        seen_keys1.add(dedupe_key1)
        seen_keys2.add(dedupe_key2)
        unique_in_batch.append(b)
    
    # 2. Checking against the DB
    final_unique_bls = []
    for b in unique_in_batch:
        if await db.is_bl_exist(b): continue
        final_unique_bls.append(b)
    
    num_diff_bls = num_all_bls - len(final_unique_bls)
    if len(final_unique_bls) < num_all_bls:
        logger.info(f"We have skipped {num_diff_bls} BLs because they are duplicates")
    
    return final_unique_bls


def create_bls_for_db(pbls: list[BillOfLading], bls: list[BLDocument], emails: dict[str, Email]):
    db_bls: list[DbBL] = []
    
    for i in range(len(pbls)):
        b, p = bls[i], pbls[i]
        e = emails[b.email_id]
        
        db_bls.append(DbBL(
            dedupe_key=db.get_dedupe_key_from_bl_number(p.bl_number or b.bl_number, e.id),
            doc_type=p.doc_type or b.bl_number,
            bl_number=p.bl_number or b.bl_number,
            booking_number=p.booking_number,
            generated_at=p.generated_at or b.generated_at or "",
            
            shipper_name=p.shipper_name,
            shipper_address=p.shipper_address,
            consignee_name=p.consignee_name,
            consignee_address=p.consignee_address,
            notify_party_name=p.notify_party_name,
            carrier_name=p.carrier_name,
            
            vessel_name=p.vessel_name,
            voyage_number=p.voyage_number,
            port_of_loading=p.port_of_loading,
            port_of_discharge=p.port_of_discharge,
            place_of_receipt=p.place_of_receipt,
            place_of_delivery=p.place_of_delivery,
            
            etd=p.etd,
            eta=p.eta,
            issue_date=p.issue_date,
            
            containers=p.containers,
            goods_summary=p.goods_summary,
            
            freight_terms=p.freight_terms,
            
            email_status=p.email_status,
            attachment=BLDocument(
                attachment_id=b.attachment_id,
                email_id=b.email_id,
                filename=b.filename,
                content=b.content,
                page_range=b.page_range,
                bl_number=b.bl_number or p.bl_number,
                generated_at=b.generated_at or p.generated_at,
                doc_type=b.doc_type or p.doc_type
            ),
            email=BaseEmail(
                id=e.id,
                subject=e.subject,
                received_at=e.received_at,
                raw_text_excerpt=e.raw_text_excerpt,
                latest_body_text=e.latest_body_text,
                source_from=e.source_from,
                email_status=p.email_status
            )
        ))
    
    return db_bls