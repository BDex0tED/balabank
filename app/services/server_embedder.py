from google import genai
from google.genai import types
import numpy as np

client = genai.Client(api_key="AIzaSyCqv5LRxlTDb12eFlWua3iBFBlpmY0QF74") # <- укажи свой api_key

def embedder(texts: list[str]):
    contents = [
        {"parts": [ {"text": t} ]}
        for t in texts
    ]

    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=contents,
        config=types.EmbedContentConfig(output_dimensionality=768)
    )

    vectors = []
    for emb in result.embeddings:
        vec = np.array(emb.values, dtype="float32")
        vec = vec / np.linalg.norm(vec)
        vectors.append(vec)

    return vectors
