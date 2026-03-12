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

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- startup ----
    client = weaviate.connect_to_custom(
        http_host="192.168.233.128", http_port=8080, http_secure=False,
        grpc_host="192.168.233.128", grpc_port=50051, grpc_secure=False,
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
