import unittest
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.main import app

client = TestClient(app)


class TestMainAPI(unittest.TestCase):
    def setUp(self):
        # Create a mock database session
        self.mock_db = MagicMock(spec=Session)
        # Override the dependency generator
        app.dependency_overrides[get_db] = lambda: self.mock_db

    def tearDown(self):
        # Clear dependency overrides
        app.dependency_overrides.clear()

    def test_read_root(self):
        """Test the entrypoint index route."""
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(json_data["status"], "online")
        self.assertEqual(json_data["app"], "Noted Ma'am")

    def test_check_health_degraded_when_no_services(self):
        """Test health status degrades when backing services are offline."""
        # By default mock connections raise exceptions or return unhealthy
        self.mock_db.execute.side_effect = Exception("DB Connection Error")

        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(json_data["status"], "degraded")
        self.assertIn(
            "unhealthy: DB Connection Error", json_data["components"]["database"]
        )
