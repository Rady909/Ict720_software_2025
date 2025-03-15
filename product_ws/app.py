
from flask import Flask, render_template, request, jsonify
import base64
import requests

app = Flask(__name__)

# Google Gemini API Configuration
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
API_KEY = "---"  # 🔹 Replace with your actual API key

def analyze_image_with_gemini(image_data):
    """Send the image to Google Gemini API for product detection."""
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": "Identify the product and provide details like brand, release date, and key features."},
                    {"inline_data": {"mime_type": "image/png", "data": image_data}}
                ]
            }
        ]
    }

    response = requests.post(f"{GEMINI_API_URL}?key={API_KEY}", json=payload, headers=headers)
    return response.json()

@app.route('/')
def index():
    """Render the web interface."""
    return render_template('index.html')

@app.route('/scan', methods=['POST'])
def scan_product():
    """Handles product detection request."""
    data = request.json
    image_data = data['image'].split(',')[1]  # Extract Base64 image data

    # Call Google Gemini API for product recognition
    response = analyze_image_with_gemini(image_data)

    # Extract detected product details from response
    try:
        detected_product = response["candidates"][0]["content"]["parts"][0]["text"]
    except KeyError:
        detected_product = "Product not recognized. Try again."

    return jsonify({"message": detected_product})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

