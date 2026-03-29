import weaviate
from weaviate.classes.config import Property, DataType, Configure, VectorDistances
from app.core.config import settings

client = weaviate.connect_to_custom(
    http_host=settings.WEAVIATE_HOST,
    http_port=settings.WEAVIATE_HTTP_PORT,
    http_secure=False,
    grpc_host=settings.WEAVIATE_HOST,
    grpc_port=settings.WEAVIATE_GRPC_PORT,
    grpc_secure=False,
)

COLL = "MemChunk"

def ensure_collection(dimension: int):
    if COLL not in [c.name for c in client.collections.list_all()]:
        client.collections.create(
            name=COLL,
            properties=[
                Property(name="user_id", data_type=DataType.TEXT),
                Property(name="kind", data_type=DataType.TEXT),
                Property(name="text", data_type=DataType.TEXT),
                Property(name="created_at", data_type=DataType.DATE),
            ],
            vectorizer_config=Configure.Vectorizer.none(),    # 我们自己传向量
            vector_index_config=Configure.VectorIndex.hnsw(
                distance_metric=VectorDistances.COSINE
            ),
        )

def coll():
    return client.collections.get(COLL)
