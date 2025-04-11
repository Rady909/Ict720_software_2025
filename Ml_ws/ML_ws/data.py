import requests
import os
import json
import uuid
import time
import random
import re  # Import the regular expression module
from urllib.parse import urlparse, unquote
from bs4 import BeautifulSoup  # For HTML parsing
from serpapi import GoogleSearch

# --- Constants ---
SERPAPI_KEY = ""  # Replace with your SerpApi key!
DATA_DIR = "image_data_serpapi"  # Use a different directory for SerpAPI data
MAX_IMAGES_PER_MODEL = 10
MIN_IMAGES_PER_MODEL = 5
GOOGLE_SEARCH_API_KEY = ""  # Replace!
GOOGLE_SEARCH_ENGINE_ID = ""  # Replace!
GOOGLE_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"

# --- Phone Models ---
#  We no longer need the "sites" key since SerpAPI searches across the web.
PHONE_MODELS = [
    # Apple
    {"brand": "Apple", "model": "iPhone 15 Pro Max"},
    {"brand": "Apple", "model": "iPhone 15 Pro"},
    {"brand": "Apple", "model": "iPhone 15"},
    {"brand": "Apple", "model": "iPhone 14"},
    {"brand": "Apple", "model": "iPhone SE (2022)"},
    # Samsung
    {"brand": "Samsung", "model": "Galaxy S24 Ultra"},
    {"brand": "Samsung", "model": "Galaxy S23 Ultra"},
    {"brand": "Samsung", "model": "Galaxy Z Fold 5"},
    {"brand": "Samsung", "model": "Galaxy A54"},
    {"brand": "Samsung", "model": "Galaxy A14"},
    # Xiaomi
    {"brand": "Xiaomi", "model": "14 Pro"},
    {"brand": "Xiaomi", "model": "13 Ultra"},
    {"brand": "Xiaomi", "model": "Redmi Note 13 Pro+"},
    {"brand": "Xiaomi", "model": "POCO F5 Pro"},
    # Oppo, OnePlus, Google, Realme, Vivo, Huawei, Honor, Nokia, Motorola, Sony, Asus
    {"brand": "Oppo", "model": "Find N3 Flip"},
    {"brand": "Oppo", "model": "Reno10 Pro+"},
    {"brand": "Google", "model": "Pixel 8 Pro"},
    {"brand": "Google", "model": "Pixel 7a"},
    {"brand": "OnePlus", "model": "12"},
    {"brand": "OnePlus", "model": "Nord 3"},
    {"brand": "Realme", "model": "GT 3"},
    {"brand": "Realme", "model": "11 Pro+"},
    {"brand": "Vivo", "model": "X90 Pro+"},
    {"brand": "Vivo", "model": "V29 Pro"},
    {"brand": "Huawei", "model": "P60 Pro"},
    {"brand": "Huawei", "model": "Mate 50 Pro"},
    {"brand": "Honor", "model": "Magic 5 Pro"},
    {"brand": "Honor", "model": "90"},
    {"brand": "Nokia", "model": "G42 5G"},
    {"brand": "Nokia", "model": "C32"},
    {"brand": "Motorola", "model": "Razr 40 Ultra"},
    {"brand": "Motorola", "model": "Edge 40 Pro"},
    {"brand": "Sony", "model": "Xperia 1 V"},
    {"brand": "Sony", "model": "Xperia 5 IV"},
    {"brand": "Asus", "model": "Zenfone 10"},
    {"brand": "Asus", "model": "ROG Phone 7 Ultimate"},
]

def create_data_dir(base_dir, brand, model):
    """Creates directories."""
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    dir_name = f"{brand}_{model}".replace(" ", "_").replace("/", "_").lower()
    product_dir = os.path.join(base_dir, dir_name)
    if not os.path.exists(product_dir):
        os.makedirs(product_dir)
    return product_dir

def is_valid_image_url(image_url):
    """Checks URL validity."""
    try:
        parsed_url = urlparse(image_url)
        if not all([parsed_url.scheme, parsed_url.netloc]):
            return False
        path = unquote(parsed_url.path)
        if not path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            return False
        return True
    except Exception:
        return False

