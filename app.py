"""
XBody EMS Studio - Client Management & Booking System
Module: S2-PFD200 (Professional Development - Task 2)
Author: Nicoleta Loredana Badoi
"""

import sqlite3
import re
from datetime import datetime
from flask import Flask, request, jsonify, render_template, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "xbody_secure_session_key_2026"
DB_FILE = "ems_studio.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # Table 1: Bookings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                preferred_date TEXT NOT NULL,
                preferred_slot TEXT NOT NULL,
                fitness_goal TEXT NOT NULL,
                has_medical_clearance INTEGER NOT NULL,
                status TEXT DEFAULT 'Confirmed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Table 2: Members & Admin Accounts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'Member'
            )
        """)
        # Seed default demo access accounts
        cursor.execute("INSERT OR IGNORE INTO members (email, password, role) VALUES (?, ?, ?)",
                       ("member@xbody.co.uk", "PulseMember2026!", "Member"))
        cursor.execute("INSERT OR IGNORE INTO members (email, password, role) VALUES (?, ?, ?)",
                       ("admin@xbody.co.uk", "PulseAdmin2026!", "Admin"))
        conn.commit()

EMAIL_REGEX = r"^[\w\.-]+@[\w\.-]+\.\w+$"

def validate_booking_payload(data):
    errors = []
    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip()
    phone = data.get("phone", "").strip()
    preferred_date = data.get("preferred_date", "").strip()
    medical_flag = data.get("has_contraindications", False)

    if not full_name or len(full_name) < 2:
        errors.append("A valid full name is required.")
    if not email or not re.match(EMAIL_REGEX, email):
        errors.append("A valid email address is required.")
    if not phone or len(phone) < 7:
        errors.append("A valid phone number is required.")

    try:
        booking_date = datetime.strptime(preferred_date, "%Y-%m-%d").date()
        if booking_date < datetime.today().date():
            errors.append("Session date cannot be in the past.")
    except (ValueError, TypeError):
        errors.append("Date must be in YYYY-MM-DD format.")

    if medical_flag:
        errors.append("EMS Health Alert: Contraindications present. GP clearance certificate required.")

    return errors

# --- PAGES ---
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user_email" not in session:
        return redirect(url_for("login_page"))
    return render_template("dashboard.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# --- APIS ---
@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM members WHERE LOWER(email) = ? AND password = ?", (email, password))
        user = cursor.fetchone()

        if user:
            session["user_email"] = user["email"]
            session["user_role"] = user["role"]
            return jsonify({"success": True, "redirect": "/dashboard"}), 200
        else:
            return jsonify({"success": False, "message": "Invalid email or password."}), 401

@app.route("/api/bookings", methods=["GET"])
def get_bookings():
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, full_name, preferred_date, preferred_slot, fitness_goal FROM bookings ORDER BY preferred_date ASC")
        rows = cursor.fetchall()
        return jsonify([dict(row) for row in rows]), 200

@app.route("/api/bookings", methods=["POST"])
def create_booking():
    data = request.get_json() or {}
    errors = validate_booking_payload(data)

    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM bookings WHERE preferred_date = ? AND preferred_slot = ?",
            (data["preferred_date"], data["preferred_slot"])
        )
        if cursor.fetchone():
            return jsonify({
                "success": False, 
                "errors": ["This time slot on the selected date is already booked. Please choose another."]
            }), 409

        cursor.execute("""
            INSERT INTO bookings (full_name, email, phone, preferred_date, preferred_slot, fitness_goal, has_medical_clearance)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data["full_name"],
            data["email"],
            data["phone"],
            data["preferred_date"],
            data["preferred_slot"],
            data["fitness_goal"],
            0 if data.get("has_contraindications") else 1
        ))
        conn.commit()

    return jsonify({"success": True, "message": "Booking confirmed!"}), 201

if __name__ == "__main__":
    init_db()
    print("XBODY Studio application running at: http://127.0.0.1:5000")
    app.run(debug=True, port=5000)