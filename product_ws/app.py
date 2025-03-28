from flask import Flask, render_template, request, jsonify
import base64
import requests
import re
import sqlite3
from io import BytesIO
import os
from PIL import Image
from datetime import datetime
from bs4 import BeautifulSoup

app = Flask(__name__, static_folder="static")

# --- Constants ---
IMAGE_SIZE = (224, 224)
DATA_DIR = "image_data_serpapi"  # Use the correct data directory
EXCHANGE_RATE = 35  # THB to USD

# --- Database Setup ---
DB_NAME = "product_scans.db"

def create_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT,
            brand TEXT,
            brand_details TEXT,
            release_date TEXT,
            usage TEXT,
            price TEXT,
            scan_time TEXT
        )
    ''')
    conn.commit()
    conn.close()

create_database()

# --- API Keys and URLs (HARDCODED - FOR TESTING ONLY) ---
GOOGLE_SEARCH_API_KEY = "----"  # YOUR GOOGLE SEARCH KEY
GOOGLE_SEARCH_ENGINE_ID = "---"  # YOUR GOOGLE SEARCH ENGINE ID
GOOGLE_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"
GEMINI_API_KEY = "A---" # YOUR GEMINI API KEY
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

# --- Utility Functions ---

def clean_text(text):
    """Cleans text by removing unwanted characters."""
    if text:
        text = re.sub(r"[\*\n]+", "", text)
        text = text.strip()
        return text
    return "Not available."

def extract_price(text):
    """Extracts a numeric price value from a string, handling commas."""
    match = re.search(r'฿([\d,\.]+)', text)
    if match:
        try:
            return float(match.group(1).replace(",", ""))
        except ValueError:
            return None
    return None

def search_shopee_lazada_price(product_name, brand=None):
    """Searches Shopee and Lazada, returning URLs."""
    lazada_url = f"https://www.lazada.co.th/tag/{product_name}/?spm=a2o4m.homepage.search.d_go&q={product_name}&catalog_redirect_tag=true"
    shopee_url = f"https://shopee.co.th/search?keyword={product_name}"
    return lazada_url, shopee_url

def search_generic_price(product_name):
    """Searches for a generic product's price (fallback)."""
    query = f"{product_name} price"
    params = {
        "q": query,
        "cx": GOOGLE_SEARCH_ENGINE_ID,
        "key": GOOGLE_SEARCH_API_KEY,
        "num": 5
    }
    try:
        response = requests.get(GOOGLE_SEARCH_URL, params=params)
        response.raise_for_status()
        results = response.json()

        price_results = []
        for item in results.get("items", []):
            if "price" in item["title"].lower() or any(
                    currency in item["snippet"] for currency in ["฿", "$", "€", "£"]):
                price_results.append(
                    f"<a href='{item['link']}' target='_blank'>{item['title']}</a>: {item['snippet']}")
        return "<br>".join(price_results) if price_results else ""
    except requests.exceptions.RequestException as e:
        print(f"Error fetching generic price: {e}")
        return "Error retrieving price data."

def analyze_image_with_gemini(image_data):
    """Sends image to Gemini API for analysis (non-phone products)."""
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": "Identify the product and provide details including: Product Name, Brand, Release Date of product and company, Brand Details brand owner, and explain what this product is used for in short sentence."},
                    {"inline_data": {"mime_type": "image/jpeg", "data": image_data}}
                ]
            }
        ]
    }
    try:
        # Pass API key as a parameter
        response = requests.post(GEMINI_API_URL, params={"key": GEMINI_API_KEY},
                                 json=payload, headers=headers)
        response.raise_for_status()  # This will raise an exception for 4xx and 5xx errors
        return response.json()
    except requests.exceptions.RequestException as e:
        print("Error calling Gemini API:", e)
        return None

def fetch_usage_with_gemini(product_name):
    """Gets product usage from Gemini (fallback)."""
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": f"In one short sentence, explain what {product_name} is used for."}
                ]
            }
        ]
    }
    try:
        # Pass API key as a parameter
        response = requests.post(GEMINI_API_URL, params={"key": GEMINI_API_KEY},
                                 json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        return clean_text(result["candidates"][0]["content"]["parts"][0]["text"])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching product usage:", e)
        return "Not available."

def get_gemini_price(product_name):
    """
    Retrieves the price of a product from Gemini, given the product name.
    """
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": f"What is the price of {product_name} in Thailand, in THB?"}
                ]
            }
        ]
    }
    try:
        response = requests.post(GEMINI_API_URL, params={"key": GEMINI_API_KEY},
                                 json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        price_text = clean_text(
            result["candidates"][0]["content"]["parts"][0]["text"])

        # Extract price
        price_match = re.search(r'([\d,\.]+)\s*THB', price_text, re.IGNORECASE)
        if price_match:
            price_value = price_match.group(1).replace(",", "")
            return f"Estimate Price (Approximate): ฿{price_value}"
        else:
            return ""

    except requests.exceptions.RequestException as e:
        print(f"Error fetching price from Gemini: {e}")
        return "Error retrieving price from Gemini."
    except Exception as e:
        print(f"Error processing Gemini response: {e}")
        return "Error processing Gemini's price response."

# --- Flask Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scan', methods=['POST'])
def scan_product():
    """Handles the image upload and product information retrieval."""
    data = request.get_json()
    if not data or 'image' not in data:
        return jsonify({"message": "Error: No image data received."}), 400

    image_data = base64.b64decode(data['image'].split(',')[1])

    response = analyze_image_with_gemini(base64.b64encode(image_data).decode('utf-8'))
    if not response:
        return jsonify(
            {"message": "Error: Could not get a response from Gemini API. Try again."}), 500

    try:
        detected_product = response["candidates"][0]["content"]["parts"][0]["text"]
        product_name_match = re.search(r'Product Name:\s*(.*?)\n', detected_product,
                                       re.DOTALL)
        product_name = clean_text(
            product_name_match.group(1)) if product_name_match else "Unknown"

        brand_match = re.search(r'Brand:\s*(.*?)\n', detected_product, re.DOTALL)
        brand = clean_text(brand_match.group(1)) if brand_match else "Unknown"

        brand_details_match = re.search(r'Brand Details:\s*(.*?)\n', detected_product,
                                           re.DOTALL)
        brand_details = clean_text(
            brand_details_match.group(1)) if brand_details_match else "Not available."

        release_date_match = re.search(r'Release Date:\s*(.*?)\n', detected_product,
                                       re.DOTALL)

        if release_date_match:
            raw_date = release_date_match.group(1).strip()
            try:
                # Attempt to parse the date
                formatted_date = datetime.strptime(raw_date,
                                                   "%B %d, %Y").strftime("%m/%d/%Y")
            except ValueError:
                # If parsing fails, just clean the text
                formatted_date = clean_text(raw_date)
        else:
            formatted_date = "Not available."
        usage_match = re.search(r'Used for:\s*(.*?)\n', detected_product + '\n',
                               re.DOTALL)
        usage = clean_text(usage_match.group(1)) if usage_match else "Not available."

        if usage == "Not available.":
            usage = fetch_usage_with_gemini(product_name)

        price_info = ""
        lazada_url, shopee_url = search_shopee_lazada_price(product_name)
        price_info += f"<a href='{lazada_url}' target='_blank'>Lazada - {product_name}</a>"
        price_info += f"<br><a href='{shopee_url}' target='_blank'>Shopee - {product_name}</a>"
        gemini_price = get_gemini_price(product_name)
        price_info += "<br>" + gemini_price

        formatted_result = f"""
            <b>Product Name:</b> {product_name}<br>
            <b>Brand:</b> {brand}<br>
            <b>Brand Details:</b> {brand_details}<br>
            <b>Release Date:</b> {formatted_date}<br>
            <b>What is it used for?</b> {usage}<br>
            <b>Price Information:</b><br>{price_info}
            """
        return jsonify({"message": formatted_result})

    except Exception as e:
        print(f"Error extracting details (Gemini): {e}")
        return jsonify({"message": "Error: Could not extract product details."}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=2502, debug=True,
            use_reloader=False)  # Disable the reloader
