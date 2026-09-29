"""
Local OCR service using Microsoft's TrOCR handwritten-text model.

The model is loaded once and then reused for subsequent OCR requests.
No external OCR API is used.
"""

import io

import torch
from PIL import Image, ImageEnhance, ImageChops
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

_processor = None
_model = None

def auto_crop_whitespace(image: Image.Image) -> Image.Image:
    """Automatically removes excess solid-color background before OCR."""
    # Get the background color from the top-left pixel
    bg_color = image.getpixel((0, 0))
    bg = Image.new(image.mode, image.size, bg_color)
    
    # Find the difference between the background and the actual text
    diff = ImageChops.difference(image, bg)
    bbox = diff.getbbox()
    
    if bbox:
        # Add a 15-pixel buffer around the text so the model has slight breathing room
        l, t, r, b = bbox
        return image.crop((
            max(0, l - 15),
            max(0, t - 15),
            min(image.width, r + 15),
            min(image.height, b + 15)
        ))
    
    return image

def _load_model():
    """
    Load TrOCR only once.
    """
    global _processor, _model

    if _model is None:
        _processor = TrOCRProcessor.from_pretrained(
            "microsoft/trocr-base-handwritten"
        )
        _model = VisionEncoderDecoderModel.from_pretrained(
            "microsoft/trocr-base-handwritten"
        )
        _model.eval()

    return _processor, _model


def run_ocr(image_bytes: bytes) -> tuple[str, float]:
    """
    Run OCR on image bytes.
    """
    processor, model = _load_model()

    # Open uploaded image
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    
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
    # 2. Gentle enhancement for photos
    # ---------------------------------
    # Do not auto-crop based on top-left pixel.
    # Tone down contrast enhancement so pen strokes aren't blown out.
    image = ImageEnhance.Contrast(image).enhance(1.2)

    # ---------------------------------
    # 3. Prepare image for TrOCR
    # ---------------------------------
    pixel_values = processor(
        images=image,
        return_tensors="pt",
    ).pixel_values

    # ---------------------------------
    # 4. Run model inference
    # ---------------------------------
    with torch.no_grad():
        outputs = model.generate(
            pixel_values,
            output_scores=True,
            return_dict_in_generate=True,
            max_new_tokens=100,
        )

    # ---------------------------------
    # 5. Convert tokens to text
    # ---------------------------------
    text = processor.batch_decode(
        outputs.sequences,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=True, 
    )[0].strip()
    
    # ---------------------------------
    # 6. Estimate confidence
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
        confidence = 0.5 if len(text) > 4 else 0.1

    return text, float(confidence)