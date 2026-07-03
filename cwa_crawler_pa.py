#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Taiwan Weather Tracker - PythonAnywhere Dedicated Crawler

功能：
1. 讀取 config.json
2. 呼叫中央氣象署 CWA API
3. 解決 PythonAnywhere SSL 憑證問題
4. 解析 36 小時天氣預報
5. 輸出固定檔案 data/weather.json
6. 適合 GitHub Commit History 追蹤變化
"""

import os
import ssl
import json
import datetime
import urllib.request
import urllib.error
from pathlib import Path


SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = SCRIPT_DIR / "config.json"

DEFAULT_DATASET = "F-C0032-001"
API_URL = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/{DEFAULT_DATASET}"


def get_config():
    if not CONFIG_PATH.exists():
        default_config = {
            "cwa_api_key": "YOUR_CWA_API_KEY_HERE",
            "output_dir": "data"
        }

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)

        print(f"[!] config.json not found. Created template at: {CONFIG_PATH}")
        print("[!] Please edit config.json and add your CWA API Key.")
        return None

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[!] Error reading config.json: {e}")
        return None


def fetch_cwa_data(api_key):
    query_url = f"{API_URL}?Authorization={api_key}&format=JSON"

    req = urllib.request.Request(
        query_url,
        headers={"User-Agent": "PythonAnywhereCWAClient/1.0"}
    )

    try:
        context = ssl._create_unverified_context()

        with urllib.request.urlopen(req, timeout=30, context=context) as response:
            if response.status != 200:
                print(f"[!] API returned HTTP status: {response.status}")
                return None

            raw_text = response.read().decode("utf-8")
            raw_data = json.loads(raw_text)

            print("[+] API call successful.")
            return raw_data

    except urllib.error.HTTPError as e:
        print(f"[!] HTTP Error {e.code}: {e.reason}")
        return None
    except urllib.error.URLError as e:
        print(f"[!] URL Error: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"[!] JSON parsing error: {e}")
        return None
    except Exception as e:
        print(f"[!] Connection or parsing error: {e}")
        return None


def parse_forecast_36h(raw_data, now):
    records = raw_data.get("records", {})
    locations = records.get("location", [])

    parsed_locations = {}

    for loc in locations:
        loc_name = loc.get("locationName")
        elements = loc.get("weatherElement", [])

        if not loc_name or not elements:
            continue

        element_map = {
            el.get("elementName"): el.get("time", [])
            for el in elements
        }

        wx_times = element_map.get("Wx", [])
        time_slots = []

        for i in range(len(wx_times)):

            def get_element_info(name):
                times = element_map.get(name, [])
                if len(times) > i:
                    param = times[i].get("parameter", {})
                    return (
                        param.get("parameterName"),
                        param.get("parameterValue")
                    )
                return None, None

            wx_name, wx_code = get_element_info("Wx")
            pop_value, _ = get_element_info("PoP")
            min_t, _ = get_element_info("MinT")
            max_t, _ = get_element_info("MaxT")
            ci_name, _ = get_element_info("CI")

            time_slots.append({
                "start_time": wx_times[i].get("startTime"),
                "end_time": wx_times[i].get("endTime"),
                "weather_phenomenon": wx_name,
                "weather_code": wx_code,
                "rain_probability": pop_value,
                "min_temp": min_t,
                "max_temp": max_t,
                "comfort_index": ci_name
            })

        parsed_locations[loc_name] = time_slots

    return {
        "dataset_id": DEFAULT_DATASET,
        "title": "台灣今明36小時天氣預報",
        "updated_at": now.isoformat(),
        "location_count": len(parsed_locations),
        "locations": parsed_locations
    }


def save_weather_json(summary, data_dir):
    data_dir.mkdir(parents=True, exist_ok=True)

    weather_file = data_dir / "weather.json"

    with open(weather_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"[+] Weather JSON updated: {weather_file}")


def main():
    tz_taiwan = datetime.timezone(datetime.timedelta(hours=8))
    now = datetime.datetime.now(tz_taiwan)

    print(f"[*] Starting CWA weather data fetch at {now.isoformat()} (Taiwan Time)...")

    config = get_config()
    if not config:
        print("[!] Execution aborted due to config error.")
        return

    api_key = config.get("cwa_api_key")

    if not api_key or api_key == "YOUR_CWA_API_KEY_HERE":
        print("[!] Error: CWA API Key is not configured in config.json.")
        return

    output_dir_name = config.get("output_dir", "data")
    data_dir = SCRIPT_DIR / output_dir_name

    raw_data = fetch_cwa_data(api_key)
    if raw_data is None:
        print("[!] Fetch failed. No data saved.")
        return

    try:
        summary = parse_forecast_36h(raw_data, now)
        save_weather_json(summary, data_dir)

        print("[+] CWA weather tracker task executed successfully!")

    except Exception as e:
        print(f"[!] Error parsing or saving weather data: {e}")


if __name__ == "__main__":
    main()