from flask import Flask, render_template, request, jsonify, redirect, send_file, current_app
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import io
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv
from google.cloud import vision_v1
import uuid
import re
from models import db, Lead, User, Exhibition
import pandas as pd
from google import genai
from google.genai import types
from pydantic import BaseModel
import json
from brevo import Brevo
from brevo.transactional_emails import (
    SendTransacEmailRequestSender,
    SendTransacEmailRequestToItem,
)
from datetime import datetime, timedelta
from threading import Thread

load_dotenv()

# Initialize Flask app
app = Flask(__name__)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login_page"

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

#Gemini
gemini_client = genai.Client()

def extract_business_card_with_gemini(image_bytes):
    response = gemini_client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=[
            types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/jpeg"
            ),
            """
            Extract the information from this business card.

            Return:
            - name
            - phone
            - phone2
            - email
            - designation
            - company
            - website
            - address
            - customer_type

            Rules:
            - Only use information present on the card.
            - Do not invent missing information.
            - Return an empty string if a field is unavailable.
            - Format phone numbers as +<country_code><space><number>. (no space or bracket or hifen in between the phone number)
            - Correct obvious OCR/reading errors when the intended value is clear.
            - If multiple phone numbers exist, put the primary number in phone
              and the second number in phone2.
            """
        ],
        config={
            "response_mime_type": "application/json"
        }
    )

    return json.loads(response.text)

# Clean Text
def clean_data(data):
    if data.get("email"):
        data["email"] = data["email"].strip().lower()

    if data.get("website"):
        data["website"] = data["website"].strip().lower()

    if data.get("name"):
        data["name"] = data["name"].strip().title()

    return data

# Auth
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()

    user = User.query.filter_by(name=data["id"]).first()

    if not user or not user.check_password(data["password"]):
        return {"error": "Invalid credentials"}, 401

    login_user(user)
    return {"status": "logged_in"}, 200

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")

# Email

brevo_client = Brevo(
    api_key=os.environ.get("BREVO_API_KEY")
)

