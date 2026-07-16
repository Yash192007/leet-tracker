import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

import app as tracker_app


@pytest.fixture
def client():
    tracker_app.DB_PATH = Path(tempfile.gettempdir()) / "tracker_test.db"
    if tracker_app.DB_PATH.exists():
        tracker_app.DB_PATH.unlink()
    tracker_app.init_db()
    tracker_app.app.config.update(TESTING=True)
    with tracker_app.app.test_client() as client:
        yield client


def test_home_page_contains_summary(client):
    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "LeetCode Class Tracker" in html
    assert "Total Students" in html


def test_add_student_and_profile(client):
    response = client.post(
        "/add",
        data={"name": "Yash", "username": "yash123", "password": "secret123"},
        follow_redirects=True,
    )
    assert response.status_code == 200

    conn = sqlite3.connect(tracker_app.DB_PATH)
    row = conn.execute("SELECT name, username FROM students WHERE username = ?", ("yash123",)).fetchone()
    conn.close()
    assert row is not None

    profile_response = client.get("/student/yash123")
    assert profile_response.status_code == 200


def test_add_duplicate_username_returns_error(client):
    client.post(
        "/add",
        data={"name": "Yash", "username": "yash123", "password": "secret123"},
        follow_redirects=True,
    )
    response = client.post(
        "/add",
        data={"name": "Yash Duplicate", "username": "yash123", "password": "secret321"},
        follow_redirects=True,
    )
    assert response.status_code == 400
    assert "Username already exists." in response.get_data(as_text=True)
