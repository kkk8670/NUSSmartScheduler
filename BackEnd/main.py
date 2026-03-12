import uvicorn
from starlette.middleware.cors import CORSMiddleware

from app import create_app
from app.core.logging import setup_logging


app = create_app()
setup_logging()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],  # 允许前端来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "Authorization"],  # 必须加 "Authorization"，前端才能带 token
)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)