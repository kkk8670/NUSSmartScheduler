from fastapi import Request
from weaviate.classes.query import Filter

def insert_chunk(request: Request, user_id: str, kind: str, text: str):
    vs = request.app.state.vectorstore
    vs.add_texts(texts=[text], metadatas=[{"user_id": user_id, "kind": kind}])

def search_chunks(request: Request, user_id: str, query: str, k: int = 5):
    vs = request.app.state.vectorstore
    f = Filter.by_property("user_id").equal(user_id)
    docs = vs.similarity_search_with_score(query, k=k, filters=f)
    return [(d.page_content, s) for d, s in docs]
