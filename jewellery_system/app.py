from flask import Flask, render_template, request, redirect, session, send_file, send_from_directory
from tinydb import TinyDB, Query
import hashlib
import random
import string
import os
from datetime import datetime
import qrcode
from reportlab.pdfgen import canvas
import smtplib
from email.mime.text import MIMEText
# -------------------------
# LANGUAGE TEXT
# -------------------------

translations = {

"en":{
"dashboard":"Customer Dashboard",
"requests":"Your Jewellery Requests",
"tracking":"Tracking",
"jewellery":"Jewellery",
"status":"Status"
},

"hi":{
"dashboard":"ग्राहक डैशबोर्ड",
"requests":"आपके आभूषण अनुरोध",
"tracking":"ट्रैकिंग",
"jewellery":"आभूषण",
"status":"स्थिति"
},

"te":{
"dashboard":"కస్టమర్ డాష్‌బోర్డ్",
"requests":"మీ ఆభరణాల అభ్యర్థనలు",
"tracking":"ట్రాకింగ్",
"jewellery":"ఆభరణం",
"status":"స్థితి"
}

}

app = Flask(__name__)
app.secret_key = "jewellery_secret_key"

# -------------------------
# EMAIL CONFIG
# -------------------------

EMAIL_ADDRESS = "tejareddykatta1@gmail.com"
EMAIL_PASSWORD = "gytboxjsgsgxetwp"

# -------------------------
# DATABASE
# -------------------------

users_db = TinyDB("database/users.json")
jewellery_db = TinyDB("database/jewellery.json")

User = Query()
Jewellery = Query()

# -------------------------
# FOLDERS
# -------------------------

IMAGE_FOLDER = "images"
FILE_FOLDER = "uploads"
QR_FOLDER = "qr"

os.makedirs(IMAGE_FOLDER, exist_ok=True)
os.makedirs(FILE_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER, exist_ok=True)

# -------------------------
# HILL CIPHER
# -------------------------

alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
key_matrix = [[3,3],[2,5]]
inverse_matrix = [[15,17],[20,9]]

def process_text(text):
    text = text.upper().replace(" ","")
    if len(text) % 2 != 0:
        text += "X"
    return text

def hill_encrypt(text):
    text = process_text(text)
    result = ""
    for i in range(0,len(text),2):
        pair = text[i:i+2]
        p1 = alphabet.index(pair[0])
        p2 = alphabet.index(pair[1])
        c1 = (key_matrix[0][0]*p1 + key_matrix[0][1]*p2) % 26
        c2 = (key_matrix[1][0]*p1 + key_matrix[1][1]*p2) % 26
        result += alphabet[c1] + alphabet[c2]
    return result

def hill_decrypt(text):
    result = ""
    for i in range(0,len(text),2):
        pair = text[i:i+2]
        p1 = alphabet.index(pair[0])
        p2 = alphabet.index(pair[1])
        d1 = (inverse_matrix[0][0]*p1 + inverse_matrix[0][1]*p2) % 26
        d2 = (inverse_matrix[1][0]*p1 + inverse_matrix[1][1]*p2) % 26
        result += alphabet[d1] + alphabet[d2]
    return result

# -------------------------
# PASSWORD HASH
# -------------------------

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# -------------------------
# GENERATE TRACKING ID
# -------------------------

def generate_tracking():
    return "JWL-" + ''.join(random.choices(string.digits,k=6))

# -------------------------
# GENERATE OTP
# -------------------------

def generate_otp():
    return str(random.randint(100000,999999))

# -------------------------
# SEND OTP EMAIL
# -------------------------

def send_otp_email(receiver_email, otp):

    try:

        subject = "Jewellery System OTP Verification"

        body = f"""
Your OTP for Jewellery System login is:

OTP: {otp}

Do not share this code with anyone.
"""

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = receiver_email

        server = smtplib.SMTP("smtp.gmail.com", 587)

        server.starttls()

        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

        server.sendmail(EMAIL_ADDRESS, receiver_email, msg.as_string())

        server.quit()

        print("OTP email sent successfully")

    except Exception as e:

        print("Email sending failed")
        print(e)
        print("Fallback OTP:", otp)
# -------------------------
# GENERATE QR
# -------------------------

def generate_qr(tracking):
    url = f"http://127.0.0.1:5000/track/{tracking}"
    img = qrcode.make(url)
    path = f"{QR_FOLDER}/{tracking}.png"
    img.save(path)
    return path

# -------------------------
# GENERATE PDF RECEIPT
# -------------------------

def generate_pdf(tracking,title,date):
    filename = f"receipt_{tracking}.pdf"
    c = canvas.Canvas(filename)

    c.setFont("Helvetica-Bold",16)
    c.drawString(200,750,"Jewellery Submission Receipt")

    c.setFont("Helvetica",12)
    c.drawString(100,700,f"Tracking ID : {tracking}")
    c.drawString(100,670,f"Jewellery   : {title}")
    c.drawString(100,640,f"Date        : {date}")
    c.drawString(100,610,"Status      : Submitted")

    c.save()
    return filename

# -------------------------
# DEFAULT USERS
# -------------------------

if len(users_db) == 0:
    users_db.insert({
        "username":"admin",
        "email":"admin@gmail.com",
        "password":hash_password("admin123"),
        "role":"admin"
    })

    users_db.insert({
        "username":"owner",
        "email":"owner@gmail.com",
        "password":hash_password("owner123"),
        "role":"owner"
    })

# -------------------------
# LOGIN
# -------------------------

