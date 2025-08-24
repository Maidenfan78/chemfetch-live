FROM python:3.10-slim

# Install system dependencies for PDF processing and OCR
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY ocr_service.py ./
COPY parse_sds.py ./
COPY sds_parser_new/ ./sds_parser_new/

# Create debug images directory
RUN mkdir -p debug_images

EXPOSE 5001

# Use proper signal handling
CMD ["python", "-u", "ocr_service.py"]