def download_image(image_url, save_path, timeout=10):
    """Downloads an image."""
    if not is_valid_image_url(image_url):
        print(f"Skipping invalid image URL: {image_url}")
        return False

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(image_url, stream=True, timeout=timeout)
            response.raise_for_status()
            with open(save_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            return True
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
            time.sleep(2 ** attempt)  # Exponential backoff
        except Exception as e:
            print(f"Error saving image: {e}")
            return False
    print(f"Failed to download after {max_retries} attempts: {image_url}")
    return False
def search_gsmarena_for_price(brand, model):
    """Searches GSM Arena for a phone's price."""
    query = f"{brand} {model} gsmarena"
    params = {
        "q": query,
        "cx": GOOGLE_SEARCH_ENGINE_ID,  # Use your Google Custom Search Engine ID
        "key": GOOGLE_SEARCH_API_KEY,  # Use your Google Custom Search API Key
        "num": 1
    }
    try:
        response = requests.get(GOOGLE_SEARCH_URL, params=params)
        response.raise_for_status()
        results = response.json()

        if "items" not in results or not results["items"]:
            print(f"No GSM Arena page found for {brand} {model}.")
            return "Price not available on GSM Arena."

        gsmarena_url = results["items"][0]["link"]
        headers = {'User-Agent': 'Mozilla/5.0'}  # Simplified user agent
        gsmarena_response = requests.get(gsmarena_url, headers=headers, timeout=10)
        gsmarena_response.raise_for_status()
        soup = BeautifulSoup(gsmarena_response.text, 'html.parser')

        price_element = soup.find('td', attrs={'data-spec': 'price'})
        if price_element:
            price_text = price_element.get_text(strip=True)
            match = re.search(r'([\d,\.]+)', price_text)
            if match:
                return f"GSM Arena Price (Approximate): {match.group(1)}"
            return "Price not available on GSM Arena."
        else:
            return "Price not available on GSM Arena."

    except requests.exceptions.RequestException as e:
        print(f"Error searching GSM Arena: {e}")
        return "Error retrieving price from GSM Arena."
    except Exception as e:
        print(f"Error parsing GSM Arena page: {e}")
        return "Error parsing price from GSM Arena."

def search_product_price(brand, model):
    """Fetches price from Shopee/Lazada, then GSM Arena."""
    query = f"{brand} {model} price site:shopee.co.th OR site:lazada.co.th"
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

        price_results = [f"{item['title']}: {item['snippet']}" for item in results.get("items", [])
                         if "price" in item["title"].lower() or "฿" in item["snippet"]]

        return "\n".join(price_results) if price_results else search_gsmarena_for_price(brand, model)

    except requests.exceptions.RequestException as e:
        print(f"Error fetching Shopee/Lazada price: {e}")
        return "Error retrieving price data."


def search_and_download_images(brand, model, max_images=MAX_IMAGES_PER_MODEL, min_images=MIN_IMAGES_PER_MODEL):
    """Searches (using SerpAPI) and downloads images, enforcing limits."""
    product_dir = create_data_dir(DATA_DIR, brand, model)
    downloaded_count = 0
    query = f"{brand} {model}"

    params = {
        "q": query,
        "engine": "google_images",
        "ijn": "0",  # Page number
        "api_key": SERPAPI_KEY,
        "tbs": "isz:m" #add Medium size
    }
    search = GoogleSearch(params) #initiate SerpAPI

    while downloaded_count < max_images:
        try:
            results = search.get_dict() #get the result

            if "images_results" not in results:
                print(f"No more image results found for {query}.")
                break

            for result in results["images_results"]:
                if downloaded_count >= max_images:
                    break

                image_url = result["original"]
                image_filename = f"{brand}_{model}_{uuid.uuid4().hex}.jpg".replace(" ", "_").replace("/", "_").lower()
                save_path = os.path.join(product_dir, image_filename)

                if download_image(image_url, save_path):
                    downloaded_count += 1

            # SerpAPI Pagination (if needed):  Move to the next page
            if "next" in results["serpapi_pagination"]:
                #Instead of increment page number, we get it from the next URL
                search.params_dict.update(dict(parse_qsl(urlparse(results["serpapi_pagination"]["next"]).query)))
            else:
                print(f"No more pagination for {query}.")
                break
            time.sleep(random.uniform(1, 3)) #delay

        except Exception as e:
            print(f"Error during SerpAPI search or download: {e}")
            break  #  Exit loop on error

    if downloaded_count < min_images:
        print(f"WARNING: Only {downloaded_count} images for {brand} {model} (min: {min_images}).")
    else:
        print(f"Downloaded {downloaded_count} images for {brand} {model}")

    price_info = search_product_price(brand, model)  # Get price info
    print(f"Price Info for {brand} {model}: {price_info}\n")

def main():
    """Iterates, collects data, and gets prices."""
    for phone in PHONE_MODELS:
        search_and_download_images(phone["brand"], phone["model"])

if __name__ == "__main__":
    main()
