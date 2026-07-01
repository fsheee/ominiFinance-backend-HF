import os
from typing import Dict, Any, List, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

CHROMA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".chroma")

_client: Optional[chromadb.PersistentClient] = None
_collection: Optional[chromadb.Collection] = None
_embedding_model: Optional[SentenceTransformer] = None
_seeded = False


def _get_embedding(text: str) -> List[float]:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model.encode(text).tolist()


def seed_knowledge_base(knowledge_base: Dict[str, Dict[str, str]]):
    global _client, _collection, _seeded

    if _seeded:
        return

    _client = chromadb.PersistentClient(
        path=CHROMA_DIR,
        settings=Settings(anonymized_telemetry=False)
    )

    _collection = _client.get_or_create_collection(
        name="financial_knowledge",
        metadata={"hnsw:space": "cosine"}
    )

    if _collection.count() > 0:
        _seeded = True
        return

    ids = []
    documents = []
    metadatas = []

    for term, data in knowledge_base.items():
        doc_text = f"{data['definition']} {data.get('explanation', '')}"
        ids.append(term)
        documents.append(doc_text)
        metadatas.append({
            "term": term,
            "definition": data["definition"],
            "analogy": data.get("analogy", ""),
            "explanation": data.get("explanation", "")
        })

    _collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )

    _seeded = True

def search_knowledge(query: str, n_results: int = 5) -> List[Dict[str, Any]]:
    if _collection is None:
        return []

    query_embedding = _get_embedding(query)
    results = _collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )

    out = []
    if not results["metadatas"] or not results["metadatas"][0]:
        return out

    for i, metadata in enumerate(results["metadatas"][0]):
        distance = results["distances"][0][i] if results.get("distances") else 0.0
        similarity = max(0.0, 1.0 - distance)
        out.append({
            "term": metadata["term"],
            "definition": metadata["definition"],
            "analogy": metadata["analogy"],
            "explanation": metadata["explanation"],
            "score": round(similarity, 4)
        })

    return out
