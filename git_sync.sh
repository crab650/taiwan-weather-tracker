#!/bin/bash
# Taiwan Weather Tracker - PythonAnywhere Git Sync Automation
# This script runs the crawler and commits/pushes changes to GitHub.

# Resolve the absolute path of the script directory
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "=== Weather Tracker Git Sync Start: $(date) ==="

# 1. Execute the Python crawler to get the latest weather.json
if [ -f "cwa_crawler_pa.py" ]; then
    python cwa_crawler_pa.py
else
    echo "[!] Error: cwa_crawler_pa.py not found in $DIR"
    exit 1
fi

# 2. Check if git is initialized
if [ ! -d ".git" ]; then
    echo "[!] Warning: Git repository not detected in $DIR."
    echo "[!] Please initialize git or clone your repo first. Skipping git push."
    exit 0
fi

# 3. Check if data/ folder has changed
STATUS=$(git status --porcelain data/)

if [ -n "$STATUS" ]; then
    echo "[*] Changes detected in weather data. Preparing to commit..."
    
    # Stage the weather data and the updated README
    git add data/ README.md
    
    # Commit with local timestamp
    git commit -m "Auto-update weather data and README: $(date +'%Y-%m-%d %H:%M:%S')"
    
    # Push to remote (usually origin main)
    # Note: Assumes SSH key or credential helper is configured on PythonAnywhere
    echo "[*] Pushing updates to GitHub..."
    git push origin main
    
    if [ $? -eq 0 ]; then
        echo "[+] Push successful!"
    else
        echo "[!] Error: Failed to push to GitHub. Check SSH keys or network connection."
    fi
else
    echo "[*] No changes detected in weather.json (weather forecast remains the same). Skipping git push."
fi

echo "=== Weather Tracker Git Sync Complete: $(date) ==="
echo ""
