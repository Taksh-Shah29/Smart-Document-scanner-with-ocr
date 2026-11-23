import cv2, numpy as np, os, tempfile
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def order_points(p):
    p=np.asarray(p,dtype=np.float32); r=np.zeros((4,2),dtype=np.float32)
    s=p.sum(axis=1); d=np.diff(p,axis=1).reshape(-1)
    r[0]=p[np.argmin(s)]; r[2]=p[np.argmax(s)]
    r[1]=p[np.argmin(d)]; r[3]=p[np.argmax(d)]
    return r

def detect_document(image):
    h, w = image.shape[:2]
    scale = min(1.0, 1400 / max(h, w))
    small = cv2.resize(image, (int(w * scale), int(h * scale))) if scale < 1 else image.copy()
    gray_raw = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray_raw, 7, 45, 45)

    # A single Canny pass misses page edges when the paper and background have
    # similar colors or uneven lighting. Try multiple edge/threshold masks.
    edges = cv2.Canny(gray, 25, 100)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    # Keep this very low-threshold pass on the unfiltered image: smoothing can
    # erase the faint edge between a pale card and a similarly light surface.
    low_edges = cv2.Canny(gray_raw, 5, 25)
    wide_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    masks = [
        cv2.morphologyEx(low_edges, cv2.MORPH_CLOSE, wide_kernel, iterations=3),
        cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2),
        cv2.morphologyEx(cv2.Canny(gray, 50, 160), cv2.MORPH_CLOSE, kernel, iterations=2),
    ]
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    masks.extend([
        cv2.morphologyEx(otsu, cv2.MORPH_CLOSE, kernel, iterations=2),
        cv2.morphologyEx(255 - otsu, cv2.MORPH_CLOSE, kernel, iterations=2),
    ])
    for block_size in (31, 61):
        adaptive = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,
            block_size, 7
        )
        masks.append(cv2.morphologyEx(adaptive, cv2.MORPH_CLOSE, kernel, iterations=2))
        masks.append(cv2.morphologyEx(255 - adaptive, cv2.MORPH_CLOSE, kernel, iterations=2))

    min_area = 0.08 * small.shape[0] * small.shape[1]
    best = None
    best_area = 0
    for mask in masks:
        contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:60]:
            area = cv2.contourArea(contour)
            if area < min_area or area <= best_area:
                continue
            x, y, cw, ch = cv2.boundingRect(contour)
            if x <= 1 and y <= 1 and x + cw >= small.shape[1] - 1 and y + ch >= small.shape[0] - 1:
                continue
            perimeter = cv2.arcLength(contour, True)
            for epsilon in (0.015, 0.02, 0.03, 0.04):
                approx = cv2.approxPolyDP(contour, epsilon * perimeter, True)
                if len(approx) == 4 and cv2.isContourConvex(approx):
                    best = approx.reshape(4, 2).astype(np.float32)
                    best_area = area
                    break

    if best is None:
        return None
    return order_points(best / scale)

def perspective_transform(image,points):
    tl,tr,br,bl=order_points(points)
    w=max(1,int(max(np.linalg.norm(br-bl),np.linalg.norm(tr-tl))))
    h=max(1,int(max(np.linalg.norm(tr-br),np.linalg.norm(tl-bl))))
    dst=np.array([[0,0],[w-1,0],[w-1,h-1],[0,h-1]],np.float32)
    m=cv2.getPerspectiveTransform(np.array([tl,tr,br,bl],np.float32),dst)
    return cv2.warpPerspective(image,m,(w,h))

