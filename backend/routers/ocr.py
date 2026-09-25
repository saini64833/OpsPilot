from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import Order, OrderStatus, OrderSource
from services.audit import log_action
from services.llm_address_cleanup import clean_address
from services.ocr_service import run_ocr
from services.routing import assign_order

router = APIRouter(prefix="/orders", tags=["ocr"])


@router.post("/{order_id}/ocr")
async def process_photo_order(order_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Image -> OCR -> LLM structuring -> confidence gate -> assignment.
    Every failure branch marks the order UNPLACED (never a crash, never a
    silent guess) and preserves whatever was already extracted."""
    order = db.query(Order).get(order_id)
    if not order:
        raise HTTPException(404, "Order not found")

    image_bytes = await file.read()
    order.source = OrderSource.PHOTO

    try:
        raw_text, ocr_conf = run_ocr(image_bytes)
    except Exception as e:
        log_action(db, "order", order.id, "system", "ocr_failed", notes=str(e))
        order.status = OrderStatus.UNPLACED
        db.commit()
        raise HTTPException(502, "OCR failed - image preserved, retry or enter manually")

    order.raw_ocr_text = raw_text
    order.ocr_confidence = ocr_conf
    log_action(
        db, "order", order.id, "system", "ocr_extracted",
        raw_payload={"text": raw_text, "confidence": ocr_conf},
    )
    db.commit()

    try:
        cleaned = clean_address(raw_text)
    except Exception as e:
        log_action(db, "order", order.id, "system", "llm_parse_error", notes=str(e))
        order.status = OrderStatus.UNPLACED
        db.commit()
        raise HTTPException(502, "Address cleanup failed - retry or enter manually")

    if cleaned.confidence == "low" or ocr_conf < settings.OCR_CONFIDENCE_THRESHOLD:
        log_action(
            db, "order", order.id, "system", "llm_low_confidence",
            raw_payload=cleaned.model_dump(),
        )
        order.status = OrderStatus.UNPLACED
        db.commit()
        return {"status": "unplaced", "raw_text": raw_text, "cleaned": cleaned.model_dump()}

    order.delivery_address = ", ".join(
        part for part in [cleaned.street, cleaned.city, cleaned.state, cleaned.zip] if part
    )
    log_action(db, "order", order.id, "system", "address_cleaned", raw_payload=cleaned.model_dump())
    assign_order(db, order)
    db.commit()
    db.refresh(order)
    return {"status": "placed", "order_id": order.id, "delivery_address": order.delivery_address}
