from flask import Flask, render_template, request, jsonify, redirect
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv
from google.cloud import vision
import uuid
import re
import spacy
from models import db, Lead

nlp = spacy.load("en_core_web_sm")

load_dotenv()

# Initialize Flask app
app = Flask(__name__)

app.config["SECRET_KEY"] = "dev-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///leads.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize DB
db.init_app(app)

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
def extract_entities(text):
    doc = nlp(text)

    name = ""
    company = ""

    for ent in doc.ents:
        if ent.label_ == "PERSON" and not name:
            name = ent.text

        elif ent.label_ == "ORG" and not company:
            company = ent.text

    return name, company

def parse_business_card(text):
    import re

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    clean = re.sub(r"[^A-Za-z ]", "", text)

    name_spacy, company_spacy = extract_entities(clean)

    email = re.findall(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        text
    )

    phone = re.findall(r"\+?\d[\d\s\-.()]{8,20}\d", text)
    phone = phone[0] if phone else ""
    phone = re.sub(r"[^\d+]", "", phone)

    clean_text = text
    for e in email:
        clean_text = clean_text.replace(e, "")

    website = re.findall(
        r"(?:https?://)?(?:www\.)?[A-Za-z0-9-]+\.[A-Za-z]{2,}(?:\.[A-Za-z]{2,})?",
        clean_text
    )

    website = [
        w for w in website
        if "@" not in w and " " not in w
    ]

    name = name_spacy
    if not name:
        for line in lines:
            if (
                "@" not in line
                and not re.search(r"\d{4,}", line)
                and 2 <= len(line.split()) <= 3
            ):
                name = line
                break

    company = company_spacy

    designation = ""
    for line in lines:
        if len(line) > 20 and line != name and ',' not in line and '.' not in line and not re.search(r"\d", line):
            designation = line
            break

    address = ""
    for line in lines:
        if "," in line and len(line) > 15:
            address = line

    return {
        "name": name,
        "company": company,
        "designation": designation,
        "email": email[0] if email else "",
        "phone": phone,
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

@app.route("/leads")
def view_leads():
    leads = Lead.query.order_by(Lead.created_at.desc()).all()
    return render_template("leads.html", leads=leads)

@app.route("/delete/<int:id>")
def delete_lead(id):
    lead = Lead.query.get_or_404(id)
    db.session.delete(lead)
    db.session.commit()
    return redirect("/leads")

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

@app.route("/api/save", methods=["POST"])
def save():
    data = request.get_json()

    if not data:
        return {"error": "Bad request"}, 400

    existing = Lead.query.filter_by(email=data.get("email")).first()
    if existing:
        return {"error": "Email already exists"}, 400
    
    lead = Lead(
        name=data.get("name"),
        phone=data.get("phone"),
        email=data.get("email"),
        designation=data.get("designation"),
        company=data.get("company"),
        website=data.get("website"),
        address=data.get("address"),
        remarks=data.get("remarks")
    )

    db.session.add(lead)
    db.session.commit()

    return {"status": "saved"}, 200


# Run App
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)