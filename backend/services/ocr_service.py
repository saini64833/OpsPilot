"""
Local OCR service using Microsoft's TrOCR printed-text model.

The model is loaded once and then reused for subsequent OCR requests.
No external OCR API is used.
"""

import io

import torch
from PIL import Image, ImageEnhance
from transformers import TrOCRProcessor, VisionEncoderDecoderModel


_processor = None
_model = None


def _load_model():
    """
    Load TrOCR only once.
    """
    global _processor, _model

    if _model is None:
        _processor = TrOCRProcessor.from_pretrained(
            "microsoft/trocr-base-printed"
        )

        _model = VisionEncoderDecoderModel.from_pretrained(
            "microsoft/trocr-base-printed"
        )

        _model.eval()

    return _processor, _model


def run_ocr(image_bytes: bytes) -> tuple[str, float]:
    """
    Run OCR on image bytes.

    Returns:
        (raw_text, confidence)

    confidence is approximately between 0 and 1.
    """

    processor, model = _load_model()

    # Open uploaded image
    image = Image.open(
        io.BytesIO(image_bytes)
    ).convert("RGB")

    # ---------------------------------
    # 1. Upscale small images
    # ---------------------------------
    if image.width < 1200:
        scale = 1200 / image.width

        image = image.resize(
            (
                int(image.width * scale),
                int(image.height * scale),
            ),
            Image.Resampling.LANCZOS,
        )

    # ---------------------------------
    # 2. Convert to grayscale
    # ---------------------------------
    image = image.convert("RGB")
    # ---------------------------------
    # 3. Increase contrast
    # ---------------------------------
    image = ImageEnhance.Contrast(image).enhance(2.0)

    # ---------------------------------
    # 4. Prepare image for TrOCR
    # ---------------------------------
    pixel_values = processor(
        images=image,
        return_tensors="pt",
    ).pixel_values

    # ---------------------------------
    # 5. Run model inference
    # ---------------------------------
    with torch.no_grad():
        outputs = model.generate(
            pixel_values,
            output_scores=True,
            return_dict_in_generate=True,
        )

    # ---------------------------------
    # 6. Convert tokens to text
    # ---------------------------------
    text = processor.batch_decode(
        outputs.sequences,
        skip_special_tokens=True,
    )[0].strip()

    # ---------------------------------
    # 7. Estimate confidence
    # ---------------------------------
    try:
        probs = [
            torch.softmax(score, dim=-1).max().item()
            for score in outputs.scores
        ]

        confidence = (
            sum(probs) / len(probs)
            if probs
            else 0.0
        )

    except Exception:
        confidence = (
            0.5
            if len(text) > 4
            else 0.1
        )

    return text, float(confidence)