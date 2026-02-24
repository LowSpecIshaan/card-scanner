from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv
from google.cloud import vision
import uuid
import re

load_dotenv()

# Initialize Flask app
app = Flask(__name__)

app.config["SECRET_KEY"] = "dev-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///leads.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize DB
db = SQLAlchemy(app)

client = vision.ImageAnnotatorClient()

# Image text Extraction
def extract_text_from_image(image_bytes):
    image = vision.Image(content=image_bytes)
    response = client.document_text_detection(image=image)

    if response.error.message:
        raise Exception(response.error.message)

    if not response.text_annotations:
        return ""

    return response.text_annotations[0].description

# Image text parsing
def parse_business_card(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    email = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    phone = re.findall(r"\+?\d[\d\s\-.()]{8,20}\d", text)
    phone = phone[0] if phone else ""
    phone = phone.replace(".", "")
    phone = phone.replace("-", "")
    phone = phone.strip()
    website = re.findall(r"(?:www\.)?[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)

    website = [w for w in website if "@" not in w]

    name = ""
    designation = ""
    address = ""

    for line in lines:
        if "@" not in line and not re.search(r"\d{4,}", line):
            name = line
            break

    if name in lines:
        idx = lines.index(name)
        if idx + 1 < len(lines):
            designation = lines[idx + 1]

    for line in lines:
        if "," in line and len(line) > 15:
            address = line

    return {
        "name": name,
        "designation": designation,
        "email": email[0] if email else "",
        "phone": phone if phone else "",
        "website": website[0] if website else "",
        "address": address
    }

# Frontend Routes
@app.route('/')
def home():
    return render_template("index.html")

@app.route('/scan')
def scan_page():
    return render_template("scan.html")

@app.route("/form")
def edit_page():
    return render_template("form.html")

# API Routes
@app.route("/api/scan", methods=["POST"])
def scan_card():
    image = request.files.get("image")

    if not image:
        return jsonify({"error": "No image received"}), 400

    try:
        image_bytes = image.read()
        text = extract_text_from_image(image_bytes)

        parsed = parse_business_card(text)

        return jsonify({
            "status": "success",
            **parsed
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


# Run App
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)