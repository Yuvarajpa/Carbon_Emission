from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from twilio.rest import Client
from dotenv import load_dotenv
import requests
import pdfkit
import pandas as pd
import os
import google.generativeai as genai
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

app.secret_key = "your_secret_key"

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)

# Create Database
with app.app_context():
    db.create_all()

    # Load CSV Data into a DataFrame

# Configure wkhtmltopdf

# Function to generate emission reduction suggestions

# Home Page
@app.route('/')
def home():
    return render_template('home.html')

# Register Page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')

        if not username or not password or not role:
            flash("All fields are required!", "danger")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        if User.query.filter_by(username=username).first():
            flash("Username already exists!", "danger")
            return redirect(url_for('register'))

        new_user = User(username=username, password=hashed_password, role=role)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

# Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role
            session['username'] = user.username
            flash("Login successful!", "success")
            return redirect(url_for('map_page'))  # Redirect to Map after login
        else:
            flash("Invalid credentials!", "danger")

    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!", "info")
    return redirect(url_for('home'))

# Protected Pages
@app.route('/map')
def map_page():
    if 'user_id' not in session:
        flash("Please log in first!", "danger")
        return redirect(url_for('login'))
    return render_template('map.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("Please log in first!", "danger")
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/alerts')
def alerts():
    if 'user_id' not in session:
        flash("Please log in first!", "danger")
        return redirect(url_for('login'))
    
    if session.get('role') != 'official':  # Only officials can access
        flash("Access Denied! This page is for officials only.", "warning")
        return redirect(url_for('home'))  # Redirect public users to home

    return render_template('alerts.html')

    return render_template('alerts.html')
@app.route('/prediction')
def prediction():
    if 'user_id' not in session:
        flash("Please log in first!", "danger")
        return redirect(url_for('login'))
    return render_template('prediction.html')

@app.route('/report')
def report():
    if 'user_id' not in session:
        flash("Please log in first!", "danger")
        return redirect(url_for('login'))
    
    if session.get('role') != 'official':  # Only officials can access
        flash("Access Denied! This page is for officials only.", "warning")
        return redirect(url_for('home'))  # Redirect public users to home

    df = pd.read_csv('coal_emissions.csv')  # Adjust path as necessary
    mines = df["Mine Name"].tolist()
    return render_template('report.html', mines=mines)

# ====== Alert System ======
DEMO_MODE = True  # Change to False for real API data
load_dotenv()
# Twilio Credentials (Replace with actual credentials)
TWILIO_SID = os.environ.get("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")
RECIPIENT_PHONE_NUMBER = os.environ.get("RECIPIENT_PHONE_NUMBER")


# Emission Thresholds
CO2_THRESHOLD = 40000
CH4_THRESHOLD = 5000
AQI_THRESHOLD = 600

# Function to fetch emission data
def fetch_emission_data():
    if DEMO_MODE:
        return {"CO2": 50000, "CH4": 7000, "AQI": 720, "Dust": 120}
    else:
        API_URL = "https://air-quality-api.open-meteo.com/v1/air-quality?latitude=23.7955&longitude=86.4146&current=carbon_monoxide,methane,ozone,dust"
        try:
            response = requests.get(API_URL)
            response.raise_for_status()
            data = response.json()
            return {
                "CO2": data["current"].get("carbon_monoxide", 0),
                "CH4": data["current"].get("methane", 0),
                "AQI": data["current"].get("ozone", 0),
                "Dust": data["current"].get("dust", 0)
            }
        except requests.exceptions.RequestException:
            return None

# Function to send SMS alert
def send_sms_alert(message):
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
        sms = client.messages.create(body=message, from_=TWILIO_PHONE_NUMBER, to=RECIPIENT_PHONE_NUMBER)
        return f"SMS Sent! Message SID: {sms.sid}"
    except Exception as e:
        return f"SMS Failed: {e}"

@app.route('/get_data', methods=['GET'])
def get_data():
    data = fetch_emission_data()
    if data:
        return jsonify({"status": "success", "message": "Data fetched successfully!", "data": data})
    return jsonify({"status": "error", "message": "Failed to fetch data"})

@app.route('/toggle_demo', methods=['POST'])
def toggle_demo():
    global DEMO_MODE
    DEMO_MODE = not DEMO_MODE
    return jsonify({"status": "success", "demo_mode": DEMO_MODE})

@app.route('/check_emissions', methods=['GET'])
def check_emissions():
    data = fetch_emission_data()
    if not data:
        return jsonify({"status": "error", "message": "Failed to fetch data"})

    alerts = []
    if data["CO2"] > CO2_THRESHOLD:
        alerts.append(f"/n⚠ CO₂ level is {data['CO2']} µg/m³, exceeding {CO2_THRESHOLD}!/n")
    if data["CH4"] > CH4_THRESHOLD:
        alerts.append(f"⚠ CH₄ level is {data['CH4']} µg/m³, exceeding {CH4_THRESHOLD}!/n")
    if data["AQI"] > AQI_THRESHOLD:
        alerts.append(f"⚠ AQI level is {data['AQI']}, exceeding {AQI_THRESHOLD}!/n ⚠ Alert: The emission levels near your location have exceeded safe limits!/n" f"⚠ High pollution levels detected. Please take necessary precautions and move to a safer location if possible./n") 
    if alerts:
        alert_message = "\n".join(alerts)
        sms_status = send_sms_alert(alert_message)
        return jsonify({"status": "alert", "message": alert_message, "sms_status": sms_status})
    return jsonify({"status": "safe", "message": "✅ Emissions are within safe limits."})




PDFKIT_CONFIG = pdfkit.configuration(wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")

# Load CSV data into a DataFrame
CSV_FILE = "coal_emissions.csv"
df = pd.read_csv(CSV_FILE)

# Function to generate emission reduction suggestions
def get_emission_suggestions(co2, ch4, so2):
    suggestions = []
    
    # CO₂ Reduction Strategies
    if co2 > 25000:
        suggestions.append("Implement Carbon Capture and Storage (CCS) technology.")
        suggestions.append("Optimize energy efficiency in coal processing.")
    elif co2 > 15000:
        suggestions.append("Switch to cleaner coal technologies like gasification.")
    
    # CH₄ Reduction Strategies
    if ch4 > 500:
        suggestions.append("Improve methane drainage and recovery systems.")
        suggestions.append("Use ventilation air methane (VAM) oxidation technology.")
    elif ch4 > 300:
        suggestions.append("Enhance underground mine ventilation to reduce methane buildup.")

    # SO₂ Reduction Strategies
    if so2 > 800:
        suggestions.append("Install flue gas desulfurization (FGD) units.")
        suggestions.append("Use low-sulfur coal and cleaner combustion methods.")
    elif so2 > 500:
        suggestions.append("Adopt limestone injection to reduce sulfur emissions.")

    return suggestions



@app.route('/download_report', methods=['GET'])
def download_report():
    mine_name = request.args.get('mine')

    # Fetch data for the selected mine
    mine_data = df[df["Mine Name"] == mine_name].iloc[0]

    # Extract emission details
    co2_emission = mine_data["CO2 Emission (Metric Tons)"]
    ch4_emission = mine_data["CH4 Emission (Metric Tons)"]
    so2_emission = mine_data["SO2 Emission (Metric Tons)"]
    year = mine_data["Year"]

    # Generate emission control suggestions
    suggestions = get_emission_suggestions(co2_emission, ch4_emission, so2_emission)
    suggestions_html = "<ul>" + "".join(f"<li>{s}</li>" for s in suggestions) + "</ul>" if suggestions else "<p>No suggestions available.</p>"

    # Generate dynamic report
    report_html = f"""
    <html>
    <head><title>Report for {mine_name}</title></head>
    <body>
        <h1>Carbon Emission Report for {mine_name}</h1>
        <p><strong>Mine Name:</strong> {mine_name}</p>
        <p><strong>CO2 Emission:</strong> {co2_emission} Metric Tons</p>
        <p><strong>CH4 Emission:</strong> {ch4_emission} Metric Tons</p>
        <p><strong>SO2 Emission:</strong> {so2_emission} Metric Tons</p>
        <p><strong>Year:</strong> {year}</p>
        
        <h2>Emission Control Suggestions</h2>
        {suggestions_html}
    </body>
    </html>
    """

    # Save PDF to Downloads folder
    downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")
    safe_mine_name = mine_name.replace(" ", "_")
    pdf_path = os.path.join(downloads_folder, f"{safe_mine_name}_report.pdf")

    # Convert HTML to PDF
    pdfkit.from_string(report_html, pdf_path, configuration=PDFKIT_CONFIG)

    # Send the file for download
    return send_file(pdf_path, as_attachment=True, download_name=f"{safe_mine_name}_report.pdf")



genai.configure(api_key="AIzaSyB5AYQImU4KyhI7hygbuX8FxcKBOuAE4tE")
model = genai.GenerativeModel("gemini-1.5-pro")

# ✅ Custom knowledge base
CUSTOM_KNOWLEDGE = """
You are an AI trained with the latest data on carbon emissions in coal mines across India.
Key facts:
-  we are team of Zero emission ,I am Yuvaraj  and nandhagopalan from the Computer Science and Engineering (CSE) department and nandhagopan  . I trained you with the latest data on carbon emissions in coal mines across India.
- Our team name is Zero Emission.
-you ar suoer fast in giving reply ay peak speed
- The major greenhouse gases from coal mines are CO₂, CH₄ (Methane), and NOx.
- The Indian government regulates emissions using CPCB guidelines.
- The highest-emitting coal mines are in Jharkhand, Chhattisgarh, and Odisha.
- If the user asks about regulations, refer to CPCB and MoEFCC guidelines.
- Provide data within 2-3 lines, unless the user asks for more details.
- You are mainly focusing on the carbon emission data of coal mines.
- you are a well known expert in coal mines realeated datas like emissions, how to control
- you are partcualry and mainy focusing on the coal mines data and emission over the mines
-you can also handle multi language questions
-you can miscorrect the question if user enters wrongly
- mine raleted and emisisons like co2 co4 how to reduce 

- about this project The **Coal Mine Emission Tracker** is a real-time monitoring system that tracks CO₂, CH₄, AQI, and dust emissions from coal mines across India. It features **live data visualization, AI-based emission prediction, an interactive map, and an automated alert system** to ensure environmental safety. The platform provides **threshold-based SMS alerts, an AI chatbot for assistance, and downloadable reports** for government officials. This system enhances transparency, aids decision-making, and helps mitigate mining-related pollution. 
"""

# ✅ Route for AI Chatbot UI
@app.route('/AI_Chatbot')
def ai_chatbot():
    if 'user_id' not in session:
        flash("Please log in first!", "danger")
        return redirect(url_for('login'))
    return render_template('chat.html')

# ✅ API Endpoint for Chatbot Interaction
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()  # Get JSON request data
        if not data or "query" not in data:
            return jsonify({"response": "Invalid request! JSON data with 'query' required."}), 400

        user_query = data["query"].strip()

        if not user_query:
            return jsonify({"response": "Please enter a valid query."}), 400

        # Combine user query with custom knowledge
        full_prompt = CUSTOM_KNOWLEDGE + "\nUser Query: " + user_query

        # Generate a response using Gemini AI
        response = model.generate_content(full_prompt)

        return jsonify({"response": response.text.strip()})

    except Exception as e:
        print("Server Error:", str(e))  # Debugging
        return jsonify({"response": "Error processing request!", "error": str(e)}), 500

# ✅ Dummy Login Route for Authentication

# Run Flask App
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=10000)
