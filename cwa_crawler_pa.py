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


def update_readme_and_split_jsons(old_data, new_data, data_dir, script_dir):
    """Save individual county JSON files and update README.md with changes and forecast table."""
    # 1. Save split JSON files by county
    counties_dir = Path(data_dir) / "counties"
    counties_dir.mkdir(parents=True, exist_ok=True)
    
    for loc_name, slots in new_data["locations"].items():
        county_file = counties_dir / f"{loc_name}.json"
        try:
            county_data = {
                "location": loc_name,
                "updated_at": new_data["updated_at"],
                "forecast": slots
            }
            with open(county_file, 'w', encoding='utf-8') as f:
                json.dump(county_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[!] Failed to save split JSON for {loc_name}: {e}")
            
    print(f"[+] Saved {len(new_data['locations'])} individual county JSON files in: {counties_dir}")

    # 2. Compare data to previous run (index 0 represent the most immediate time slot)
    changes = []
    if old_data and "locations" in old_data:
        old_locs = old_data["locations"]
        new_locs = new_data["locations"]
        
        for loc_name, new_slots in new_locs.items():
            if loc_name in old_locs and len(new_slots) > 0 and len(old_locs[loc_name]) > 0:
                old_slot = old_locs[loc_name][0]
                new_slot = new_slots[0]
                
                loc_changes = []
                
                # Weather phenomenon
                if old_slot.get("weather_phenomenon") != new_slot.get("weather_phenomenon"):
                    loc_changes.append(f"天氣現象由「{old_slot.get('weather_phenomenon')}」轉為「{new_slot.get('weather_phenomenon')}」")
                
                # Rain probability
                try:
                    old_pop = int(old_slot.get("rain_probability", 0))
                    new_pop = int(new_slot.get("rain_probability", 0))
                    if old_pop != new_pop:
                        diff = new_pop - old_pop
                        sign = "+" if diff > 0 else ""
                        loc_changes.append(f"降雨機率 {old_pop}% → {new_pop}% ({sign}{diff}%)")
                except Exception:
                    pass
                
                # Temperatures
                try:
                    old_min = int(old_slot.get("min_temp", 0))
                    new_min = int(new_slot.get("min_temp", 0))
                    old_max = int(old_slot.get("max_temp", 0))
                    new_max = int(new_slot.get("max_temp", 0))
                    
                    temp_change = []
                    if old_min != new_min:
                        diff = new_min - old_min
                        sign = "+" if diff > 0 else ""
                        temp_change.append(f"最低溫 ({sign}{diff}°C)")
                    if old_max != new_max:
                        diff = new_max - old_max
                        sign = "+" if diff > 0 else ""
                        temp_change.append(f"最高溫 ({sign}{diff}°C)")
                    if temp_change:
                        loc_changes.append("、".join(temp_change))
                except Exception:
                    pass
                
                if loc_changes:
                    changes.append(f"* **{loc_name}**：{', '.join(loc_changes)}")
                    
    # 3. Generate Markdown Content
    md_content = []
    
    # Header & timestamp
    updated_dt = datetime.datetime.fromisoformat(new_data["updated_at"])
    formatted_time = updated_dt.strftime("%Y-%m-%d %H:%M:%S")
    md_content.append(f"**⏰ 最後更新時間 (台北時間)**: `{formatted_time}`\n")
    
    # Changes section
    md_content.append("### 📢 天氣變動提醒 (與前次更新相比)")
    if changes:
        md_content.extend(changes)
    else:
        md_content.append("*氣象預報與前次相比無變動。*")
    md_content.append("")
    
    # Table section
    md_content.append("### 🗺️ 各縣市即時預報快照 (最接近時段)")
    md_content.append("| 縣市 | 預報時間段 | 天氣狀態 | 溫度範圍 | 降雨機率 | 舒適度 |")
    md_content.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
    
    for loc_name, slots in new_data["locations"].items():
        if slots:
            s = slots[0]
            start_t = s.get("start_time")
            end_t = s.get("end_time")
            # Format: "07-03 18:00 ~ 06:00"
            time_range = f"{start_t[5:10]} {start_t[11:16]} ~ {end_t[11:16]}"
            md_content.append(
                f"| {loc_name} | {time_range} | {s.get('weather_phenomenon')} | {s.get('min_temp')}°C ~ {s.get('max_temp')}°C | {s.get('rain_probability')}% | {s.get('comfort_index')} |"
            )
            
    md_block = "\n".join(md_content)
    
    # 4. Read README.md and replace content between markers
    readme_path = Path(script_dir) / "README.md"
    if readme_path.exists():
        try:
            with open(readme_path, 'r', encoding='utf-8') as f:
                readme_text = f.read()
                
            start_marker = "<!-- WEATHER_START -->"
            end_marker = "<!-- WEATHER_END -->"
            
            if start_marker in readme_text and end_marker in readme_text:
                parts = readme_text.split(start_marker)
                before = parts[0]
                after = parts[1].split(end_marker)[1]
                
                new_readme = f"{before}{start_marker}\n\n{md_block}\n\n{end_marker}{after}"
                
                with open(readme_path, 'w', encoding='utf-8') as f:
                    f.write(new_readme)
                print("[+] README.md has been automatically updated with the latest weather info.")
            else:
                print("[!] Warning: WEATHER markers not found in README.md. Skipping README update.")
        except Exception as e:
            print(f"[!] Failed to update README.md: {e}")

def save_weather_json(summary, data_dir):
    """Save simplified summary JSON as a single weather.json file, then update split files and README.md."""
    data_dir.mkdir(parents=True, exist_ok=True)
    weather_file = data_dir / "weather.json"
    
    # 1. Read old data if it exists to compare later
    old_data = None
    if weather_file.exists():
        try:
            with open(weather_file, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
        except Exception:
            pass
            
    # 2. Write new data
    try:
        with open(weather_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"[+] Weather JSON updated: {weather_file}")
        
        # 3. Save split county files and update README.md
        update_readme_and_split_jsons(old_data, summary, data_dir, SCRIPT_DIR)
        
    except Exception as e:
        print(f"[!] Failed to save weather JSON: {e}")


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