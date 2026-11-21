#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <time.h>
#include "sas_refresh.h"
#include "device_secrets.h"

#include "mbedtls/base64.h"
#include "mbedtls/md.h"

// =======================
// 1) НАЛАШТУВАННЯ
// =======================




const bool SEND_DEVICE_LOCATION = true;
const double DEVICE_LATITUDE = 49.83870;
const double DEVICE_LONGITUDE = 23.99440;


static const int MQTT_PORT = 8883;
static const char* MQTT_API_VERSION = "2021-04-12";

#define TRIG_PIN 5
#define ECHO_PIN 18

float occupiedBelowCm = 40.0f;
float freeAboveCm = 55.0f;
bool occupied = false;

const uint32_t SEND_EVERY_MS = 5000;

const uint32_t SAS_TTL_SECS = 3600;
const uint32_t SAS_REFRESH_BEFORE_SECS = 300;

static const char* AZURE_IOTHUB_CA_CHAIN_PEM = R"EOF(
-----BEGIN CERTIFICATE-----
MIIEtjCCA56gAwIBAgIQCv1eRG9c89YADp5Gwibf9jANBgkqhkiG9w0BAQsFADBh
MQswCQYDVQQGEwJVUzEVMBMGA1UEChMMRGlnaUNlcnQgSW5jMRkwFwYDVQQLExB3
d3cuZGlnaWNlcnQuY29tMSAwHgYDVQQDExdEaWdpQ2VydCBHbG9iYWwgUm9vdCBH
MjAeFw0yMjA0MjgwMDAwMDBaFw0zMjA0MjcyMzU5NTlaMEcxCzAJBgNVBAYTAlVT
MR4wHAYDVQQKExVNaWNyb3NvZnQgQ29ycG9yYXRpb24xGDAWBgNVBAMTD01TRlQg
UlMyNTYgQ0EtMTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAMiJV34o
eVNHI0mZGh1Rj9mdde3zSY7IhQNqAmRaTzOeRye8QsfhYFXSiMW25JddlcqaqGJ9
GEMcJPWBIBIEdNVYl1bB5KQOl+3m68p59Pu7npC74lJRY8F+p8PLKZAJjSkDD9Ex
mjHBlPcRrasgflPom3D0XB++nB1y+WLn+cB7DWLoj6qZSUDyWwnEDkkjfKee6ybx
SAXq7oORPe9o2BKfgi7dTKlOd7eKhotw96yIgMx7yigE3Q3ARS8m+BOFZ/mx150g
dKFfMcDNvSkCpxjVWnk//icrrmmEsn2xJbEuDCvtoSNvGIuCXxqhTM352HGfO2JK
AF/Kjf5OrPn2QpECAwEAAaOCAYIwggF+MBIGA1UdEwEB/wQIMAYBAf8CAQAwHQYD
VR0OBBYEFAyBfpQ5X8d3on8XFnk46DWWjn+UMB8GA1UdIwQYMBaAFE4iVCAYlebj
buYP+vq5Eu0GF485MA4GA1UdDwEB/wQEAwIBhjAdBgNVHSUEFjAUBggrBgEFBQcD
AQYIKwYBBQUHAwIwdgYIKwYBBQUHAQEEajBoMCQGCCsGAQUFBzABhhhodHRwOi8v
b2NzcC5kaWdpY2VydC5jb20wQAYIKwYBBQUHMAKGNGh0dHA6Ly9jYWNlcnRzLmRp
Z2ljZXJ0LmNvbS9EaWdpQ2VydEdsb2JhbFJvb3RHMi5jcnQwQgYDVR0fBDswOTA3
oDWgM4YxaHR0cDovL2NybDMuZGlnaWNlcnQuY29tL0RpZ2lDZXJ0R2xvYmFsUm9v
dEcyLmNybDA9BgNVHSAENjA0MAsGCWCGSAGG/WwCATAHBgVngQwBATAIBgZngQwB
AgEwCAYGZ4EMAQICMAgGBmeBDAECAzANBgkqhkiG9w0BAQsFAAOCAQEAdYWmf+AB
klEQShTbhGPQmH1c9BfnEgUFMJsNpzo9dvRj1Uek+L9WfI3kBQn97oUtf25BQsfc
kIIvTlE3WhA2Cg2yWLTVjH0Ny03dGsqoFYIypnuAwhOWUPHAu++vaUMcPUTUpQCb
eC1h4YW4CCSTYN37D2Q555wxnni0elPj9O0pymWS8gZnsfoKjvoYi/qDPZw1/TSR
penOgI6XjmlmPLBrk4LIw7P7PPg4uXUpCzzeybvARG/NIIkFv1eRYIbDF+bIkZbJ
QFdB9BjjlA4ukAg2YkOyCiB8eXTBi2APaceh3+uBLIgLk8ysy52g2U3gP7Q26Jlg
q/xKzj3O9hFh/g==
-----END CERTIFICATE-----

