"""Optional offline-after-download English handwriting OCR via TrOCR."""
import cv2
import numpy as np
from PIL import Image

_MODEL_ID = "microsoft/trocr-small-handwritten"
_processor = None
_model = None
_torch = None


def _load_model():
    global _processor, _model, _torch
    if _model is not None:
        return _processor, _model, _torch

    try:
        import torch
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    except ImportError as exc:
        raise RuntimeError(
            "Handwriting OCR needs the optional packages. Install them with "
            "python -m pip install -r requirements-handwriting.txt."
        ) from exc

    _processor = TrOCRProcessor.from_pretrained(_MODEL_ID)
    _model = VisionEncoderDecoderModel.from_pretrained(_MODEL_ID)
    _model.eval()
    if torch.cuda.is_available():
        _model.to("cuda")
    _torch = torch
    return _processor, _model, _torch


def _line_crops(image):
    """Split a page into horizontal text lines for the line-based model."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image.copy()
    h, w = gray.shape[:2]
    if max(h, w) < 1600:
        scale = min(2.0, 1600 / max(h, w))
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        h, w = gray.shape[:2]

    gray = cv2.fastNlMeansDenoising(gray, None, 5, 7, 21)
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 35, 11
    )
    binary = cv2.morphologyEx(
        binary, cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, 3))
    )

    projection = np.count_nonzero(binary, axis=1)
    active = projection >= max(5, int(w * 0.003))
    rows = np.flatnonzero(active)
    if not rows.size:
        return []

    max_gap = max(5, int(h * 0.008))
    groups = []
    start = previous = int(rows[0])
    for row in rows[1:]:
        row = int(row)
        if row - previous > max_gap:
            groups.append((start, previous))
            start = row
        previous = row
    groups.append((start, previous))

    pad = max(4, int(h * 0.006))
    crops = []
    for y0, y1 in groups:
        if y1 - y0 < max(7, int(h * 0.008)):
            continue
        top, bottom = max(0, y0 - pad), min(h, y1 + pad + 1)
        crops.append(Image.fromarray(gray[top:bottom]).convert("RGB"))
    return crops


def extract_handwriting(image):
    """Recognize English handwriting from an image containing one or more lines."""
    processor, model, torch = _load_model()
    lines = _line_crops(image)
    if not lines:
        return ""

    device = next(model.parameters()).device
    results = []
    for line in lines:
        pixel_values = processor(images=line, return_tensors="pt").pixel_values.to(device)
        with torch.inference_mode():
            generated = model.generate(pixel_values, max_new_tokens=128)
        text = processor.batch_decode(generated, skip_special_tokens=True)[0].strip()
        if text:
            results.append(text)
    return "\n".join(results)
