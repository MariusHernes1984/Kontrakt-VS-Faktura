#!/bin/bash
# Installer systempakker for OCR (Tesseract + Poppler) hvis de mangler.
if ! command -v tesseract >/dev/null 2>&1; then
    echo "Installerer tesseract-ocr og poppler-utils..."
    apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr tesseract-ocr-nor tesseract-ocr-eng poppler-utils
fi

gunicorn --bind=0.0.0.0:8000 --timeout 180 app:app
