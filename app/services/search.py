import json
from pathlib import Path
import faiss
import numpy as np

from app.services.server_embedder import embedder

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
CHUNKS_JSON = DATA_DIR / "chunks.json"
FAISS_INDEX = DATA_DIR / "index.faiss"

with open(CHUNKS_JSON, "r", encoding="utf-8") as f:
    chunks = json.load(f)

index = faiss.read_index(str(FAISS_INDEX))

def search(query: str, top_k: int = 5):
    query_vector = embedder([query])[0].astype("float32")
    query_vector = np.expand_dims(query_vector, axis=0)

    distances, indices = index.search(query_vector, top_k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx < 0 or idx >= len(chunks):
            continue
        chunk_data = chunks[idx]
        chunk_data = chunk_data.copy()
        chunk_data["score"] = float(dist)
        results.append(chunk_data)

    return results

