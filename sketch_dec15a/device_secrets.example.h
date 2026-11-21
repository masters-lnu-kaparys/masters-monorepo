#pragma once
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASS = "YOUR_WIFI_PASSWORD";
const char* IOT_HUB_HOSTNAME = "YOUR_HUB.azure-devices.net";
const char* DEVICE_ID = "YOUR_DEVICE_ID";
const char* DEVICE_KEY = "YOUR_BASE64_DEVICE_KEY";

// A stable numeric identifier for the place monitored by this device.
#define PARKING_BAY_ID 999999999UL
// POSIX time zone used to select the time-of-day context.
#define PARKING_TIME_ZONE "EET-2EEST,M3.5.0/3,M10.5.0/4"
