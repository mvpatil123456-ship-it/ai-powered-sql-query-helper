import os
import mysql.connector
from dotenv import load_dotenv
import google.generativeai as genai

# Load API key
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-3.6-flash")

# Connect to MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="mansipatil123",
    database="sales_db"
)

cursor = db.cursor()

# Test: fetch all customers to confirm connection works
cursor.execute("SELECT * FROM customers")
rows = cursor.fetchall()
for row in rows:
    print(row)