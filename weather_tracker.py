#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Taiwan Weather Tracker - Core Script
Fetches weather forecast data from the Taiwan Central Weather Administration (CWA) Open Data Platform,
saves it in JSON format (both raw and simplified), and hosts a dashboard to visualize it.
"""

import os
import json
import argparse
import datetime
import urllib.request
import urllib.error
import http.server
import socketserver
import webbrowser
from pathlib import Path

# Constants
DEFAULT_CONFIG_FILE = "config.json"
DEFAULT_DATASET = "F-C0032-001" # 36h weather forecast for counties/cities
API_URL_TEMPLATE = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/{dataset_id}"

DEFAULT_CONFIG = {
    "cwa_api_key": "YOUR_CWA_API_KEY_HERE",
    "output_dir": "data",
    "datasets": [DEFAULT_DATASET],
    "server_port": 8000
}

def setup_config():
    """Create default config file if it does not exist."""
    if not os.path.exists(DEFAULT_CONFIG_FILE):
        print(f"[*] Creating default configuration file: {DEFAULT_CONFIG_FILE}")
        with open(DEFAULT_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
        print("[!] Please edit 'config.json' and fill in your Central Weather Administration API key (cwa_api_key).")
        print("[!] You can obtain a free API key at: https://opendata.cwa.gov.tw/")
        return DEFAULT_CONFIG
    
    try:
        with open(DEFAULT_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[!] Error reading config file: {e}")
        return DEFAULT_CONFIG

def get_api_key(config):
    """Retrieve API key from config or environment variable."""
    api_key = os.environ.get("CWA_API_KEY")
    if api_key:
        return api_key
    
    config_key = config.get("cwa_api_key")
    if config_key and config_key != "YOUR_CWA_API_KEY_HERE":
        return config_key
        
    return None

def fetch_data(dataset_id, api_key):
    """Fetch JSON data from CWA Open Data API."""
    url = API_URL_TEMPLATE.format(dataset_id=dataset_id)
    # CWA API expects Authorization in query parameters or headers.
    # We will pass it as a query parameter.
    query_url = f"{url}?Authorization={api_key}&format=JSON"
    
    print(f"[*] Fetching dataset '{dataset_id}' from CWA Open Data Platform...")
    
    req = urllib.request.Request(
        query_url, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) WeatherTracker/1.0'}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.status == 200:
                raw_data = response.read().decode('utf-8')
                return json.loads(raw_data)
            else:
                print(f"[!] API request failed with status code: {response.status}")
                return None
    except urllib.error.HTTPError as e:
        print(f"[!] HTTP Error {e.code}: {e.reason}")
        # Try reading response body for error details
        try:
            error_details = e.read().decode('utf-8')
            print(f"[!] Error response details: {error_details}")
        except Exception:
            pass
        return None
    except urllib.error.URLError as e:
        print(f"[!] Connection Error: {e.reason}")
        return None
    except Exception as e:
        print(f"[!] Unexpected error during fetch: {e}")
        return None

def save_raw_json(dataset_id, data, output_dir, timestamp):
    """Save raw JSON payload to a timestamped file for archival purposes."""
    date_str = timestamp.strftime("%Y-%m-%d")
    time_str = timestamp.strftime("%H%M%S")
    
    # Path: data/raw/{dataset_id}/{YYYY-MM-DD}/raw_{HHMMSS}.json
    raw_dir = Path(output_dir) / "raw" / dataset_id / date_str
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = raw_dir / f"raw_{time_str}.json"
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[+] Saved raw JSON data to: {file_path}")
        return file_path
    except Exception as e:
        print(f"[!] Failed to save raw JSON: {e}")
        return None

def parse_forecast_36h(raw_data):
    """
    Parses F-C0032-001 (今明36小時天氣預報) JSON into a clean, flat format.
    """
    try:
        if not raw_data or not raw_data.get("success") == "true":
            print("[!] Raw data indicates failure or is empty.")
            return None
            
        records = raw_data.get("records", {})
        locations = records.get("location", [])
        
        parsed_locations = {}
        
        # Each location represents a city/county (e.g. 臺北市)
        for loc in locations:
            loc_name = loc.get("locationName")
            weather_elements = loc.get("weatherElement", [])
            
            # We want to extract for each of the 3 time slots:
            # Wx (天氣現象), PoP (降雨機率), MinT (最低溫), MaxT (最高溫), CI (舒適度)
            # The time slots are consistent across elements, typically 3 slots.
            time_slots = []
            
            # Let's pivot the data by time slot
            # Find the time structures first from Wx (first element)
            if not weather_elements:
                continue
                
            element_map = {el.get("elementName"): el.get("time", []) for el in weather_elements}
            
            # We assume there are 3 time slots in the first element
            wx_times = element_map.get("Wx", [])
            num_slots = len(wx_times)
            
            for i in range(num_slots):
                slot_time = wx_times[i]
                start_time = slot_time.get("startTime")
                end_time = slot_time.get("endTime")
                
                # Helper function to get element parameter for slot index i
                def get_element_info(element_name):
                    times = element_map.get(element_name, [])
                    if len(times) > i:
                        param = times[i].get("parameter", {})
                        return {
                            "name": param.get("parameterName"),
                            "value": param.get("parameterValue"), # Code value, if available
                            "unit": param.get("parameterUnit")
                        }
                    return {"name": None, "value": None, "unit": None}
                
                wx_info = get_element_info("Wx")
                pop_info = get_element_info("PoP")
                min_t_info = get_element_info("MinT")
                max_t_info = get_element_info("MaxT")
                ci_info = get_element_info("CI")
                
                time_slots.append({
                    "start_time": start_time,
                    "end_time": end_time,
                    "weather_phenomenon": wx_info["name"],
                    "weather_code": wx_info["value"], # Useful for selecting icons
                    "rain_probability": pop_info["name"], # Percentage string e.g. "30"
                    "min_temp": min_t_info["name"],
                    "max_temp": max_t_info["name"],
                    "comfort_index": ci_info["name"]
                })
                
            parsed_locations[loc_name] = time_slots
            
        summary = {
            "dataset_id": DEFAULT_DATASET,
            "title": "台灣今明36小時天氣預報",
            "updated_at": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
            "locations": parsed_locations
        }
        return summary
    except Exception as e:
        print(f"[!] Error parsing 36h forecast data: {e}")
        import traceback
        traceback.print_exc()
        return None

def save_summary_json(summary_data, output_dir):
    """Save simplified summary JSON as a single weather.json file in the output directory."""
    file_path = Path(output_dir) / "weather.json"
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)
        print(f"[+] Updated weather data at: {file_path}")
        return file_path
    except Exception as e:
        print(f"[!] Failed to save weather JSON: {e}")
        return None

def serve_dashboard(port, output_dir):
    """Start a local web server to display the weather dashboard, automatically finding an available port if occupied."""
    # Custom handler to allow CORS and serve files
    class DashboardHTTPHandler(http.server.SimpleHTTPRequestHandler):
        def end_headers(self):
            # Enable CORS for local development
            self.send_header('Access-Control-Allow-Origin', '*')
            super().end_headers()
            
    socketserver.TCPServer.allow_reuse_address = True
    
    current_port = port
    max_attempts = 20
    httpd = None
    
    for attempt in range(max_attempts):
        try:
            httpd = socketserver.TCPServer(("", current_port), DashboardHTTPHandler)
            break
        except OSError as e:
            # WSAEADDRINUSE is 10048 on Windows, EADDRINUSE is 98 on Linux/macOS
            if "already in use" in str(e) or getattr(e, 'errno', None) in (98, 10048):
                print(f"[!] Port {current_port} is already in use. Trying port {current_port + 1}...")
                current_port += 1
            else:
                print(f"[!] Socket error: {e}")
                return
                
    if not httpd:
        print(f"[!] Failed to find an open port after {max_attempts} attempts.")
        return
        
    try:
        with httpd:
            print(f"[+] Dashboard is live!")
            print(f"[*] Opening browser to http://localhost:{current_port}/index.html ...")
            webbrowser.open(f"http://localhost:{current_port}/index.html")
            print("[*] Press Ctrl+C to stop the server.")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server stopped.")
    except Exception as e:
        print(f"[!] Failed to run dashboard server: {e}")

def run_fetch_pipeline(config, dataset_id=None):
    """Main pipeline to fetch, parse, and save weather data."""
    api_key = get_api_key(config)
    if not api_key:
        print("[!] CWA API Key is missing. Please configure it in config.json or set the CWA_API_KEY environment variable.")
        return False
        
    dataset = dataset_id or config.get("datasets", [DEFAULT_DATASET])[0]
    output_dir = config.get("output_dir", "data")
    
    now = datetime.datetime.now()
    
    # 1. Fetch raw data
    raw_data = fetch_data(dataset, api_key)
    if not raw_data:
        print("[!] Fetch failed. Aborting pipeline.")
        return False
        
    # 2. If it's the standard county forecast dataset, parse it to summary
    if dataset == DEFAULT_DATASET:
        summary = parse_forecast_36h(raw_data)
        if summary:
            save_summary_json(summary, output_dir)
            print("[+] Weather data pipeline completed successfully!")
            return True
        else:
            print("[!] Parsing failed.")
            return False
    else:
        print(f"[i] Dataset '{dataset}' parsing is not implemented. Doing nothing.")
        return True

def main():
    parser = argparse.ArgumentParser(description="Taiwan Weather Tracker CLI")
    parser.add_argument("--fetch", action="store_true", help="Fetch latest weather data from CWA API")
    parser.add_argument("--dataset", type=str, default=None, help=f"Specify dataset ID (default: {DEFAULT_DATASET})")
    parser.add_argument("--serve", action="store_true", help="Start the dashboard local web server")
    parser.add_argument("--port", type=int, default=None, help="Dashboard port (default from config or 8000)")
    parser.add_argument("--setup", action="store_true", help="Initialize or fix config.json")
    
    args = parser.parse_args()
    
    # Initialize configuration
    config = setup_config()
    
    # If setup flag is specified, we stop here
    if args.setup:
        print("[+] Setup complete. Please configure config.json before running.")
        return
        
    # Action handling
    action_taken = False
    
    if args.fetch:
        action_taken = True
        run_fetch_pipeline(config, args.dataset)
        
    if args.serve:
        action_taken = True
        port = args.port or config.get("server_port", 8000)
        output_dir = config.get("output_dir", "data")
        serve_dashboard(port, output_dir)
        
    if not action_taken:
        # Default behavior: run fetch, then exit. If user wants server, they run with --serve.
        print("[*] No action specified. Running weather data fetch pipeline...")
        success = run_fetch_pipeline(config, args.dataset)
        if success:
            print("\n[*] Tip: Run 'python weather_tracker.py --serve' to view the visual dashboard!")
            print("[*] Tip: Edit config.json to supply your CWA Open Data API key.")

if __name__ == "__main__":
    main()
