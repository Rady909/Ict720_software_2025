#include <M5GFX.h>
#include <WiFi.h>
#include <qrcode.h>

// Wi-Fi Credentials
#define WIFI_SSID "The Campus 1613"
#define WIFI_PASSWORD "12345678"

// URL to Display as QR Code (Change this to your desired link)
#define TARGET_URL "https://tarpon-workable-optionally.ngrok-free.app"

// Display Setup
M5GFX display;

void drawQRCode(const char* text) {
    QRCode qrcode;
    uint8_t qrcodeData[qrcode_getBufferSize(3)];
    qrcode_initText(&qrcode, qrcodeData, 3, 0, text);

    int qrSize = qrcode.size;
    int blockSize = 6;

    display.fillScreen(TFT_WHITE);
    display.setTextSize(2);
    display.setTextColor(TFT_BLACK, TFT_WHITE);
    display.setCursor(20, 20);
    display.println("Scan to Visit: ProdScan");

    for (int y = 0; y < qrSize; y++) {
        for (int x = 0; x < qrSize; x++) {
            int xPos = 40 + (x * blockSize);
            int yPos = 60 + (y * blockSize);
            if (qrcode_getModule(&qrcode, x, y)) {
                display.fillRect(xPos, yPos, blockSize, blockSize, TFT_BLACK);
            }
        }
    }
    Serial.println("QR Code Rendered!");
}

void setup() {
    Serial.begin(115200);
    Serial.println("Starting QR Code Display...");

    display.init();
    display.fillScreen(TFT_WHITE);
    display.setTextColor(TFT_BLACK, TFT_WHITE);
    display.setTextSize(2);
    display.setCursor(20, 20);
    display.println("Connecting to WiFi...");

    // Connect to Wi-Fi
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }

    Serial.println("\nWiFi Connected!");
    display.fillScreen(TFT_WHITE);
    display.setCursor(20, 20);
    display.println("WiFi Connected!");

    // Display QR Code
    drawQRCode(TARGET_URL);
}

void loop() {
    // No need to loop anything; just keep showing the QR code.
}
