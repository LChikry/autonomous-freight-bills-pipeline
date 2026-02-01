import io
import re
import pdfplumber
import pikepdf
from datetime import datetime
from typing import Literal, cast

from types.app_types import AttachmentPages, BLDocument, FetchedAttachment

def split_grouped_bills(attachment: FetchedAttachment) -> list[BLDocument]:
    total_pages, invoice_ranges = get_invoice_ranges_in_attachments(attachment.content)
    bills = split_mega_attachments(attachment.content, total_pages, invoice_ranges)

    bls = []
    for b in bills:
        bls.append(BLDocument(
            attachment_id=attachment.attachment_id,
            email_id=attachment.email_id,
            filename=attachment.filename,
            content=b.content,
            page_range=b.page_range,
            bl_number=b.bl_number,
            doc_type=cast(Literal["hbl", "mbl"], b.bl_number.split("-")[0].lower().strip()),
            created_at=b.created_at
        ))
    
    return bls


def get_invoice_ranges_in_attachments(file_content_bytes):
    # Regex setup
    page_pattern = re.compile(r"Page\s+(\d+)\s*(?:of|/)\s*(\d+)", re.IGNORECASE)
    ref_pattern = re.compile(r"Reference:\s*((?:MBL|HBL)-\d+)", re.IGNORECASE)
    date_pattern = re.compile(r"Generated:\s*(\d{1,2}-[A-Za-z]{3}-\d{4}\s+\d{2}:\d{2})", re.IGNORECASE)
    invoice_ranges = [] # Format: (Ref_ID, Date, Start_Index, End_Index)
    
    with pdfplumber.open(io.BytesIO(file_content_bytes)) as pdf:
        total_pages = len(pdf.pages)
        current_start_page = 0
        
        active_ref_id = "UNKNOWN_REF" 
        active_date = "UNKNOWN_DATE"
        for i, page in enumerate(pdf.pages):
            width, height = page.width, page.height
            footer_crop = page.crop((0, height * 0.90, width, height))
            text = footer_crop.extract_text() or ""
            
            # Search for metadata
            page_match = page_pattern.search(text)
            ref_match = ref_pattern.search(text)
            date_match = date_pattern.search(text)
            
            # Logic: Did we hit the start of a NEW invoice?
            if page_match and int(page_match.group(1)) == 1:
                # Identify the ID for this NEW invoice
                new_found_id = "UNKNOWN_REF"
                if ref_match: new_found_id = str(ref_match.group(1)).upper()
                
                new_found_date = "UNKNOWN_DATE"
                if date_match: new_found_date = str(date_match.group(1))
                
                if i > 0:
                    invoice_ranges.append((active_ref_id, active_date, current_start_page, i))
                    current_start_page = i
                
                active_ref_id = new_found_id
                active_date = new_found_date
                
            # Fallback: If we didn't find the Ref ID on Page 1
            else:
                if ref_match and active_ref_id == "UNKNOWN_REF":
                    active_ref_id = str(ref_match.group(1)).upper()
                if date_match and active_date == "UNKNOWN_DATE":
                    active_date = str(date_match.group(1))

        # 4. Save the final block (The last invoice in the file)
        if current_start_page < total_pages:
            invoice_ranges.append((active_ref_id, active_date, current_start_page, total_pages))
    
    return total_pages, invoice_ranges


def split_mega_attachments(file_content_bytes: bytes, total_pages: int, invoice_ranges: list[tuple[str, str, int, int]]) -> list[AttachmentPages]:
    # Skip splitting if df contains only one invoice
    if len(invoice_ranges) == 1:
        ref, date, start, end = invoice_ranges[0]
        if start == 0 and end == total_pages:
            return [AttachmentPages(
                    bl_number=ref,
                    content=file_content_bytes,
                    page_range=(start, end),
                    created_at=datetime.strptime(date, "%d-%b-%Y %H:%M").isoformat()
                )]

    split_pdfs = []
    with pikepdf.open(io.BytesIO(file_content_bytes)) as pdf:
        for ref, date, start, end in invoice_ranges:
            new_pdf = pikepdf.new()
            
            for page_num in range(start, end):
                new_pdf.pages.append(pdf.pages[page_num])
            
            output_buffer = io.BytesIO()
            new_pdf.save(output_buffer)
            split_pdfs.append(AttachmentPages(bl_number=ref,
                content=output_buffer.getvalue(),
                page_range=(start, end),
                created_at=datetime.strptime(date, "%d-%b-%Y %H:%M").isoformat() if date != "UNKNOWN_DATE" else None
            ))
            
    return split_pdfs