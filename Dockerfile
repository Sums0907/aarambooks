FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

# Port is provided via environment variable at runtime (if physical transport is later authorized).
ENV PYTHONPATH=/app
CMD ["python", "-c", "import time; print('AaramBooks Brain Core Started (Logical Mode)'); time.sleep(86400)"]
