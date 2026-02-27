from flask import Flask, render_template, request, jsonify, redirect
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv
# from google.cloud import vision
from google.cloud import vision_v1
import uuid
import re
# import spacy
from models import db, Lead

# nlp = spacy.load("en_core_web_sm")

load_dotenv()

# Initialize Flask app
app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize DB
db.init_app(app)

# Google API
import json
from google.oauth2 import service_account

credentials_info = json.loads(os.environ.get("GOOGLE_CREDENTIALS_JSON"))
credentials = service_account.Credentials.from_service_account_info(credentials_info)

# client = vision.ImageAnnotatorClient(credentials=credentials)

client = vision_v1.ImageAnnotatorClient(
    credentials=credentials,
    transport="rest"
)

# Image text Extraction
def extract_text_from_image(image_bytes):
    image = vision_v1.Image(content=image_bytes)
    # response = client.document_text_detection(image=image)
    response = client.document_text_detection(
        image=image,
        timeout=20
    )

    if response.error.message:
        raise Exception(response.error.message)

    if not response.text_annotations:
        return ""

    return response.text_annotations[0].description

# Image text parsing
address_words = {
    "street", "st", "road", "rd", "lane", "ln",
    "city", "avenue", "ave", "block", "sector", "office", "shop", "no", "number", "floor"
}

designation_keywords = [
    "manager", "owner", "ceo", "cto", "cfo", "founder",
    "director", "head", "designer", "advisor", "consultant",
    "engineer", "developer", "analyst", "marketing",
    "sales", "executive", "president", "lead", "specialist",
    "architect", "officer", "administrator", "advocate", "lawyer", "senior", "surgeon", "accountant"
]

company_keywords = [
    "technologies", "technology", "solutions", "systems",
    "pvt", "ltd", "private", "limited", "corp",
    "corporation", "inc", "llp", "group",
    "industries", "services", "consulting", "graphics", "llc", "india"
]

def looks_like_initials_name(line):
    return bool(
        re.match(r"^([A-Z]\.?[\s]*){1,3}[A-Z]{2,}$", line.strip())
    )


# def extract_entities(text):
#     lines = [l.strip() for l in text.split("\n") if l.strip()]

#     clean_lines = []
#     for line in lines:
#         lower = line.lower()

#         if (
#             "@" in line
#             or re.search(r"\d{6,}", line)
#             or "," in line
#             or any(w in lower for w in address_words)
#         ):
#             continue

#         clean_lines.append(line)

#     name = ""

#     for line in lines:
#         if looks_like_initials_name(line):
#             name = line.title()
#             break

#     if not name:
#         for line in clean_lines:
#             doc = nlp(line)
#             for ent in doc.ents:
#                 if ent.label_ == "PERSON":
#                     name = ent.text
#                     break
#             if name:
#                 break

#     company = ""

#     for line in reversed(clean_lines):
#         lower = line.lower()

#         if (
#             line.isupper()
#             and len(line) > 3
#             and not any(w in lower for w in designation_words)
#         ):
#             company = line
#             break

#     return name, company

def extract_entities(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    clean_lines = []
    for line in lines:
        lower = line.lower()

        if (
            "@" in line
            or re.search(r"\d{6,}", line)
            or "," in line
            or any(w in lower for w in address_words)
        ):
            continue

        clean_lines.append(line)

    company = ""
    for line in clean_lines:
        if any(keyword in line.lower() for keyword in company_keywords):
            company = line
            break

    if not company:
        for line in clean_lines:
            if line.isupper() and len(line.split()) >= 2:
                company = line
                break

    name = ""

    for line in clean_lines:
        if looks_like_initials_name(line):
            name = line.title()
            break

    if not name:
        for line in clean_lines[:5]:
            if (
                line != company
                and not any(k in line.lower() for k in designation_keywords)
                and 2 <= len(line.split()) <= 3
                and line.replace(" ", "").isalpha()
            ):
                name = line.title()
                break

    return name, company

def parse_business_card(text):
    print(text)
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # clean = re.sub(r"[^A-Za-z ]", "", text)

    # name_spacy, company_spacy = extract_entities(clean)

    name_detected, company_detected = extract_entities(text)

    email = re.findall(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        text
    )

    phone_candidates = []

    for line in text.split("\n"):
        match = re.search(r"\+?\d[\d\s\-().]{7,}\d", line)
        if match:
            phone_candidates.append(match.group())

    phones = [
        re.sub(r"[^\d+]", "", p)
        for p in phone_candidates
    ]

    phone = phones[0] if phones else ""
    phone2 = phones[1] if len(phones) > 1 else ""

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

    # name = name_spacy
    name = name_detected

    if not name:
        for line in lines:
            if (
                "@" not in line and "," not in line and "." not in line
                and not re.search(r"\d{4,}", line)
                and 2 <= len(line.split()) <= 3
            ):
                name = line
                break

    # company = company_spacy
    company = company_detected

    designation = ""

    for line in lines:
        lower_line = line.lower()

        if (
            line != name
            and not re.search(r"\d", line)
            and any(keyword in lower_line for keyword in designation_keywords)
        ):
            designation = line
            break

    address = []
    for line in lines:
        if "," in line and len(line) > 15:
            address.append(line)

    address = " ".join(address)

    return {
        "name": name.title(),
        "company": company,
        "designation": designation,
        "email": email[0].lower() if email else "",
        "phone": phone,
        "phone2": phone2,
        "website": website[0].lower() if website else "",
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
def form_page():
    return render_template("form.html")

@app.route("/leads")
def view_leads():
    leads = Lead.query.order_by(Lead.created_at.asc()).all()
    return render_template("leads.html", leads=leads)

@app.route("/edit/<int:id>")
def edit_page(id):
    return render_template("edit.html", id=id)

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
        import traceback
        traceback.print_exc()
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
        phone2=data.get("phone2"),
        email=data.get("email"),
        customer_type=data.get("customer_type"),
        designation=data.get("designation"),
        company=data.get("company"),
        website=data.get("website"),
        address=data.get("address"),
        remarks=data.get("remarks")
    )

    db.session.add(lead)
    db.session.commit()

    return {"status": "saved"}, 200

@app.route("/api/get/<int:id>")
def get_lead(id):
    lead = Lead.query.get_or_404(id)
    return jsonify({
        "name": lead.name,
        "phone": lead.phone,
        "phone2": lead.phone2,
        "email": lead.email,
        "customer_type": lead.customer_type,
        "designation": lead.designation,
        "company": lead.company,
        "website": lead.website,
        "address": lead.address,
        "remarks": lead.remarks,
    })

@app.route("/api/update/<int:id>", methods=["PUT"])
def update_lead(id):
    data = request.get_json()

    lead = Lead.query.get_or_404(id)

    lead.name = data.get("name")
    lead.phone = data.get("phone")
    lead.phone2 = data.get("phone2")
    lead.email = data.get("email")
    lead.customer_type = data.get("customer_type")
    lead.designation = data.get("designation")
    lead.website = data.get("website")
    lead.address = data.get("address")
    lead.company = data.get("company")
    lead.remarks = data.get("remarks")

    db.session.commit()

    return {"status": "saved"}, 200

@app.route("/api/delete/<int:id>")
def delete_lead(id):
    lead = Lead.query.get_or_404(id)
    db.session.delete(lead)
    db.session.commit()
    return redirect("/leads")

# Run App
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000)