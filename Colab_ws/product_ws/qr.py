import subprocess
import requests
import time
import qrcode
from PIL import Image, ImageDraw, ImageFont

def start_ngrok():
    """Start Ngrok in the background if it's not already running."""
    print("Starting Ngrok on port 5000...")
    subprocess.Popen(["ngrok", "http", "5000"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)  # Wait for Ngrok to initialize

def get_ngrok_url():
    """Fetch the public URL from Ngrok's API."""
    try:
        response = requests.get("http://127.0.0.1:4040/api/tunnels")
        data = response.json()
        return data["tunnels"][0]["public_url"]
    except Exception as e:
        print("Error fetching Ngrok URL:", e)
        return None

def generate_qr(url):
    """Generate a QR code with a 'ProdScan' background."""
    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    # Create the QR code
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")

    # Create background with text
    bg = Image.new("RGBA", (qr_img.size[0], qr_img.size[1] + 50), "white")
    bg.paste(qr_img, (0, 50))  # Shift QR down to make space for text

    # Add text at the top
    draw = ImageDraw.Draw(bg)
    font_size = 30
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    text = "ProdScan"
    
    # 🔹 Fix: Use `textbbox()` instead of `textsize()`
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width, text_height = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
    
    text_x = (bg.width - text_width) // 2
    text_y = 10
    draw.text((text_x, text_y), text, font=font, fill="black")

    # Save and display QR code
    bg.save("ngrok_qr.png")
    print("✅ QR Code saved as 'ngrok_qr.png'")
    bg.show()

if __name__ == "__main__":
    # Start Ngrok if not already running
    start_ngrok()

    # Get Ngrok public URL
    ngrok_url = get_ngrok_url()
    if ngrok_url:
        print(f"Ngrok Public URL: {ngrok_url}")
        generate_qr(ngrok_url)
    else:
        print("Failed to retrieve Ngrok URL. Make sure Ngrok is running.")