def send_followup_email(lead):
    sender_email = os.environ.get("BREVO_SENDER_EMAIL")
    sender_name = os.environ.get("BREVO_SENDER_NAME", "Your Company")

    user = db.session.get(User, lead.user_id)
    company_name = user.company_name if user and user.company_name else "Our Team"

    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="
        margin:0;
        padding:30px 15px;
        background:#f5f7fa;
        font-family:Arial, Helvetica, sans-serif;
    ">

    <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
    <td align="center">

    <table width="600" cellpadding="0" cellspacing="0"
        style="
            max-width:600px;
            width:100%;
            background:#ffffff;
            border-radius:10px;
            padding:40px;
        ">

    <tr>
    <td>

    <h2 style="
        margin:0 0 25px;
        color:#222;
        font-size:22px;
    ">
        Hi {lead.name},
    </h2>

    <p style="
        color:#444;
        font-size:16px;
        line-height:1.7;
        margin:0 0 18px;
    ">
        It was great connecting with you at
        <strong>{lead.exhibition.name}</strong>!
    </p>

    <p style="
        color:#444;
        font-size:16px;
        line-height:1.7;
        margin:0 0 28px;
    ">
        Kindly share your requirements with us, and we would be
        happy to assist you.
    </p>

    <p style="
        color:#444;
        font-size:16px;
        line-height:1.6;
        margin:0;
    ">
        Regards,<br>
        <strong>{company_name or "Our Team"}</strong>
    </p>

    </td>
    </tr>

    </table>

    </td>
    </tr>
    </table>

    </body>
    </html>
    """

    result = brevo_client.transactional_emails.send_transac_email(
        subject=f"{lead.name}, thank you for connecting at {lead.exhibition.name}",

        html_content=html,

        sender=SendTransacEmailRequestSender(
            name=sender_name,
            email=sender_email
        ),

        to=[
            SendTransacEmailRequestToItem(
                email=lead.email,
                name=lead.name
            )
        ]
    )

    print("EMAIL SENT:", result.message_id)


def send_email_background(lead_id, app):
    with app.app_context():
        try:
            lead = db.session.get(Lead, lead_id)

            if not lead:
                print(f"BACKGROUND EMAIL ERROR: Lead {lead_id} not found")
                return

            send_followup_email(lead)

        except Exception as e:
            print("BACKGROUND EMAIL ERROR:", repr(e))

        finally:
            db.session.remove()

# Initialize DB
db.init_app(app)

# Google API
# import json
# from google.oauth2 import service_account

# credentials_info = json.loads(os.environ.get("GOOGLE_CREDENTIALS_JSON"))
# credentials = service_account.Credentials.from_service_account_info(credentials_info)

# client = vision_v1.ImageAnnotatorClient(
#     credentials=credentials,
#     transport="rest"
# )

# Image text Extraction
# def extract_text_from_image(image_bytes):
#     image = vision_v1.Image(content=image_bytes)
#     response = client.document_text_detection(
#         image=image,
#         timeout=20
#     )

#     if response.error.message:
#         raise Exception(response.error.message)

#     if not response.text_annotations:
#         return ""

#     return response.text_annotations[0].description

# Image text parsing
# designation_keywords = [
#     "manager", "owner", "ceo", "cto", "cfo", "founder",
#     "director", "head", "designer", "advisor", "consultant",
#     "engineer", "developer", "analyst", "marketing",
#     "sales", "executive", "president", "lead", "specialist",
#     "architect", "officer", "administrator", "advocate", "lawyer", "senior", "surgeon", "accountant"
# ]

# company_keywords = [
#     "technologies", "solutions", "systems",
#     "pvt", "ltd", "private", "limited", "corp",
#     "corporation", "inc", "llp", "group",
#     "industries", "services", "consulting", "llc", "india",
#     "doors", "wood", "enterprise", "sons", "lab", 
#     "decor", "kitchen", "hardware", "decorators", "l&c", "studio", "designers", 
#     "interior", "company", "co", "associates", "agency", "traders", "exports", "imports",
#     "builders", "construction", "family", "media", "digital",
#     "engineering", "enterprises", "global", "international", "transport", "designs", "rubber", "polymer",
#     "furniture", "plastic", "silicon", "steel", "paper", "polymer", "silk", "agencies", "media", "ware", 
#     "ceramics", "industry", "insurance", "bharat"
# ]

# def looks_like_initials_name(line):
#     line = line.strip()

#     if re.match(r"^([A-Z]\.? ){1,3}[A-Z][a-z]+$", line):
#         return True

#     if re.match(r"^[A-Z]{2,}\s[A-Z]{2,}$", line):
#         return True

#     return False

# def extract_entities(text):
#     lines = [l.strip() for l in text.split("\n") if l.strip()]

#     clean_lines = []
#     for line in lines:
#         lower = line.lower()

#         if (
#             "@" in line
#             or re.search(r"\+?\d[\d\s\-().]{7,}\d", line)
#             or "," in line
#             or re.search(r"(?:https?://)?(?:www\.)?[A-Za-z0-9-]+\.[A-Za-z]{2,}(?:\.[A-Za-z]{2,})?", line)
#         ):  
#             continue

#         clean_lines.append(line)

#     name = ""

#     for line in clean_lines:
#         if (looks_like_initials_name(line)
#             and not any(k in line.lower() for k in company_keywords) 
#             and not any(k in line.lower() for k in designation_keywords)
#         ):
#             name = line.title()
#             break

#     if not name:
#         for line in clean_lines[:5]:
#             if (not any(k in line.lower() for k in company_keywords) 
#                 and not any(k in line.lower() for k in designation_keywords)
#                 and 2 <= len(line.split()) <= 3
#                 and line.replace(" ", "").isalpha()
#             ):
#                 name = line.title()
#                 break

#     company = ""
#     for line in clean_lines:
#         if any(keyword in line.lower() for keyword in company_keywords):
#             company = line.title()
#             break

#     if not company:
#         for line in clean_lines:
#             if not any(k in line.lower() for k in designation_keywords) and 1 <= len(line.split()) <= 4 and line.title() != name:
#                 company = line.title()
#                 break

#     return name, company

# def parse_business_card(text):
#     lines = [l.strip() for l in text.split("\n") if l.strip()]

#     name, company = extract_entities(text)

#     email = re.findall(
#         r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
#         text
#     )

#     phone_candidates = []

#     for line in text.split("\n"):
#         match = re.search(r"\+?\d[\d\s\-().]{7,}\d", line)
#         if match:
#             phone_candidates.append(match.group())

#     phones = [
#         re.sub(r"[^\d+]", "", p)
#         for p in phone_candidates
#     ]

#     phone = phones[0] if phones else ""
#     phone2 = phones[1] if len(phones) > 1 else ""

#     clean_text = text
#     for e in email:
#         clean_text = clean_text.replace(e, "")

#     website = re.findall(
#         r"(?:https?://)?(?:www\.)?[A-Za-z0-9-]+\.[A-Za-z]{2,}(?:\.[A-Za-z]{2,})?",
#         clean_text
#     )

#     website = [
#         w for w in website
#         if "@" not in w and " " not in w
#     ]

#     designation = ""

#     for line in lines:
#         lower_line = line.lower()

#         if (
#             line != name
#             and not re.search(r"\d", line)
#             and any(keyword in lower_line for keyword in designation_keywords)
#         ):
#             designation = line
#             break

#     address = []
#     for line in lines:
#         if "," in line and len(line) > 15:
#             address.append(line)

#     address = " ".join(address)

#     return_dict = {
#         "name": name,
#         "company": company,
#         "designation": designation,
#         "email": email[0].lower() if email else "",
#         "phone": phone,
#         "phone2": phone2,
#         "website": website[0].lower() if website else "",
#         "address": address
#     }

#     return return_dict

# Frontend Routes
@app.route('/')
@login_required
def home():
    exhibitions = Exhibition.query.filter_by(
        user_id=current_user.id
    ).order_by(Exhibition.name).all()

    return render_template(
        "index.html",
        exhibitions=exhibitions
    )

@app.route('/scan')
@login_required
def scan_page():
    return render_template("scan.html")

@app.route("/form")
@login_required
def form_page():
    return render_template("form.html")

@app.route("/leads")
@login_required
def view_leads():
    exhibition_id = request.args.get("exhibition_id", type=int)

    query = Lead.query.filter_by(
        is_deleted=False,
        user_id=current_user.id
    )

    if exhibition_id:
        query = query.filter_by(exhibition_id=exhibition_id)

    leads = query.order_by(Lead.created_at.asc()).all()

    exhibitions = Exhibition.query.filter_by(
        user_id=current_user.id
    ).order_by(Exhibition.name).all()

    return render_template(
        "leads.html",
        leads=leads,
        exhibitions=exhibitions,
        selected_exhibition_id=exhibition_id
    )

@app.route("/exhibitions")
@login_required
def view_exhibitions():
    exhibitions = Exhibition.query.filter_by(
        user_id=current_user.id
    ).order_by(Exhibition.name).all()

    return render_template(
        "exhibitions.html",
        exhibitions=exhibitions
    )

@app.route("/edit/<int:id>")
@login_required
def edit_page(id):
    exhibitions = Exhibition.query.filter_by(
        user_id=current_user.id
    ).order_by(Exhibition.name).all()

    return render_template(
        "edit.html",
        id=id,
        exhibitions=exhibitions
    )

@app.route("/admin/create-user")
@login_required
def create_user_page():
    if not current_user.is_admin:
        return redirect("/")
    return render_template("create-user.html")

# API Routes
@app.route("/api/scan", methods=["POST"])
@login_required
def scan_card():
    image = request.files.get("image")

    if not image:
        return jsonify({"error": "No image received"}), 400

    try:
        image_bytes = image.read()

        # text = extract_text_from_image(image_bytes)

        # parsed = extract_business_card_with_gemini(text)
        
        parsed = extract_business_card_with_gemini(image_bytes)
        parsed = clean_data(parsed)

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
@login_required
def save():
    data = request.get_json()

    mail_timing = data.get("mail_timing", "none")

    app = current_app._get_current_object()

    if not data:
        return {"error": "Bad request"}, 400

    if not current_user.current_exhibition_id:
        return {"error": "Please select an exhibition first"}, 400

    existing = Lead.query.filter_by(email=data.get("email"), user_id=current_user.id, exhibition_id=current_user.current_exhibition_id).first()
    if existing:
        if existing.is_deleted==False:
            return {"error": "Email already exists"}, 400
        else:
            existing.is_deleted = False
            existing.name = data.get("name")
            existing.phone = data.get("phone")
            existing.phone2 = data.get("phone2")
            existing.customer_type = data.get("customer_type")
            existing.designation = data.get("designation")
            existing.company = data.get("company")
            existing.website = data.get("website")
            existing.address = data.get("address")
            existing.remarks = data.get("remarks")

            db.session.commit()

            if mail_timing == "now":
                Thread(
                    target=send_email_background,
                    args=(existing.id, app),
                    daemon=True
                ).start()

            return {"status": "saved"}, 200
    
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
        remarks=data.get("remarks"),
        user_id=current_user.id,
        exhibition_id=current_user.current_exhibition_id,
    )

    db.session.add(lead)
    db.session.commit()

    if mail_timing == "now":
        Thread(
            target=send_email_background,
            args=(lead.id, app),
            daemon=True
        ).start()

    return {"status": "saved"}, 200

@app.route("/api/get/<int:id>")
@login_required
def get_lead(id):
    lead = Lead.query.filter_by(id=id, user_id=current_user.id).first_or_404()
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
        "exhibition_id": lead.exhibition_id
    })

@app.route("/api/update/<int:id>", methods=["PUT"])
@login_required
def update_lead(id):
    data = request.get_json()

    lead = Lead.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    lead.exhibition = data.get("exhibition")
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

@app.route("/api/add-exhibition", methods=["POST"])
@login_required
def add_exhibition():
    data = request.get_json()

    name = data.get("name", "").strip()

    if not name:
        return jsonify({"error": "Exhibition name cannot be empty."}), 400

    existing = Exhibition.query.filter_by(
        user_id=current_user.id,
        name=name
    ).first()

    if existing:
        return jsonify({"error": "An exhibition with this name already exists."}), 400

    exhibition = Exhibition(
        name=name,
        user_id=current_user.id
    )

    db.session.add(exhibition)
    db.session.commit()

    return jsonify({"success": True})

@app.route("/api/change-exhibition", methods=["POST"])
@login_required
def change_exhibition():
    exhibition_id = request.form.get("exhibition_id", type=int)

    if not exhibition_id:
        return redirect("/")

    exhibition = Exhibition.query.filter_by(
        id=exhibition_id,
        user_id=current_user.id
    ).first()

    if not exhibition:
        return redirect("/")

    current_user.current_exhibition_id = exhibition.id
    db.session.commit()

    return redirect("/")

@app.route("/api/edit-exhibition/<int:id>", methods=["POST"])
@login_required
def edit_exhibition(id):
    exhibition = Exhibition.query.filter_by(
        id=id,
        user_id=current_user.id
    ).first_or_404()

    data = request.get_json()

    new_name = data.get("name", "").strip()

    if not new_name:
        return jsonify({"error": "Name required"}), 400

    existing = Exhibition.query.filter(
        Exhibition.user_id == current_user.id,
        Exhibition.name == new_name,
        Exhibition.id != exhibition.id
    ).first()

    if existing:
        return jsonify({"error": "Exhibition already exists"}), 400

    exhibition.name = new_name
    db.session.commit()

    return jsonify({"success": True})

@app.route("/api/to-excel")
@login_required
def excel():
    exhibition_id = request.args.get('exhibition_id', type=int)

    query = Lead.query.filter_by(
        user_id=current_user.id,
        is_deleted=False
    )

    if exhibition_id:
        query = query.filter_by(exhibition_id=exhibition_id)

    leads = query.all()
    data_list = []

    for lead in leads:
        dic = {
            "exhibition":lead.exhibition.name,
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
        }
        data_list.append(dic)
    
    df = pd.DataFrame(data_list)

    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="leads.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.route("/api/delete/<int:id>", methods=["POST"])
@login_required
def delete_lead(id):
    lead = Lead.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    lead.is_deleted = True
    db.session.commit()
    return redirect("/leads")

@app.route("/api/admin/create-user", methods=["POST"])
@login_required
def create_user():
    if not current_user.is_admin:
        return {"error": "Access Denied"}, 403

    data = request.get_json()
    password = data.get("password")

    if not password:
        return {"error": "Password required"}, 400

    new_user = User()
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()

    return {"user_id": new_user.name}, 200

# Robot Safety
@app.route("/robots.txt")
def robots():
    return "User-agent: *\nDisallow: /api/\n", 200, {"Content-Type": "text/plain"}

# Run App
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=False, host = '0.0.0.0')