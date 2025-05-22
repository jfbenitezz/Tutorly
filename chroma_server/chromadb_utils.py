# chromadb_utils.py

import PyPDF2
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import spacy
import os
import re
import logging
import requests
from typing import Dict, List, Tuple
from collections import OrderedDict

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

# ---------- 1. Extract and Chunk Text with Metadata ----------
def extract_chunks_from_pdf(file_path, MAX_SENTENCES_PER_CHUNK=5):
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
            sentences = [sent.text.strip() for sent in doc.sents]

            # Split into chunks of MAX_SENTENCES_PER_CHUNK
            for k in range(0, len(sentences), MAX_SENTENCES_PER_CHUNK):
                chunk_sentences = sentences[k:k + MAX_SENTENCES_PER_CHUNK]
                chunks.append({
                    "text": " ".join(chunk_sentences),
                    "metadata": {
                        "source": file_path,
                        "page": i + 1,
                        "para_index": j,
                        "chunk_index": k // MAX_SENTENCES_PER_CHUNK,
                        "citation": f"{base_name}, 2024"
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
    return f"Extracted from {meta['citation']} (p. {meta['page']})"

# ---------- 4. Query Interface with Citation-Ready Output ----------
def query_text(query, top_k=3, page_start=None, page_end=None):
    logging.info(f"Executing query: '{query}' (top_k={top_k}, filter_page={page_start},{ page_end})")
    query_embedding = model.encode([f"query: {query}"])[0]

    page_filter = None
    if page_start is not None or page_end is not None:
        conditions = []
        if page_start is not None:
            conditions.append({"page": {"$gte": page_start}})
        if page_end is not None:
            conditions.append({"page": {"$lte": page_end}})
        page_filter = {"$and": conditions} if len(conditions) > 1 else conditions[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=page_filter
    )

    return [
        (doc, cite_apa(meta))
        for doc, meta in zip(results['documents'][0], results['metadatas'][0])
    ]

# ---------- 5. Retrieve Schema from Another Server ----------
schemas_server_url = "http://127.0.0.1:8000/"
def retrieve_schema(filename: str) -> Dict[str, str]:
    """Retrieve schema from another server"""
    try:
        schema_url = f"{schemas_server_url}get_schema/{filename}"
        print(f"Retrieving schema from: {schema_url}")
        response = requests.get(schema_url)
        response.raise_for_status()
        
        # Handle the response format you showed
        if isinstance(response.json(), dict) and 'schema' in response.json():
            return {'sections': parse_text_schema(response.json()['schema'])}
        return response.json()
    except Exception as e:
        logging.error(f"Error retrieving schema: {str(e)}")
        return {}
    
def parse_text_schema(text: str) -> List[Dict]:
    """Parse numbered hierarchy and return clean structure without numbers in titles"""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    root = {'title': 'Root', 'subsections': []}
    stack = [(root, -1)]  # (node, current_depth)
    
    for line in lines:
        # Match numbered items (1., 1.1., etc.)
        match = re.match(r'^(\d+(?:\.\d+)*)\.\s*(.*)', line)
        if not match:
            continue
            
        number_part, title = match.groups()
        depth = number_part.count('.')
        
        # Find appropriate parent
        while stack[-1][1] >= depth:
            stack.pop()
            
        # Create new node with clean title
        parent = stack[-1][0]
        node = {
            'title': title.strip(), 
            'number': number_part,  # Keep original number for reference
            'subsections': []
        }
        parent['subsections'].append(node)
        stack.append((node, depth))
    
    return root['subsections']

def populate_schema_with_content(schema_data: dict, top_k: int = 3) -> dict:
    """Recursively populate schema with ChromaDB results"""
    populated = {}
    
    def process_node(node, path=""):
        # Build the hierarchical path
        current_path = f"{path}/{node['title']}" if path else node['title']
        
        # Query ChromaDB using the clean title (without numbers)
        results = query_text(node['title'], top_k=top_k)
        
        # Store results with both text and citations
        populated[current_path] = [
            {"text": text, "citation": citation}
            for text, citation in results
        ]
        
        # Process all subsections recursively
        for subsection in node.get('subsections', []):
            process_node(subsection, current_path)
    
    # Start processing from top-level sections
    for section in schema_data['sections']:
        process_node(section)
    
    return populated
