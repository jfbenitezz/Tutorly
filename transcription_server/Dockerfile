FROM python:3.9-slim

WORKDIR /app
COPY . .

RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install -r requirements.txt

CMD ["uvicorn", "fastapi_server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]