# main.py

from fastapi import FastAPI, UploadFile, File, Query
from chromadb_utils import extract_chunks_from_pdf, index_chunks, query_text, retrieve_schema, populate_schema_with_content
import os
import uuid

app = FastAPI()

UPLOAD_DIR = "data"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload-pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    chunks = extract_chunks_from_pdf(file_path)
    index_chunks(chunks)
    return {"message": "PDF processed and indexed.", "file_id": file_id}

@app.get("/query/")
def query_endpoint(
    q: str = Query(..., description="Search query"),
    top_k: int = Query(3, description="Number of top results"),
    page_start: int = Query(None, description="Start page filter"),
    page_end: int = Query(None, description="End page filter")
):
    results = query_text(q, top_k=top_k, page_start=page_start, page_end=page_end)
    return {"results": [{"text": text, "citation": citation} for text, citation in results]}

@app.get("/get_schema_content/")
async def get_schema_content(
    filename: str = Query(..., description="Filename to fetch schema from"),
    top_k: int = Query(1, description="Number of results per section")
):
    """Endpoint to retrieve schema and populate with ChromaDB content"""
    try:
        # 1. Retrieve and parse schema
        schema_data = retrieve_schema(filename)
        if not schema_data.get('sections'):
            return {"status": "error", "message": "Empty or invalid schema"}
        
        # 2. Populate with ChromaDB content
        populated_schema = populate_schema_with_content(schema_data, top_k)
        
        return {
            "status": "success",
            "populated_content": populated_schema
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)