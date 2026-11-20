# Docker step 1: start from a small Python image
FROM python:3.12-slim

# Docker step 2: no .pyc files, direct log output, and tell Python where our code is (src folder)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

# Docker step 3: the working folder inside the image
WORKDIR /app

# Docker step 4: install the packages first, so this layer is reused when only the code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Docker step 5: copy only the code that the app needs (never the .env file)
COPY src ./src
COPY ui ./ui

# Docker step 6: run as a normal user, not as root
RUN useradd --create-home appuser \
    && mkdir -p /app/uploads \
    && chown -R appuser:appuser /app
USER appuser

# Docker step 7: the ports of the API and of the UI (this is only a note, compose opens them)
EXPOSE 8000 8501