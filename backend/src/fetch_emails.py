import base64
import logging
import datetime

from auth import get_gmail_service
from backend.src.types.my_types import Email, FetchedAttachment

logger = logging.getLogger(__name__)

def fetch_latest_emails(limit: int = 10, user_id: str = 'me', label_id: str = "INBOX") -> list[Email]:
    logger.info(f"Fetching latest {limit} emails in {label_id}")
    
    service = get_gmail_service()
    results: dict = (
            service.users().messages().list(userId=user_id, labelIds=[label_id], maxResults=limit).execute()
        )
    messages_ids: list[dict] = results.get("messages", [])
    if not messages_ids:
        logger.debug("No emails to fetch")
        return []
    
    logger.debug(f"{len(messages_ids)} emails found; starting individual fetching")
    result = []
    for msg_id in messages_ids:
        logger.debug(f"Fetching email_id={msg_id}")
        email: dict = (
            service.users().messages().get(userId="me", id=msg_id["id"], format="full").execute()
        )
        
        logger.debug(email["payload"]["parts"][0].keys())
        logger.debug(email["payload"]["body"])

        if "multipart" not in email["payload"]["mimeType"].lower():
            logger.debug(f"Skipping email_id={msg_id["id"]} because it has no attachments")
            continue
        
        raw_text_excerpt, latest_body_text, attachments = parse_payload(service, email["payload"], user_id, msg_id["id"])
        
        if not attachments:
            logger.debug(f"Skipping email_id={msg_id["id"]} because it has no attachments")
            continue

        if not latest_body_text or not raw_text_excerpt:
            logger.warning(f"Skipping email_id={msg_id} because it has no body text")
            continue

        subject, source_from = parse_headers(email['payload']['headers'])
        
        print('\n\n', datetime.datetime.fromtimestamp(float(email["internalDate"]) /1000.0, tz=datetime.timezone.utc).isoformat())
        
        email_data = Email(
            id=email["id"],
            subject=subject,
            source_from=source_from,
            received_at=datetime.datetime.fromtimestamp(float(email["internalDate"]) /1000.0, tz=datetime.timezone.utc).isoformat(),
            latest_body_text=latest_body_text,
            raw_text_excerpt=raw_text_excerpt,
            attachments=attachments,
        )
        result.append(email_data)
    
    return result


def parse_headers(headers: dict):
    subject, source_from = "", ""
    for h in headers:
        name = h['name']
        
        if name == 'Subject':
            subject = h['value']
        elif name == 'From':
            source_from = h['value']
        
        if subject and source_from: break
    
    if 'Fwd: ' in subject: subject = subject[5:]
    return (subject, source_from)


def parse_payload(service, payload, user_id, msg_id) -> tuple[str | None, str | None, list[FetchedAttachment] | None]:
    logger.debug(f"Parsing email_id={msg_id} body for latest body text")
    body_text = get_email_body(payload)
    latest_body_text = extract_latest_body_text(body_text)
    attachments = extract_attachments(payload, service, user_id, msg_id)
    return (body_text, latest_body_text, attachments)


def extract_latest_body_text(body_text) -> str | None:
    if not body_text: return None
    
    separator = "---------- Forwarded message ---------"
    if separator not in body_text:
        return body_text
    return body_text.split(separator)[0].strip()


def get_email_body(payload) -> str | None:
    if not payload: return None
    
    if payload["mimeType"].lower() == "text/plain" and "body" in payload:
        return decode_data(payload["body"].get("data", ""))
    
    if "parts" not in payload: return None
    for part in payload["parts"]:
        text = get_email_body(part)
        if text: return text


def extract_attachments(payload, service, user_id, msg_id) -> list[FetchedAttachment]:
    pdfs = []
    
    parts = [payload]
    while parts:
        part = parts.pop()
        
        if part.get('parts'):
            parts.extend(part['parts'])
        
        if not part.get('filename') or not part.get('body', {}).get('attachmentId'):
            continue
        
        if part["mimeType"].lower() != "application/pdf":
            logger.debug(f"A non PDF attachment is skipped in email_id={msg_id}")
            continue

        att_id = part['body']['attachmentId']
        filename = part['filename']
        logger.debug(f"An attachment in email_id={msg_id} is found with id={att_id} and name={filename}")
        
        # FETCH ATTACHMENT: Download the actual data
        att_id = part["body"]["attachmentId"]
        attachment = service.users().messages().attachments().get(
            userId=user_id,
            messageId=msg_id,
            id=att_id
        ).execute()
        
        file_data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))
        
        pdfs.append(FetchedAttachment(
            attachment_id=att_id,
            email_id=msg_id,
            filename=filename,
            content=file_data
        ))

    return pdfs

def decode_data(data):
    """Helper to handle Base64 decoding"""
    if not data:
        return ""
    # Python requires padding for base64 decoding if length isn't divisible by 4
    padding = len(data) % 4
    if padding:
        data += '=' * (4 - padding)
    return base64.urlsafe_b64decode(data).decode('utf-8')

if __name__ == "__main__":
    fetch_latest_emails()