-----BEGIN CERTIFICATE-----
MIIDjjCCAnagAwIBAgIQAzrx5qcRqaC7KGSxHQn65TANBgkqhkiG9w0BAQsFADBh
MQswCQYDVQQGEwJVUzEVMBMGA1UEChMMRGlnaUNlcnQgSW5jMRkwFwYDVQQLExB3
d3cuZGlnaWNlcnQuY29tMSAwHgYDVQQDExdEaWdpQ2VydCBHbG9iYWwgUm9vdCBH
MjAeFw0xMzA4MDExMjAwMDBaFw0zODAxMTUxMjAwMDBaMGExCzAJBgNVBAYTAlVT
MRUwEwYDVQQKEwxEaWdpQ2VydCBJbmMxGTAXBgNVBAsTEHd3dy5kaWdpY2VydC5j
b20xIDAeBgNVBAMTF0RpZ2lDZXJ0IEdsb2JhbCBSb290IEcyMIIBIjANBgkqhkiG
9w0BAQEFAAOCAQ8AMIIBCgKCAQEAuzfNNNx7a8myaJCtSnX/RrohCgiN9RlUyfuI
2/Ou8jqJkTx65qsGGmvPrC3oXgkkRLpimn7Wo6h+4FR1IAWsULecYxpsMNzaHxmx
1x7e/dfgy5SDN67sH0NO3Xss0r0upS/kqbitOtSZpLYl6ZtrAGCSYP9PIUkY92eQ
q2EGnI/yuum06ZIya7XzV+hdG82MHauVBJVJ8zUtluNJbd134/tJS7SsVQepj5Wz
tCO7TG1F8PapspUwtP1MVYqooOQY62wivcIHjYbIUl5/gxxQKhi5B3rAqO67uB52
qGkHUQaXxkRed1b+R1E9kTnkk9q7Bvm2rWc3fnG7XlbwXyB6GQIDAQABo0IwQDAP
BgNVHRMBAf8EBTADAQH/MA4GA1UdDwEB/wQEAwIBhjAdBgNVHQ4EFgQUTiJUIBiV
5uNu5g/6+rkS7QYXjzkwDQYJKoZIhvcNAQELBQADggEBAGBnKJRvDkhj6zHd6mcY
1Yl9PMWLSn/pvtsrF9+wX3N3KjITOYFnQoQj8kVnNeyIv/iPsGEMNKSuIEyExtv4
NeF22d+mQrvHRAiGfzZ0JFrabA0UWTW98kndth/Jsw1HKj2ZL7tcu7XUIOGZX1NG
Fdtom/DzMNU+MeKNhJ7jitralj41E6Vf8PlwUHBHQRFXGU7Aj64GxJUTFy8bJZ91
8rGOmaFvE7FBcf6IKshPECBV1/MUReXgRPTqh5Uykw7+U0b6LJ3/iyK5S9kJRaTe
pLiaWN0bfVKfjllDiIGknibVb63dDcY3fe0Dkhvld1927jyNxF1WW6LZZm6zNTfl
MrY=
-----END CERTIFICATE-----
)EOF";

// =======================
// 2) ГЛОБАЛИ
// =======================
WiFiClientSecure tlsClient;
PubSubClient mqtt(tlsClient);

String sasToken;
uint64_t sasExpiry = 0;
uint32_t lastSend = 0;

// =======================
// 3) УТИЛІТИ
// =======================
static String urlEncode(const String& s) {
  String out;
  for (size_t i = 0; i < s.length(); i++) {
    char c = s[i];
    if (isalnum((unsigned char)c) || c == '-' || c == '_' || c == '.' || c == '~') out += c;
    else {
      char buf[4];
      snprintf(buf, sizeof(buf), "%%%02X", (unsigned char)c);
      out += buf;
    }
  }
  return out;
}

static bool base64Decode(const char* input, uint8_t* outBuf, size_t outBufSize, size_t* outLen) {
  size_t len = 0;
  int rc = mbedtls_base64_decode(outBuf, outBufSize, &len,
                                (const unsigned char*)input, strlen(input));
  if (rc != 0) return false;
  *outLen = len;
  return true;
}

