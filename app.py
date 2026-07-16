import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from flask import Flask, redirect, render_template, request, send_file, session, url_for
from openpyxl import Workbook

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "tracker-secret-key")
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "tracker.db"
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    columns = conn.execute("PRAGMA table_info(students)").fetchall()
    if not columns:
        conn.execute(
            """
            CREATE TABLE students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL DEFAULT 'student123',
                easy INTEGER NOT NULL DEFAULT 0,
                medium INTEGER NOT NULL DEFAULT 0,
                hard INTEGER NOT NULL DEFAULT 0,
                total INTEGER NOT NULL DEFAULT 0,
                last_updated TEXT NOT NULL
            )
            """
        )
    else:
        column_names = [column[1] for column in columns]
        if "password" not in column_names:
            conn.execute("ALTER TABLE students ADD COLUMN password TEXT NOT NULL DEFAULT 'student123'")
    conn.commit()
    conn.close()


init_db()


@app.route("/")
def index():
    conn = sqlite3.connect(DB_PATH)
    students = conn.execute(
        "SELECT name, username, easy, medium, hard, total, last_updated FROM students ORDER BY total DESC"
    ).fetchall()
    conn.close()
    total_students = len(students)
    total_solved = sum(student[5] for student in students)
    easy_solved = sum(student[2] for student in students)
    medium_solved = sum(student[3] for student in students)
    hard_solved = sum(student[4] for student in students)
    return render_template(
        "index.html",
        students=students,
        total_students=total_students,
        total_solved=total_solved,
        easy_solved=easy_solved,
        medium_solved=medium_solved,
        hard_solved=hard_solved,
        admin_logged_in=session.get("admin_logged_in"),
    )


@app.route("/add", methods=["GET", "POST"])
def add_student():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if not name or not username:
            return render_template("add_student.html", error="Both name and username are required."), 400

        try:
            stats = fetch_leetcode_stats(username)
        except Exception:
            stats = {"easy": 0, "medium": 0, "hard": 0, "total": 0}

        now = datetime.now().strftime("%d %B %Y")
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute(
                """
                INSERT INTO students (name, username, password, easy, medium, hard, total, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (name, username, password or "student123", stats["easy"], stats["medium"], stats["hard"], stats["total"], now),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return render_template("add_student.html", error="Username already exists."), 400
        conn.close()
        return redirect(url_for("index"))

    return render_template("add_student.html")


@app.route("/student/<username>")
def student_profile(username: str):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT name, username, easy, medium, hard, total, last_updated FROM students WHERE username = ?",
        (username,),
    ).fetchone()
    conn.close()
    if not row:
        return render_template("student_profile.html", error="Student not found."), 404
    return render_template("student_profile.html", student=row)


@app.route("/refresh")
def refresh_all():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT username FROM students").fetchall()
    conn.close()
    for (username,) in rows:
        try:
            stats = fetch_leetcode_stats(username)
        except Exception:
            stats = {"easy": 0, "medium": 0, "hard": 0, "total": 0}
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "UPDATE students SET easy = ?, medium = ?, hard = ?, total = ?, last_updated = ? WHERE username = ?",
            (stats["easy"], stats["medium"], stats["hard"], stats["total"], datetime.now().strftime("%d %B %Y"), username),
        )
        conn.commit()
        conn.close()
    return redirect(url_for("index"))


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session.clear()
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        return render_template("admin_login.html", error="Invalid admin credentials."), 400
    return render_template("admin_login.html")


@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    conn = sqlite3.connect(DB_PATH)
    students = conn.execute(
        "SELECT id, name, username, easy, medium, hard, total FROM students ORDER BY total DESC"
    ).fetchall()
    conn.close()
    total_students = len(students)
    total_solved = sum(student[6] for student in students)
    easy_solved = sum(student[3] for student in students)
    medium_solved = sum(student[4] for student in students)
    hard_solved = sum(student[5] for student in students)
    return render_template(
        "admin_dashboard.html",
        students=students,
        total_students=total_students,
        total_solved=total_solved,
        easy_solved=easy_solved,
        medium_solved=medium_solved,
        hard_solved=hard_solved,
    )


@app.route("/remove", methods=["POST"])
def remove_student():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    username = request.form.get("username", "").strip()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM students WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/export")
def export_excel():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT name, username, easy, medium, hard, total FROM students ORDER BY total DESC"
    ).fetchall()
    conn.close()

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Students"
    sheet.append(["Name", "Username", "Easy", "Medium", "Hard", "Total"])
    for row in rows:
        sheet.append(row)

    export_path = BASE_DIR / "students_export.xlsx"
    workbook.save(export_path)
    return send_file(export_path, as_attachment=True, download_name="students_export.xlsx")


@app.route("/search")
def search_students():
    query = request.args.get("q", "").strip()
    conn = sqlite3.connect(DB_PATH)
    if query:
        rows = conn.execute(
            "SELECT name, username, easy, medium, hard, total, last_updated FROM students WHERE name LIKE ? OR username LIKE ? ORDER BY total DESC",
            (f"%{query}%", f"%{query}%"),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT name, username, easy, medium, hard, total, last_updated FROM students ORDER BY total DESC"
        ).fetchall()
    conn.close()
    return render_template("index.html", students=rows, total_students=len(rows), total_solved=sum(student[5] for student in rows), easy_solved=sum(student[2] for student in rows), medium_solved=sum(student[3] for student in rows), hard_solved=sum(student[4] for student in rows), query=query)


def fetch_leetcode_stats(username: str) -> dict[str, int]:
    url = "https://leetcode.com/graphql"
    payload = {
        "query": """
        query userProfile($username: String!) {
          matchedUser(username: $username) {
            submitStatsGlobal {
              acSubmissionNum {
                difficulty
                count
              }
            }
          }
        }
        """,
        "variables": {"username": username},
    }
    response = requests.post(url, json=payload, timeout=15)
    response.raise_for_status()
    data = response.json()
    if not data.get("data", {}).get("matchedUser"):
        raise ValueError(f"LeetCode user {username} was not found.")

    stats = data["data"]["matchedUser"]["submitStatsGlobal"]["acSubmissionNum"]
    easy = next(item["count"] for item in stats if item["difficulty"] == "Easy")
    medium = next(item["count"] for item in stats if item["difficulty"] == "Medium")
    hard = next(item["count"] for item in stats if item["difficulty"] == "Hard")
    return {"easy": easy, "medium": medium, "hard": hard, "total": easy + medium + hard}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG", "0") == "1")
