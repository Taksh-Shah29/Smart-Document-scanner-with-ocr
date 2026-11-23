# Scanify Pro — Smart Document Scanner

## Features
- Drag-and-drop style manual corner adjustment: drag the four yellow corner handles in the original preview.
- Before/after comparison: original and processed image panes shown side by side.
- Webcam capture from the default camera.
- Multi-page PDF: process an image, click Add PDF Page, open the next image, repeat, then Export Multi-page PDF.
- Branded Scanify Pro loading screen on startup.
- Advanced filters: Original, Magic Color, Grayscale, Black & White, High Contrast, Sharpen, and Shadow Removal.
- Improved OCR: upscaling, denoising, local contrast enhancement, sharpening, adaptive + Otsu threshold passes, preserved line breaks, selectable language/PSM, and mean word confidence.
- Basic unit tests.

## Install (Windows)
1. Install Python 3.9+.
2. Open terminal in this folder.
3. `python -m pip install -r requirements.txt`
4. Install Tesseract OCR separately: https://github.com/UB-Mannheim/tesseract/wiki
5. `python app.py`

If Tesseract is installed but not detected, add this after imports in app.py (adjust path):
`pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"`

## Run tests
`python -m unittest test_scanner.py`

## Demo
Open a tilted document → adjust yellow corners → Enhance → Extract OCR → Add PDF Page → open another image and repeat → Export Multi-page PDF.

## OCR notes
- `pytesseract` is a Python wrapper; the Tesseract desktop engine must be installed separately.
- Default language is `eng`. Install additional trained language data (for example Hindi) before entering its code.
- PSM 6 is a useful starting point for a block of text. Try 3, 4 or 11 for other layouts.
- Confidence is an engine confidence score, not a measured accuracy percentage. For a formal evaluation, compare OCR output against manually transcribed ground truth and calculate character error rate / word error rate.
- Designed for printed text; handwriting recognition is not included.

## Limitations
- Webcam uses camera index 0.
- PDF pages are held in memory until export.
- For manual corners, if automatic detection fails, click Auto Detect; the fallback corner frame is initialized when you click the image, then drag handles. Printed text OCR depends on image quality and installed language data.


## AI-assisted document classification
- Click **Extract OCR**. Scanify Pro then automatically predicts a document category.
- You can also click **AI Classify** after editing or pasting text into the OCR editor.
- Supported categories: Invoice, Receipt, Bank Statement, Identity Document, Academic Document, Letter, Form, and General Document.
- The classifier runs locally using weighted text patterns; it needs no internet connection, API key, or model download.
- Its confidence is a heuristic indicator, not a calibrated probability. OCR mistakes can affect classification, so verify the suggested category before filing or relying on it.
- The popup also provides a suggested filename. Rename the exported file yourself; the app does not silently rename or upload documents.