static bool hmacSha256(const uint8_t* key, size_t keyLen,
                       const uint8_t* msg, size_t msgLen,
                       uint8_t* out, size_t outSize, size_t* outLen) {
  const mbedtls_md_info_t* mdInfo = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
  if (!mdInfo) return false;

  mbedtls_md_context_t ctx;
  mbedtls_md_init(&ctx);

  if (mbedtls_md_setup(&ctx, mdInfo, 1) != 0) { mbedtls_md_free(&ctx); return false; }
  if (mbedtls_md_hmac_starts(&ctx, key, keyLen) != 0) { mbedtls_md_free(&ctx); return false; }
  if (mbedtls_md_hmac_update(&ctx, msg, msgLen) != 0) { mbedtls_md_free(&ctx); return false; }
  if (mbedtls_md_hmac_finish(&ctx, out) != 0) { mbedtls_md_free(&ctx); return false; }

  mbedtls_md_free(&ctx);
  *outLen = 32;
  return outSize >= 32;
}

static uint64_t getEpochTime() {
  time_t now = time(nullptr);
  return (uint64_t)now;
}

static void syncTimeNtpHard() {
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  Serial.print("Sync time");
  while (true) {
    time_t now = time(nullptr);
    if (now > 1700000000) break;
    Serial.print(".");
    delay(500);
  }
  Serial.println();
  Serial.print("Epoch: ");
  Serial.println((unsigned long)time(nullptr));
}

static String buildSasToken(uint64_t nowEpoch) {
  String resourceUri = String(IOT_HUB_HOSTNAME) + "/devices/" + String(DEVICE_ID);
  resourceUri.toLowerCase();

  uint64_t expiry = nowEpoch + SAS_TTL_SECS;
  sasExpiry = expiry;

  String srEncoded = urlEncode(resourceUri);
  String toSign = srEncoded + "\n" + String((unsigned long)expiry);

  uint8_t keyBin[64];
  size_t keyLen = 0;
  if (!base64Decode(DEVICE_KEY, keyBin, sizeof(keyBin), &keyLen)) {
    Serial.println("ERROR: base64 decode DEVICE_KEY failed");
    return "";
  }

  uint8_t hmac[32];
  size_t hmacLen = 0;
  if (!hmacSha256(keyBin, keyLen, (const uint8_t*)toSign.c_str(), toSign.length(),
                  hmac, sizeof(hmac), &hmacLen)) {
    Serial.println("ERROR: HMAC failed");
    return "";
  }

  unsigned char sigB64[128];
  size_t sigB64Len = 0;
  if (mbedtls_base64_encode(sigB64, sizeof(sigB64), &sigB64Len, hmac, hmacLen) != 0) {
    Serial.println("ERROR: base64 encode HMAC failed");
    return "";
  }

  String sig = String((char*)sigB64).substring(0, sigB64Len);
  String sigEncoded = urlEncode(sig);

  return "SharedAccessSignature sr=" + srEncoded +
         "&sig=" + sigEncoded +
         "&se=" + String((unsigned long)expiry);
}

// =======================
// 4) СЕНСОР
// =======================
static float readDistanceCmOnce() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  unsigned long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  if (duration == 0) return -1.0;
  float cm = duration / 58.2f;
  return cm >= 2.0f && cm <= 400.0f ? cm : -1.0f;
}

static float readDistanceCmAvg(int n = 5) {
  float sum = 0;
  int ok = 0;
  for (int i = 0; i < n; i++) {
    float d = readDistanceCmOnce();
    if (d > 0) { sum += d; ok++; }
    delay(20);
  }
  return ok == 0 ? -1.0 : (sum / ok);
}

static void updateOccupiedState(float cm) {
  if (!occupied && cm < occupiedBelowCm) occupied = true;
  if (occupied && cm > freeAboveCm) occupied = false;
}

static String buildTelemetryPayload(float cm) {
  uint64_t now = getEpochTime();

  String payload =
    String("{") +
    "\"deviceId\":\"" + String(DEVICE_ID) + "\"," +
    "\"ts\":" + String((unsigned long)now) + "," +
    "\"distanceCm\":" + String(cm, 1) + "," +
    "\"occupied\":" + String(occupied ? "true" : "false");

  if (SEND_DEVICE_LOCATION) {
    payload +=
      String(",\"latitude\":") + String(DEVICE_LATITUDE, 6) +
      ",\"longitude\":" + String(DEVICE_LONGITUDE, 6);
  }

  payload += "}";
  return payload;
}

