import uvicorn
from starlette.middleware.cors import CORSMiddleware

from app import create_app
from app.core.logging import setup_logging

from prometheus_fastapi_instrumentator import Instrumentator



app = create_app()
setup_logging()

Instrumentator().instrument(app).expose(app)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)