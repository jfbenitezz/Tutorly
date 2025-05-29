FROM python:3.11

WORKDIR /app

# 1. First install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Rust (required for some ChromaDB dependencies)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# 3. Copy requirements first for better caching
COPY requirements.txt .

# 4. Install Python packages with specific flags
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of the application
COPY . /app

# 6. Download SpaCy model
RUN python -m spacy download es_core_news_sm

EXPOSE 9000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]