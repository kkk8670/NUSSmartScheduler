# BackEnd/tests/conftest.py 

"""
conftest.py — global pytest fixtures
public share：TestClient、JWT token、mock DB session
"""
import os
import sys
from unittest.mock import MagicMock

# 1. 注入环境变量
os.environ.setdefault("OPENAI_API_KEY",        "sk-test-fake")
os.environ.setdefault("JWT_SECRET_KEY",        "test-secret-key-for-pytest")
os.environ.setdefault("JWT_ALGORITHM",         "HS256")
os.environ.setdefault("JWT_EXPIRE_MINUTES",    "60")
os.environ.setdefault("DATABASE_URL",          "sqlite:///:memory:")
os.environ.setdefault("WEAVIATE_URL",          "http://localhost:8080")
os.environ.setdefault("WEAVIATE_HOST",         "localhost")
os.environ.setdefault("WEAVIATE_HTTP_PORT",    "8080")
os.environ.setdefault("WEAVIATE_GRPC_PORT",    "50051")
os.environ.setdefault("AGENT_MODEL",           "gpt-4o-mini")
os.environ.setdefault("AGENT_TEMPERATURE",     "0")

# 2. 替换掉整个wv 模块
mock_wv_module = MagicMock()
mock_wv_module.client = MagicMock()
mock_wv_module.coll = MagicMock(return_value=MagicMock())
mock_wv_module.ensure_collection = MagicMock()
sys.modules["app.db.wv"] = mock_wv_module
 
# 3. 拦截 weaviate 本身 
mock_weaviate = MagicMock()
mock_weaviate.connect_to_custom = MagicMock(return_value=MagicMock())
sys.modules.setdefault("weaviate", mock_weaviate)


# start import

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from dotenv import load_dotenv
load_dotenv(override=False) 

 

# ── Block external connections for CI ──
@pytest.fixture(scope="session", autouse=True)
def mock_weaviate():
    '''
    Weaviate is initialized by lifespan when the app starts.
    Weaviate is not available in CI and must be intercepted at the beginning of the session.
    '''
    with patch("app.db.wv.init_weaviate", return_value=MagicMock()):
        yield


@pytest.fixture(scope="session", autouse=True)
def mock_db_engine():
    """
    get_engine() is called in travel_graph and session.py.
    Replace it with MagicMock to avoid real MySQL connections.
    """
    with patch("app.db.session.get_engine", return_value=MagicMock()):
        yield


# ── App & TestClient（session level, creating once）──
@pytest.fixture(scope="session")
def client(mock_weaviate, mock_db_engine):
    """
    TestClient is used by test_api.py to make requests.
    Rely on mock_weaviate and mock_db_engine to ensure not connected real service at startup.
    """
    from app import create_app
    app = create_app()
    with TestClient(app) as c:
        yield c


# ──────────── public test data ─────────────── 
@pytest.fixture
def sample_task():
    """singal task，test_scheduler & test_api will use """
    from app.schemas.tasks import TaskIn
    return TaskIn(
        id="t1",
        title="Study",
        location="COM1",
        earliest="09:00",
        latest="12:00",
        duration_min=60,
        fixed=False,
        priority=2,
    )


@pytest.fixture
def sample_tasks():
    """wo tasks in two different locations to test travel gap and no_overlap."""
    from app.schemas.tasks import TaskIn
    return [
        TaskIn(
            id="t1",
            title="Study",
            location="COM1",
            earliest="09:00",
            latest="12:00",
            duration_min=60,
            fixed=False,
            priority=2,
        ),
        TaskIn(
            id="t2",
            title="Lunch",
            location="USC",
            earliest="12:00",
            latest="14:00",
            duration_min=45,
            fixed=False,
            priority=1,
        ),
    ]

