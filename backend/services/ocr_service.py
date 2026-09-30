"""
Local OCR service using Microsoft's TrOCR printed model.
Complies with requirement: Pretrained model microsoft/trocr-base-printed.
"""
import io
import warnings
import torch
from PIL import Image, ImageEnhance, ImageOps
import transformers
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

# Suppress Hugging Face noise
transformers.logging.set_verbosity_error()
warnings.filterwarnings("ignore", category=FutureWarning, module="transformers")

_processor = None
_model = None

def _load_model():
    global _processor, _model
    if _model is None:
        model_name = "microsoft/trocr-base-printed"
        _processor = TrOCRProcessor.from_pretrained(model_name)
        _model = VisionEncoderDecoderModel.from_pretrained(model_name)
        _model.eval()
    return _processor, _model

def _preprocess_image(image: Image.Image) -> Image.Image:
    """Prepares label image for TrOCR without destroying font strokes."""
    # Convert to RGB
    image = image.convert("RGB")
    
    # Auto-orient based on EXIF if present
    image = ImageOps.exif_transpose(image)

    # Resize maintaining aspect ratio (TrOCR expects around 384x384 internally)
    max_dim = 1024
    if max(image.width, image.height) > max_dim:
        scale = max_dim / max(image.width, image.height)
        image = image.resize(
            (int(image.width * scale), int(image.height * scale)),
            Image.Resampling.BILINEAR
        )

    # Moderate contrast enhancement (avoid double-contrast blowout)
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.2)
    return image

def run_ocr(image_bytes: bytes) -> tuple[str, float]:
    """
    Runs TrOCR inference. Returns (extracted_text, confidence_score).
    """
    processor, model = _load_model()
    raw_image = Image.open(io.BytesIO(image_bytes))
    image = _preprocess_image(raw_image)

    pixel_values = processor(images=image, return_tensors="pt").pixel_values

    with torch.no_grad():
        outputs = model.generate(
            pixel_values,
            output_scores=True,
            return_dict_in_generate=True,
            max_new_tokens=128,
            num_beams=4,
            early_stopping=True,
        )

    # Use tokenizer directly to avoid the FutureWarning
    text = processor.tokenizer.batch_decode(
        outputs.sequences,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False
    )[0].strip()

    # Calculate token probability confidence
    try:
        if outputs.scores:
            probs = [torch.softmax(score, dim=-1).max().item() for score in outputs.scores]
            confidence = float(sum(probs) / len(probs))
        else:
            confidence = 0.85 if len(text) > 8 else 0.1
    except Exception:
        confidence = 0.5 if len(text) > 4 else 0.0

    # Filter out empty or raw noise artifacts (e.g. '***')
    if not text or text == "***" or set(text).issubset({".", "*", "-", " "}):
        return "", 0.0

    return text, round(confidence, 3)