def enhance_document(image, mode="Magic Color"):
    """Apply selectable scan filters. Input and output are OpenCV BGR images."""
    if mode == "Original":
        return image.copy()

    if mode == "Magic Color":
        # Improve local contrast while retaining document color.
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l = cv2.createCLAHE(clipLimit=2.4, tileGridSize=(8, 8)).apply(l)
        enhanced = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)
        return cv2.bilateralFilter(enhanced, 5, 35, 35)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    if mode == "Grayscale":
        gray = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8)).apply(gray)
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    if mode == "Black & White":
        denoised = cv2.bilateralFilter(gray, 7, 45, 45)
        bw = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 31, 11
        )
        return cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR)

    if mode == "High Contrast":
        boosted = cv2.createCLAHE(clipLimit=3.5, tileGridSize=(8, 8)).apply(gray)
        boosted = cv2.convertScaleAbs(boosted, alpha=1.25, beta=-8)
        _, bw = cv2.threshold(boosted, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR)

    if mode == "Sharpen":
        smooth = cv2.GaussianBlur(gray, (0, 0), 2.0)
        sharp = cv2.addWeighted(gray, 1.7, smooth, -0.7, 0)
        sharp = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(sharp)
        return cv2.cvtColor(sharp, cv2.COLOR_GRAY2BGR)

    if mode == "Shadow Removal":
        # Estimate uneven illumination and normalize it before thresholding.
        background = cv2.medianBlur(gray, 31)
        normalized = cv2.divide(gray, background, scale=255)
        normalized = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(normalized)
        bw = cv2.adaptiveThreshold(
            normalized, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 31, 10
        )
        return cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR)

    # Safe fallback for an unknown filter name.
    return image.copy()


def prepare_for_ocr(image):
    """Create a clean, enlarged grayscale OCR input."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image.copy()
    h, w = gray.shape[:2]
    if max(h, w) < 2200:
        factor = min(2.0, 2200 / max(h, w))
        gray = cv2.resize(gray, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)

    # Reduce camera noise, improve local contrast, and lightly sharpen characters.
    gray = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    gray = cv2.createCLAHE(clipLimit=2.3, tileGridSize=(8, 8)).apply(gray)
    blur = cv2.GaussianBlur(gray, (0, 0), 1.0)
    gray = cv2.addWeighted(gray, 1.35, blur, -0.35, 0)
    return gray


def _ocr_pass(image, lang, psm, threshold_mode):
    """Run one Tesseract pass and preserve detected line breaks."""
    if threshold_mode == "adaptive":
        prepared = cv2.adaptiveThreshold(
            image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 31, 11
        )
    elif threshold_mode == "otsu":
        _, prepared = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    else:
        prepared = image

    import pytesseract
    config = f"--oem 3 --psm {int(psm)} -c preserve_interword_spaces=1"
    data = pytesseract.image_to_data(
        prepared, lang=lang, config=config, output_type=pytesseract.Output.DICT
    )

    lines = {}
    scores = []
    for i, word in enumerate(data["text"]):
        word = word.strip()
        try:
            confidence = float(data["conf"][i])
        except (TypeError, ValueError):
            confidence = -1
        if not word or confidence < 0:
            continue
        key = (
            data["page_num"][i], data["block_num"][i],
            data["par_num"][i], data["line_num"][i]
        )
        lines.setdefault(key, []).append(word)
        scores.append(confidence)

    output = "\n".join(" ".join(words) for words in lines.values())
    mean_confidence = round(float(np.mean(scores)), 1) if scores else 0.0
    return output.strip(), mean_confidence


def extract_text_and_confidence(image, lang="eng", psm=6):
    """Try adaptive, Otsu, and grayscale OCR inputs; return the top confidence result."""
    prepared = prepare_for_ocr(image)
    candidates = [
        _ocr_pass(prepared, lang, psm, "adaptive"),
        _ocr_pass(prepared, lang, psm, "otsu"),
        _ocr_pass(prepared, lang, psm, "none"),
    ]
    # Confidence is a useful selection signal, not a guarantee of text accuracy.
    return max(candidates, key=lambda result: result[1])


def export_multipage_pdf(images,path):
    pw,ph=A4; margin=24; pdf=canvas.Canvas(path,pagesize=A4)
    for image in images:
        pil=Image.fromarray(cv2.cvtColor(image,cv2.COLOR_BGR2RGB))
        scale=min((pw-2*margin)/pil.width,(ph-2*margin)/pil.height)
        dw,dh=pil.width*scale,pil.height*scale
        with tempfile.NamedTemporaryFile(suffix=".jpg",delete=False) as f: tmp=f.name
        try:
            pil.save(tmp,quality=95)
            pdf.drawImage(tmp,(pw-dw)/2,(ph-dh)/2,width=dw,height=dh,preserveAspectRatio=True)
            pdf.showPage()
        finally:
            if os.path.exists(tmp): os.remove(tmp)
    pdf.save()
