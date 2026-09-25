"""Loads microsoft/trocr-base-printed once (module-level cache) and runs
local inference on uploaded images. No external API calls, no network
dependency beyond the one-time model download."""

import io

from PIL import Image

_processor = None
_model = None


def _load_model():
    global _processor, _model
    if _model is None:
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel

        _processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-printed")
        _model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-printed")
    return _processor, _model


def run_ocr(image_bytes: bytes) -> tuple[str, float]:
    """Returns (raw_text, confidence 0-1). Raises on failure - the caller
    (routers/ocr.py) is responsible for catching this and marking the order
    UNPLACED rather than crashing or silently guessing."""
    import torch

    processor, model = _load_model()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    pixel_values = processor(images=image, return_tensors="pt").pixel_values

    with torch.no_grad():
        outputs = model.generate(pixel_values, output_scores=True, return_dict_in_generate=True)

    text = processor.batch_decode(outputs.sequences, skip_special_tokens=True)[0].strip()

    # TrOCR doesn't expose a single clean confidence score, so approximate one
    # from the average max-softmax probability across generated tokens.
    try:
        probs = [torch.softmax(s, dim=-1).max().item() for s in outputs.scores]
        confidence = sum(probs) / len(probs) if probs else 0.0
    except Exception:
        confidence = 0.5 if len(text) > 4 else 0.1

    return text, confidence
