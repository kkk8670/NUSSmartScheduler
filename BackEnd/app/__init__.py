# app/__init__.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .routers import locations, schedule, planner, oauth, calendar as cal_router
from .routers.auth_router import router as auth_router
from .agent import router as agent_router
from .routers.multiagents_router import router as multi_router
from .routers.react_router import router as react_router
# Weaviate / VectorStore
import weaviate
from langchain_openai import OpenAIEmbeddings
from langchain_weaviate.vectorstores import WeaviateVectorStore
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- startup ----
    # WEAVIATE_HOST Preferred environment variable for Docker / K8s / Cloud configuration;
    # Default localhost for local development without setting this variable.
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
        # 连不上 Weaviate 时不阻塞启动（memory/knowledge 功能降级）
        logger.warning(f"Weaviate unavailable ({wv_host}:{wv_http_port}): {e}. Memory/RAG features disabled.")
        app.state.weaviate_client = None
        app.state.vectorstore = None

    yield  # ---- running ----

    # ---- shutdown ----
    if getattr(app.state, "weaviate_client", None):
        app.state.weaviate_client.close()
        app.state.weaviate_client = None
    app.state.vectorstore = None

def create_app() -> FastAPI:
    app = FastAPI(title="NUS Smart Scheduler", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOW_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 路由注册
    app.include_router(locations.router, prefix="/api", tags=["locations"])
    app.include_router(schedule.router,  prefix="/api", tags=["schedule"])
    app.include_router(planner.router,   prefix="/api", tags=["planner"])
    app.include_router(oauth.router,                 tags=["auth"])
    app.include_router(cal_router.router,            tags=["calendar"])
    app.include_router(agent_router.router, prefix="/agent", tags=["agent"])
    app.include_router(multi_router, prefix="/api")
    app.include_router(react_router, prefix="/api")
    app.include_router(auth_router,  prefix="/auth", tags=["auth"])
    return app

__all__ = ["create_app"]