@app.route("/", methods=["GET","POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        hashed_password = hash_password(password)

        user = users_db.get((User.username == username) & (User.password == hashed_password))

        if user:

            otp = generate_otp()

            session["otp"] = otp
            session["temp_user"] = username
            session["lang"] = "en"
            session["role"] = user["role"]

            email = user.get("email")

            if email:
                send_otp_email(email, otp)
            else:
                print("OTP:", otp)

            return redirect("/verify")

    return render_template("login.html")

# -------------------------
# VERIFY OTP
# -------------------------

@app.route("/verify",methods=["GET","POST"])
def verify():

    if request.method == "POST":

        if request.form["otp"] == session["otp"]:

            session["user"] = session["temp_user"]

            if session["role"] == "admin":
                return redirect("/admin")

            elif session["role"] == "owner":
                return redirect("/owner")

            else:
                return redirect("/customer")

    return render_template("otp.html")

# -------------------------
# REGISTER
# -------------------------

@app.route("/register",methods=["GET","POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        email = request.form["email"]
        password = hash_password(request.form["password"])

        users_db.insert({
            "username":username,
            "email":email,
            "password":password,
            "role":"customer"
        })

        return redirect("/")

    return render_template("register.html")

# -------------------------
# CUSTOMER DASHBOARD
# -------------------------

@app.route("/customer")
def customer():

    data = jewellery_db.search(Jewellery.customer == session["user"])

    lang = session.get("lang","en")

    return render_template(
        "customer_dashboard.html",
        data=data,
        t=translations[lang]
    )

# -------------------------
# SUBMIT JEWELLERY
# -------------------------

@app.route("/submit",methods=["GET","POST"])
def submit():

    if request.method == "POST":

        title = request.form["title"]
        description = request.form["description"]

        encrypted_description = hill_encrypt(description)

        image = request.files["image"]
        file = request.files["file"]

        image_path = os.path.join(IMAGE_FOLDER,image.filename)
        file_path = os.path.join(FILE_FOLDER,file.filename)

        image.save(image_path)
        file.save(file_path)

        tracking = generate_tracking()

        qr_path = generate_qr(tracking)

        jewellery_db.insert({
            "tracking":tracking,
            "customer":session["user"],
            "title":title,
            "description":encrypted_description,
            "image":image.filename,
            "file":file_path,
            "qr":qr_path,
            "status":"Submitted",
            "date":str(datetime.now().date())
        })

        pdf = generate_pdf(tracking,title,datetime.now().date())

        return send_file(pdf,as_attachment=True)

    return render_template("submit_jewellery.html")

# -------------------------
# ADMIN DASHBOARD
# -------------------------

@app.route("/admin")
def admin():

    tracking = request.args.get("tracking")
    customer = request.args.get("customer")
    status = request.args.get("status")

    data = jewellery_db.all()

    if tracking:
        data = [i for i in data if tracking.lower() in i["tracking"].lower()]

    if customer:
        data = [i for i in data if customer.lower() in i["customer"].lower()]

    if status:
        data = [i for i in data if i["status"] == status]

    for item in data:
        item["description"] = hill_decrypt(item["description"])

    total = len(data)
    submitted = len([i for i in data if i["status"]=="Submitted"])
    completed = len([i for i in data if i["status"]=="Completed"])
    resolved = len([i for i in data if i["status"]=="Resolved"])

    stats = {
        "total":total,
        "submitted":submitted,
        "completed":completed,
        "resolved":resolved
    }

    return render_template("admin_dashboard.html",data=data,stats=stats)
# -------------------------
# ASSIGN OWNER
# -------------------------

@app.route("/assign/<tracking>", methods=["POST"])
def assign_owner(tracking):

    owner = request.form["owner"]

    jewellery_db.update(
        {"owner":owner,"status":"Assigned"},
        Jewellery.tracking == tracking
    )

    return redirect("/admin")

# -------------------------
# OWNER DASHBOARD
# -------------------------

@app.route("/owner")
def owner():

    data = jewellery_db.search(Jewellery.owner == session["user"])

    for item in data:
        item["description"] = hill_decrypt(item["description"])

    return render_template("owner_dashboard.html",data=data)

# -------------------------
# OWNER UPDATE STATUS
# -------------------------

@app.route("/update_status/<tracking>", methods=["POST"])
def update_status(tracking):

    status = request.form["status"]

    jewellery_db.update(
        {"status":status},
        Jewellery.tracking == tracking
    )

    return redirect("/owner")

# -------------------------
# QR SCANNER PAGE
# -------------------------

@app.route("/scan")
def scan():
    return render_template("scan.html")

# -------------------------
# TRACK PAGE
# -------------------------

@app.route("/track", methods=["GET","POST"])
@app.route("/track/<tracking>", methods=["GET","POST"])
def track(tracking=None):

    item = None

    if request.method == "POST":
        tracking = request.form["tracking"]

    if tracking:
        item = jewellery_db.get(Jewellery.tracking == tracking)

        if item:
            item["description"] = hill_decrypt(item["description"])

    return render_template("track.html", item=item)

# -------------------------
# SERVE IMAGES
# -------------------------

@app.route("/images/<filename>")
def serve_image(filename):
    return send_from_directory("images", filename)
    # -------------------------
# CHANGE LANGUAGE
# -------------------------

@app.route("/language/<lang>")
def change_language(lang):

    session["lang"] = lang

    return redirect(request.referrer or "/")

# -------------------------
# LOGOUT
# -------------------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# -------------------------

if __name__ == "__main__":
    app.run(debug=True)