static bool publishTelemetry(float cm) {
  String topic = "devices/" + String(DEVICE_ID) + "/messages/events/?$ct=application%2Fjson&$ce=utf-8";
  String payload = buildTelemetryPayload(cm);
  bool pubOk = mqtt.publish(topic.c_str(), payload.c_str());

  Serial.print("Publish ");
  Serial.print(pubOk ? "OK" : "FAIL");
  Serial.print(" | ");
  Serial.println(payload);

  return pubOk;
}

static bool tryReadJsonNumber(const String& json, const char* fieldName, float& value) {
  String marker = String("\"") + fieldName + "\"";
  int markerIndex = json.indexOf(marker);
  if (markerIndex < 0) return false;

  int colonIndex = json.indexOf(':', markerIndex + marker.length());
  if (colonIndex < 0) return false;

  int start = colonIndex + 1;
  while (start < json.length() && isspace((unsigned char)json[start])) start++;

  int end = start;
  while (end < json.length()) {
    char c = json[end];
    if ((c >= '0' && c <= '9') || c == '-' || c == '+' || c == '.') {
      end++;
      continue;
    }
    break;
  }

  if (end <= start) return false;

  value = json.substring(start, end).toFloat();
  return true;
}

static String extractMethodRequestId(const String& topic) {
  int ridIndex = topic.indexOf("$rid=");
  if (ridIndex < 0) return "";

  String requestId = topic.substring(ridIndex + 5);
  int ampIndex = requestId.indexOf('&');
  if (ampIndex >= 0) {
    requestId = requestId.substring(0, ampIndex);
  }

  return requestId;
}

static String extractMethodName(const String& topic) {
  const String prefix = "$iothub/methods/POST/";
  if (!topic.startsWith(prefix)) return "";

  int start = prefix.length();
  int end = topic.indexOf('/', start);
  if (end < 0) return "";

  return topic.substring(start, end);
}

static void publishMethodResponse(int statusCode, const String& requestId, const String& payload) {
  String responseTopic = "$iothub/methods/res/" + String(statusCode) + "/?$rid=" + requestId;
  bool ok = mqtt.publish(responseTopic.c_str(), payload.c_str());

  Serial.print("Method response ");
  Serial.print(ok ? "OK" : "FAIL");
  Serial.print(" | topic=");
  Serial.print(responseTopic);
  Serial.print(" | payload=");
  Serial.println(payload);
}

static void handleDeviceMethod(const String& methodName, const String& requestId, const String& payload) {
  if (methodName == "ping") {
    publishMethodResponse(
      200,
      requestId,
      String("{\"ok\":true,\"message\":\"pong\",\"deviceId\":\"") + DEVICE_ID + "\"}");
    return;
  }

  if (methodName == "measureNow") {
    float cm = readDistanceCmAvg(5);
    if (cm < 0) {
      publishMethodResponse(500, requestId, "{\"ok\":false,\"message\":\"measurement_failed\"}");
      return;
    }

    updateOccupiedState(cm);
    publishTelemetry(cm);
    lastSend = millis();
    publishMethodResponse(
      200,
      requestId,
      String("{\"ok\":true,\"distanceCm\":") + String(cm, 1) +
      ",\"occupied\":" + String(occupied ? "true" : "false") + "}");
    return;
  }

  if (methodName == "setThresholds") {
    float nextOccupiedBelowCm = occupiedBelowCm;
    float nextFreeAboveCm = freeAboveCm;

    bool hasOccupiedBelow = tryReadJsonNumber(payload, "occupiedBelowCm", nextOccupiedBelowCm);
    bool hasFreeAbove = tryReadJsonNumber(payload, "freeAboveCm", nextFreeAboveCm);

    if (!hasOccupiedBelow || !hasFreeAbove || nextOccupiedBelowCm <= 0 || nextFreeAboveCm <= nextOccupiedBelowCm) {
      publishMethodResponse(400, requestId, "{\"ok\":false,\"message\":\"invalid_thresholds\"}");
      return;
    }

    occupiedBelowCm = nextOccupiedBelowCm;
    freeAboveCm = nextFreeAboveCm;

    publishMethodResponse(
      200,
      requestId,
      String("{\"ok\":true,\"occupiedBelowCm\":") + String(occupiedBelowCm, 1) +
      ",\"freeAboveCm\":" + String(freeAboveCm, 1) + "}");
    return;
  }

  if (methodName == "reboot") {
    publishMethodResponse(200, requestId, "{\"ok\":true,\"message\":\"restarting\"}");
    delay(250);
    ESP.restart();
    return;
  }

  publishMethodResponse(404, requestId, "{\"ok\":false,\"message\":\"unknown_method\"}");
}

