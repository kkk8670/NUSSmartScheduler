# app/__init__.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .core.config import settings
from .core.limiter import limiter
from .core.tracing import get_langfuse, flush as lf_flush
from .routers import locations, schedule, planner, oauth, calendar as cal_router
from .routers.auth_router import router as auth_router
from .agent import router as agent_router
from .routers.multiagents_router import router as multi_router

# Weaviate / VectorStore
import weaviate
from langchain_openai import OpenAIEmbeddings
from langchain_weaviate.vectorstores import WeaviateVectorStore
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- startup ----
    get_langfuse()

    wv_host = settings.WEAVIATE_HOST
    wv_http_port = settings.WEAVIATE_HTTP_PORT
    wv_grpc_port = settings.WEAVIATE_GRPC_PORT

    try:
        client = weaviate.connect_to_custom(
            http_host=wv_host, http_port=wv_http_port, http_secure=False,
            grpc_host=wv_host, grpc_port=wv_grpc_port, grpc_secure=False,
        )
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.OPENAI_API_KEY,
        )
        vs = WeaviateVectorStore(
            client=client,
            index_name="MemChunk",
            text_key="text",
            embedding=embeddings,
        )
        app.state.weaviate_client = client
        app.state.vectorstore = vs

    except Exception as e:
        logger.warning(f"Weaviate unavailable ({wv_host}:{wv_http_port}): {e}. Memory/RAG features disabled.")
        app.state.weaviate_client = None
        app.state.vectorstore = None

    yield  # ---- running ----

    lf_flush()

    if getattr(app.state, "weaviate_client", None):
        app.state.weaviate_client.close()
        app.state.weaviate_client = None
    app.state.vectorstore = None

def create_app() -> FastAPI:
    app = FastAPI(title="NUS Smart Scheduler", version="0.1.0", lifespan=lifespan)

    # Rate limiting：按 IP 限流，超限返回 429
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOW_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 路由注册
    app.include_router(locations.router, prefix="/api/locations", tags=["locations"])
    app.include_router(schedule.router, prefix="/api/schedule", tags=["schedule"])
    app.include_router(planner.router, prefix="/api/planner", tags=["planner"])

    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(oauth.router, prefix="/auth/oauth", tags=["auth"])

    app.include_router(cal_router.router, prefix="/api/calendar", tags=["calendar"])
    app.include_router(agent_router.router, prefix="/api/agent", tags=["agent"])
    app.include_router(multi_router, prefix="/api/multi")

    return app

__all__ = ["create_app"]