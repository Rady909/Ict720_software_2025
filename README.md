# ProdScan - AI-Based Product Identification System  

Repo for demo idea, model, and code for ICT720 course of 2025.
![Product Flowchart](product_ws/Product.png)


## Team Members  

1. Thanawin Ungkananuchat  
2. Sahatus Asawadilockchai  
3. Rady LY  

---

## **User Stories**  

1. **As a consumer**, I want to scan any product using my smartphone camera, so that I can get details about it instantly.  
2. **As a store manager**, I want to identify products in my inventory using AI, so that I can quickly check specifications and pricing.  
3. **As a production operator**, I want to register and categorize products efficiently, so that I can optimize stock management.  

---

## **Project Overview**  
This project enables **real-time product recognition** using **a smartphone camera and AI**.  
Users can scan **any random product (electronics, food, household items, etc.)**, and the system will identify it using **Google Gemini API**, providing details like **brand, release date, price, and specifications**.

---

## **Features**  
Scan any product using a smartphone camera
AI-based product recognition using Google Gemini API
Displays brand, release date, key specifications, and price (if available)
Works on mobile devices without app installation
HTTPS support via Ngrok for iOS compatibility
Supports multiple product categories (smartphones, electronics, food, etc.)

---

## **Tech Stack**  

| Component  | Technology Used |
|------------|----------------|
| **Frontend (Web UI)** | HTML, WebRTC API |
| **Backend (API Server)** | Flask (Python) |
| **AI Model (Product Recognition)** | Google Gemini API |
| **Camera Access** | WebRTC API (Back Camera) |
| **Secure Connection** | Ngrok (for HTTPS) |
| **Product Data Retrieval** | Web Scraping / External APIs (Amazon, Walmart, etc.) |

---

## **Setup & Installation**  

### **Install Dependencies**  
```bash
pip install flask requests
