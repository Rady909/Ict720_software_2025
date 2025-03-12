from flask import Flask, render_template, request, jsonify
import base64
import requests
import re
from datetime import datetime

app = Flask(__name__, static_folder="static")

# API Keys
GEMINI_API_KEY = "AIzaSyAa3WEZZG_JnVmGGgFIlD9UtRaCRkKJa80"  # Replace with your Google Gemini API Key
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
GOOGLE_SEARCH_API_KEY = "AIzaSyD6yOh1Wdh0RBz50EDYUNTNKBFcvnQNmMs"  # Replace with your Google Search API Key
GOOGLE_SEARCH_ENGINE_ID = "66eb8e930e15d4758"  # Your Programmable Search Engine ID
GOOGLE_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"

def clean_text(text):
    """Clean AI response by removing unwanted characters and ensuring proper formatting."""
    if text:
        text = re.sub(r"\*\*", "", text)  # Remove markdown formatting (**bold**)
        text = re.sub(r"\*", "", text)  # Remove stray * symbols
        text = text.replace("\n", " ").strip()  # Ensure proper spacing
    return text if text else "Not available."

def analyze_image_with_gemini(image_data):
    """Send image to Gemini API to recognize the product details."""
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": "Identify the product and provide details including: Product Name, Brand, Release Date (MM/DD/YYYY format), and explain what this product is used for in one short sentence."},
                    {"inline_data": {"mime_type": "image/png", "data": image_data}}
                ]
            }
        ]
    }
    
    try:
        response = requests.post(GEMINI_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print("Error calling Gemini API:", e)
        return None

def fetch_usage_with_gemini(product_name):
    """Send a separate request to Gemini API to get product usage if missing."""
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
        response = requests.post(GEMINI_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        return clean_text(result["candidates"][0]["content"]["parts"][0]["text"])
    except requests.exceptions.RequestException as e:
        print("Error fetching product usage:", e)
        return "Not available."

def search_product_price(product_name):
    """Fetch the latest product price using Google Programmable Search Engine API, only from Shopee & Lazada Thailand."""
    params = {
        "q": f"{product_name} price site:shopee.co.th OR site:lazada.co.th",
        "cx": GOOGLE_SEARCH_ENGINE_ID,
        "key": GOOGLE_SEARCH_API_KEY,  # API Key Added Here
        "num": 5
    }
    try:
        response = requests.get(GOOGLE_SEARCH_URL, params=params)
        response.raise_for_status()
        results = response.json()

        price_results = []
        for item in results.get("items", []):
            if "price" in item["title"].lower() or "฿" in item["snippet"]:
                price_results.append(f"<b>{item['title']}</b>: {item['snippet']}<br><a href='{item['link']}' target='_blank'>View Price</a>")

        return "<br>".join(price_results) if price_results else "Price not available."

    except requests.exceptions.RequestException as e:
        print("Error fetching product price:", e)
        return "Error retrieving price data."

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scan', methods=['POST'])
def scan_product():
    """Handles product detection request."""
    data = request.json
    image_data = data['image'].split(',')[1]  

    # Step 1: Recognize product using Gemini API
    response = analyze_image_with_gemini(image_data)

    if not response:
        return jsonify({"message": "❌ Error: Could not get a response from Gemini API. Try again."})

    try:
        detected_product = response["candidates"][0]["content"]["parts"][0]["text"]

        # Extract Product Name
        product_name_match = re.search(r'Product Name:\s*(.*?)\n', detected_product, re.DOTALL)
        product_name = clean_text(product_name_match.group(1)) if product_name_match else "Unknown"

        # Extract Brand
        brand_match = re.search(r'Brand:\s*(.*?)\n', detected_product, re.DOTALL)
        brand = clean_text(brand_match.group(1)) if brand_match else "Unknown"

        # Extract First Occurrence of Release Date & Convert to MM/DD/YYYY
        release_date_match = re.search(r'Release Date:\s*(.*?)\n', detected_product, re.DOTALL)
        if release_date_match:
            raw_date = release_date_match.group(1).strip()
            try:
                formatted_date = datetime.strptime(raw_date, "%B %d, %Y").strftime("%m/%d/%Y")  
            except ValueError:
                formatted_date = clean_text(raw_date)  # Ensure clean formatting
        else:
            formatted_date = "Not available."

        # Extract What the Product is Used For
        usage_match = re.search(r'Used for:\s*(.*?)\n', detected_product, re.DOTALL)
        usage = clean_text(usage_match.group(1)) if usage_match else "Not available."

        # If usage is still missing, request it separately from Gemini
        if usage == "Not available.":
            usage = fetch_usage_with_gemini(product_name)

        # Step 2: Search for the real price using Google Programmable Search API (Shopee & Lazada only)
        product_price = search_product_price(product_name)

        # Step 3: Format final output
        formatted_result = f"""
        <b>Product Name:</b> {product_name}<br>
        <b>Brand:</b> {brand}<br>
        <b>Release Date:</b> {formatted_date}<br>
        <b>What is it used for?</b> {usage}<br>
        <b>Price Comparison (Shopee & Lazada):</b><br> {product_price}
        """

    except Exception as e:
        print("Error extracting product details:", e)
        formatted_result = "❌ Error: Could not extract product details. Try again."

    return jsonify({"message": formatted_result})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=2502, debug=True)