static void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  String topicText = String(topic);
  String payloadText;
  payloadText.reserve(length);

  for (unsigned int i = 0; i < length; i++) {
    payloadText += (char)payload[i];
  }

  Serial.print("MQTT inbound | topic=");
  Serial.print(topicText);
  Serial.print(" | payload=");
  Serial.println(payloadText);

  if (!topicText.startsWith("$iothub/methods/POST/")) {
    return;
  }

  String methodName = extractMethodName(topicText);
  String requestId = extractMethodRequestId(topicText);

  if (methodName.length() == 0 || requestId.length() == 0) {
    Serial.println("Unable to parse direct method topic");
    return;
  }

  handleDeviceMethod(methodName, requestId, payloadText);
}

// =======================
// 5) MQTT CONNECT
// =======================
static void printTlsLastError() {
  char buf[128];
  int err = tlsClient.lastError(buf, sizeof(buf));
  Serial.print("TLS lastError=");
  Serial.print(err);
  Serial.print(" | ");
  Serial.println(buf);
}

static bool ensureMqttConnected() {
  uint64_t now = getEpochTime();
  bool refresh = sasToken.length() == 0 || shouldRefreshSas(now, sasExpiry, SAS_REFRESH_BEFORE_SECS);
  if (mqtt.connected() && !refresh) return true;
  if (mqtt.connected()) mqtt.disconnect();

  IPAddress ip;
  if (WiFi.hostByName(IOT_HUB_HOSTNAME, ip)) {
    Serial.print("IoT Hub IP: ");
    Serial.println(ip);
  } else {
    Serial.println("DNS failed for IoT Hub hostname");
  }

  now = getEpochTime();
  if (now < 1700000000) {
    Serial.println("Time not synced yet, syncing...");
    syncTimeNtpHard();
    now = getEpochTime();
  }

  if (sasToken.length() == 0 || shouldRefreshSas(now, sasExpiry, SAS_REFRESH_BEFORE_SECS)) {
    sasToken = buildSasToken(now);
    Serial.println("SAS token generated/refreshed");
  }

  String username = String(IOT_HUB_HOSTNAME) + "/" + String(DEVICE_ID) + "/?api-version=" + MQTT_API_VERSION;

  Serial.print("MQTT connecting to ");
  Serial.print(IOT_HUB_HOSTNAME);
  Serial.print(":");
  Serial.println(MQTT_PORT);

  bool ok = mqtt.connect(DEVICE_ID, username.c_str(), sasToken.c_str());
  if (!ok) {
    Serial.print("MQTT connect failed, rc=");
    Serial.println(mqtt.state());
    printTlsLastError();
    return false;
  }

  Serial.println("MQTT connected");
  bool subOk = mqtt.subscribe("$iothub/methods/POST/#");
  Serial.print("Direct methods subscribe ");
  Serial.println(subOk ? "OK" : "FAIL");
  return true;
}

// =======================
// 6) SETUP/LOOP
// =======================
void setup() {
  Serial.begin(115200);
  delay(300);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  digitalWrite(TRIG_PIN, LOW);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  Serial.print("WiFi connecting");
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(500);
  }
  Serial.println();
  Serial.print("WiFi OK, IP: ");
  Serial.println(WiFi.localIP());

  tlsClient.setCACert(AZURE_IOTHUB_CA_CHAIN_PEM);
  tlsClient.setTimeout(15000);
  tlsClient.setHandshakeTimeout(30);
  Serial.println("TLS: CA cert set (secure mode)");

  mqtt.setServer(IOT_HUB_HOSTNAME, MQTT_PORT);
  mqtt.setCallback(onMqttMessage);

  mqtt.setBufferSize(2048);
  Serial.print("MQTT buffer size = ");
  Serial.println(mqtt.getBufferSize());

  mqtt.setKeepAlive(60);
  mqtt.setSocketTimeout(10);

  syncTimeNtpHard();
}

void loop() {
  mqtt.loop();

  if (millis() - lastSend < SEND_EVERY_MS) return;
  lastSend = millis();

  float cm = readDistanceCmAvg(5);
  if (cm < 0) {
    Serial.println("No echo");
    return;
  }

  updateOccupiedState(cm);

  if (!ensureMqttConnected()) {
    delay(500);
    return;
  }

  publishTelemetry(cm);
}
