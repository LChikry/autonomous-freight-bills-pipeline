import base64
import logging

from auth import get_gmail_service

logger = logging.getLogger(__name__)

def fetch_latest_emails(limit: int = 10, user_id: str = 'me', label_id: str = "INBOX") -> list[dict]:
    logger.info(f"Fetching latest {limit} emails in {label_id}")
    
    service = get_gmail_service()
    results: dict = (
            service.users().messages().list(userId=user_id, labelIds=[label_id], maxResults=limit).execute()
        )
    messages_ids: list[dict] = results.get("messages", [])
    if not messages_ids:
        logger.debug("No emails to fetch")
        return messages_ids
    
    logger.debug(f"{len(messages_ids)} emails found; starting individual fetching")
    result = []
    for msg_id in messages_ids:
        logger.debug(f"Fetching email_id={msg_id}")
        email: dict = (
            service.users().messages().get(userId="me", id=msg_id["id"], format="full").execute()
        )
        
        logger.debug(email["payload"]["parts"][0].keys())
        logger.debug(email["payload"]["body"])

        if "multipart" not in email["payload"]["mimeType"]:
            logger.debug(f"Skipping email_id={msg_id["id"]} because it has no attachments")
            continue
        
        latest_body_text, attachments = parse_payload(service, email["payload"], user_id, msg_id["id"])
        
        if not attachments:
            logger.debug(f"Skipping email_id={msg_id["id"]} because it has no attachments")
            continue

        if not latest_body_text:
            logger.warning(f"Skipping email_id={msg_id} because it has no body text")
            continue

        email_data = {
            "id": email["id"],
            "internalDate_ms": email["internalDate"],
            "latest_body_text": latest_body_text,
            "attachments": attachments
        }
        result.append(email_data)
    
    return result


def parse_payload(service, payload, user_id, msg_id) -> tuple[str | None, list | None]:
    logger.debug(f"Parsing email_id={msg_id} body for latest body text")
    latest_body_text = extract_latest_body_text(payload)
    attachments = extract_attachments(payload, service, user_id, msg_id)
    return (latest_body_text, attachments)


def extract_latest_body_text(payload):
    body_text = get_email_body(payload)
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


def extract_attachments(payload, service, user_id, msg_id) -> list[dict]:
    pdfs = []
    
    parts = [payload]
    while parts:
        part = parts.pop()
        
        if part.get('parts'):
            parts.extend(part['parts'])
        
        if not part.get('filename') or not part.get('body', {}).get('attachmentId'):
            continue
        
        if not part["mimeType"] != "application/pdf":
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
        
        pdfs.append({
            "id": att_id,
            "filename": filename,
            "email_id": msg_id,
            "content": file_data,
        })

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