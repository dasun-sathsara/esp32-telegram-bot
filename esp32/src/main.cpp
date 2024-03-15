#include <Arduino.h>
#include <ArduinoJson.h>
#include <FastLED.h>
#include <WebSocketsClient.h>
#include <WiFi.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

#define WS_HOST ""  // Replace with your WebSocket Server IP or Hostname
#define WS_PORT 443 // Replace with your WebSocket Server Port

#define LED_PIN 48
#define NUM_LEDS 1

// Wi-Fi credentials
const char *ssid = "";
const char *password = "";

WebSocketsClient wsClient;
CRGB led[NUM_LEDS];
TimerHandle_t ledOffTimer;

void sendLedStateChange(const char *origin, const char *state)
{
    // Create a JSON document
    JsonDocument doc;

    // Set the values
    if (strcmp(origin, "tg") == 0)
    {
        doc["type"] = "tg_change_state";
    }
    else if (strcmp(origin, "esp32") == 0)
    {
        doc["type"] = "esp32_change_state";
    }

    doc["state"] = state;

    // Serialize the JSON document
    char buffer[256];
    size_t length = serializeJson(doc, buffer);

    // Send the message
    wsClient.sendTXT(buffer, length);
}

void turnOffLed(TimerHandle_t xTimer)
{
    led[0] = CRGB::Black;
    FastLED.show();
    sendLedStateChange("esp32", "off");
}

void changeLedColor(const char *message)
{
    if (strcmp(message, "red") == 0)
    {
        led[0] = CRGB::Red;
    }
    else if (strcmp(message, "blue") == 0)
    {
        led[0] = CRGB::Blue;
    }
    else if (strcmp(message, "off") == 0)
    {
        led[0] = CRGB::Black;
    }
    FastLED.show();

    // Start the timer
    if (xTimerStart(ledOffTimer, 0) != pdPASS)
    {
        Serial.println("[ERROR] Failed to start timer");
    }
}

void handleMessages(uint8_t *payload, size_t length)
{
    // Deserialize JSON
    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, payload);

    if (error)
    {
        Serial.print("[ERROR] JSON deserialization error: ");
        Serial.println(error.c_str());
        return;
    }

    // Check for the 'tg_change_state' type
    const char *messageType = doc["type"];
    if (strcmp(messageType, "tg_change_state") == 0)
    {
        const char *state = doc["state"];
        changeLedColor(state);
        sendLedStateChange("tg", state);
    }
}

void handleEvent(WStype_t type, uint8_t *payload, size_t length)
{
    switch (type)
    {
    case WStype_DISCONNECTED:
        Serial.printf("[INFO] Disconnected from the WebSocket Server!\n");
        break;
    case WStype_CONNECTED:
        Serial.printf("[INFO] Connected to the WebSocket Server \n");
        break;
    case WStype_TEXT:
        Serial.printf("<<< %s\n", payload);
        handleMessages(payload, length);
        break;
    }
}

[[noreturn]] void checkWifiTask(void *param)
{
    while (true)
    {
        if (WiFiClass::status() != WL_CONNECTED)
        {
            Serial.println("[INFO] Reconnecting to the Wi-Fi Network");
            WiFi.reconnect();
        }

        // Delay for 1 minutes
        vTaskDelay(60 * 1000 / portTICK_PERIOD_MS);
    }
}

[[noreturn]] void reconnectWebSocketsTask(void *param)
{
    while (true)
    {
        if (!wsClient.isConnected())
        {
            Serial.println("[INFO] Reconnecting to the WebSocket Server");

            wsClient.beginSSL(WS_HOST, WS_PORT, nullptr, "", "wss");
            wsClient.onEvent(handleEvent);
        }

        // Delay for 0.5 minutes
        vTaskDelay(30 * 1000 / portTICK_PERIOD_MS);
    }
}

void setup()
{
    Serial.begin(115200);

    WiFi.begin(ssid, password);

    CFastLED::addLeds<WS2812, LED_PIN, GRB>(led, NUM_LEDS);

    // Setting the LED to Black turns it off
    led[0] = CRGB::Black;
    FastLED.show();

    // Block until Wi-Fi is connected
    while (WiFiClass::status() != WL_CONNECTED)
    {
        delay(100);
    }

    xTaskCreate(checkWifiTask, "WiFi Reconnected Task", 2048, nullptr, 2, nullptr);

    ledOffTimer = xTimerCreate("Led Off Timer", pdMS_TO_TICKS(5000), pdFALSE, nullptr, turnOffLed);
    if (ledOffTimer == nullptr)
    {
        Serial.println("[ERROR] Failed to create timer");
    }

    wsClient.beginSSL(WS_HOST, WS_PORT, nullptr, "", "wss");
    wsClient.onEvent(handleEvent);

    // This task will check if the WebSocket is connected and reconnect if it's not, every 30 seconds
    xTaskCreate(reconnectWebSocketsTask, "Reconnect WebSockets Task", 2048, nullptr, 2, nullptr);
}

void loop()
{
    wsClient.loop();
}
