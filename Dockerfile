FROM python:3.11-slim

# Avoid interactive prompts during apt install
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies:
# - tesseract-ocr: Open source OCR engine
# - tesseract-ocr-kan: Kannada language training data
# - tesseract-ocr-eng: English language training data
# - poppler-utils: pdftoppm for Linux high-res PDF page rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-kan \
    tesseract-ocr-eng \
    poppler-utils \
    python3-tk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency definition and install
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /app

# Default port for Render, Railway, Cloud Run, etc.
ENV PORT=8000
EXPOSE 8000

# Run the web server
CMD ["python3", "server.py"]
