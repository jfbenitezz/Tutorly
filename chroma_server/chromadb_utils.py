# -*- coding: utf-8 -*-

import PyPDF2
from sentence_transformers import SentenceTransformer
from chromadb.config import Settings
import chromadb
import spacy
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("chromadb_operations.log"),
        logging.StreamHandler()
    ]
)

# Initialize ChromaDB
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection("e5-bibliography")

# Load sentence embedding model
model = SentenceTransformer("intfloat/multilingual-e5-small")
nlp = spacy.load("es_core_news_sm")

"""## Functions

"""

# ---------- 1. Extract and Chunk Text with Metadata ----------
def extract_chunks_from_pdf(file_path):
    logging.info(f"Extracting chunks from: {file_path}")
    reader = PyPDF2.PdfReader(file_path)
    chunks = []
    base_name = os.path.basename(file_path).replace(".pdf", "")

    for i, page in enumerate(reader.pages):
        page_text = page.extract_text()
        if not page_text:
            continue

        paragraphs = [p.strip() for p in page_text.split('\n\n') if len(p.strip()) > 50]

        for j, para in enumerate(paragraphs):
            doc = nlp(para)
            # Join SpaCy-detected sentences
            sentence_chunk = " ".join([sent.text.strip() for sent in doc.sents])
            chunks.append({
                "text": sentence_chunk,
                "metadata": {
                    "source": file_path,
                    "page": i + 1,
                    "para_index": j,
                    "citation": f"{base_name}, {2024}"  # or a dynamic year
                }
            })
    logging.info(f"Extracted {len(chunks)} chunks from {file_path}")
    return chunks

# ---------- 2. Index Chunks into ChromaDB ----------
def index_chunks(chunks):
    texts = [f"passage: {chunk['text']}" for chunk in chunks]
    metadatas = [chunk["metadata"] for chunk in chunks]
    embeddings = model.encode(texts, normalize_embeddings=True)

    collection.add(
        documents=texts,
        embeddings=embeddings.tolist(),
        metadatas=metadatas,
        ids=[str(i) for i in range(len(chunks))]
    )

# ---------- 3. Citation Formatter ----------
def cite_apa(meta):
    return f"{meta['citation']} (p. {meta['page']})"

# ---------- 4. Query Interface with Citation-Ready Output ----------
    """
    Query ChromaDB with optional page range filtering.

    Args:
        query: Search string
        top_k: Number of results
        page_start: First page to include (inclusive). None = start from first page.
        page_end: Last page to include (inclusive). None = go until last page.
    """
def query_text(query, top_k=3, page_start=None, page_end=None):
    logging.info(f"Executing query: '{query}' (top_k={top_k}, filter_page={page_start},{ page_end})")
    query_embedding = model.encode([f"query: {query}"])[0]

    # Build page filter if any range is specified
    page_filter = None
    if page_start is not None or page_end is not None:
        conditions = []

        if page_start is not None:
            conditions.append({"page": {"$gte": page_start}})

        if page_end is not None:
            conditions.append({"page": {"$lte": page_end}})

        # Combine conditions with $and if multiple, use single condition directly if only one
        page_filter = {"$and": conditions} if len(conditions) > 1 else conditions[0]

    #Query Chorma Client
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=page_filter  # None if no page filtering
    )

    return [
        (doc, cite_apa(meta))
        for doc, meta in zip(results['documents'][0], results['metadatas'][0])
    ]

chunks = extract_chunks_from_pdf("test.pdf")
index_chunks(chunks)

results = query_text("Asociación Ticket a Empresa")
for i, (text, citation) in enumerate(results):
    print(f"\nResult {i + 1}:")
    print(text)
    print(f"— {citation}")

results = query_text("horas trabajadas en ticket abierto", page_start=10, page_end=31)
for i, (text, citation) in enumerate(results):
    print(f"\nResult {i + 1}:")
    print(text)
    print(f"— {citation}")