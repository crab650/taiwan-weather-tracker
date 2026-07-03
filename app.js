// Taiwan Weather Tracker - Client JavaScript

// Region classification for filtering
const REGIONS = {
    north: ["臺北市", "新北市", "基隆市", "桃園市", "新竹市", "新竹縣", "宜蘭縣"],
    central: ["苗栗縣", "臺中市", "彰化縣", "南投縣", "雲林縣"],
    south: ["嘉義市", "嘉義縣", "臺南市", "高雄市", "屏東縣"],
    east: ["花蓮縣", "臺東縣"],
    islands: ["澎湖縣", "金門縣", "連江縣"]
};

// Global App State
let weatherData = null;
let currentSlotIndex = 0;
let currentRegion = "all";
let searchQuery = "";

// Weather SVG Icons mapping
function getWeatherIcon(code, phenomenonName) {
    const codeNum = parseInt(code) || 0;
    
    // SVG Styling
    const baseSvg = (path) => `<svg viewBox="0 0 24 24" width="64" height="64" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="fill: none; filter: drop-shadow(0 4px 6px rgba(0,0,0,0.15));">${path}</svg>`;
    
    // Color definitions in SVG strokes
    const sunColor = "#fbbf24";
    const cloudColor = "#94a3b8";
    const rainColor = "#3b82f6";
    const lightningColor = "#a855f7";
    const windColor = "#06b6d4";
    const snowColor = "#e2e8f0";
    
    // Sunny: 01
    if (codeNum === 1) {
        return baseSvg(`
            <circle cx="12" cy="12" r="5" stroke="${sunColor}" fill="${sunColor}" fill-opacity="0.2" />
            <line x1="12" y1="1" x2="12" y2="3" stroke="${sunColor}" />
            <line x1="12" y1="21" x2="12" y2="23" stroke="${sunColor}" />
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" stroke="${sunColor}" />
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" stroke="${sunColor}" />
            <line x1="1" y1="12" x2="3" y2="12" stroke="${sunColor}" />
            <line x1="21" y1="12" x2="23" y2="12" stroke="${sunColor}" />
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" stroke="${sunColor}" />
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" stroke="${sunColor}" />
        `);
    }
    
    // Mostly Sunny / Partly Cloudy: 02, 03
    if (codeNum === 2 || codeNum === 3) {
        return baseSvg(`
            <path d="M12 2a5 5 0 0 0-4.96 4.4 4.5 4.5 0 0 0-2 8.1 5 5 0 0 0 9.8 0 4.5 4.5 0 0 0-2.84-8.1A5 5 0 0 0 12 2z" stroke="${cloudColor}" fill="${cloudColor}" fill-opacity="0.1" />
            <path d="M16 11a4 4 0 1 1-4-4 4 4 0 0 1 4 4z" stroke="${sunColor}" fill="${sunColor}" fill-opacity="0.2" style="transform: translate(4px, -4px) scale(0.7);" />
        `);
    }
    
    // Cloudy / Overcast: 04, 05, 06, 07
    if (codeNum >= 4 && codeNum <= 7) {
        return baseSvg(`
            <path d="M20 17.58A5 5 0 0 0 18 8h-1.26A8 8 0 1 0 4 15.25" stroke="${cloudColor}" />
            <path d="M16 16.5a4 4 0 1 0-7.3-2A6 6 0 1 0 18 16.5z" stroke="${cloudColor}" fill="${cloudColor}" fill-opacity="0.1" />
        `);
    }
    
    // Shower / Light Rain: 08, 09, 10, 11, 12, 13, 14, 19, 20, 29, 30
    const lightRainCodes = [8, 9, 10, 11, 12, 13, 14, 19, 20, 29, 30, 31, 32, 38, 39];
    if (lightRainCodes.includes(codeNum) || phenomenonName.includes("雨") && !phenomenonName.includes("雷")) {
        return baseSvg(`
            <path d="M20 17.58A5 5 0 0 0 18 8h-1.26A8 8 0 1 0 4 15.25" stroke="${cloudColor}" fill="${cloudColor}" fill-opacity="0.1" />
            <line x1="8" y1="19" x2="6" y2="22" stroke="${rainColor}" />
            <line x1="12" y1="19" x2="10" y2="22" stroke="${rainColor}" />
            <line x1="16" y1="19" x2="14" y2="22" stroke="${rainColor}" />
        `);
    }
    
    // Thunderstorm: 15, 16, 17, 18, 21, 22, 33, 34, 35, 36, 41
    if (phenomenonName.includes("雷")) {
        return baseSvg(`
            <path d="M19 16.9A5 5 0 0 0 18 8h-1.26a8 8 0 1 0-11.62 8.58" stroke="${cloudColor}" fill="${cloudColor}" fill-opacity="0.1" />
            <polyline points="13 10 9 16 12 16 10 22 16 14 13 14 15 10" stroke="${lightningColor}" fill="${lightningColor}" fill-opacity="0.2" />
        `);
    }
    
    // Snowing / Ice: 23, 37, 42
    if (phenomenonName.includes("雪")) {
        return baseSvg(`
            <path d="M20 17.58A5 5 0 0 0 18 8h-1.26A8 8 0 1 0 4 15.25" stroke="${cloudColor}" />
            <line x1="8" y1="19" x2="8" y2="21" stroke="${snowColor}" />
            <line x1="12" y1="19" x2="12" y2="21" stroke="${snowColor}" />
            <line x1="16" y1="19" x2="16" y2="21" stroke="${snowColor}" />
            <circle cx="8" cy="20" r="1" fill="${snowColor}" />
            <circle cx="12" cy="20" r="1" fill="${snowColor}" />
            <circle cx="16" cy="20" r="1" fill="${snowColor}" />
        `);
    }
    
    // Wind / Fog / Others: 24, 25, 26, 27, 28
    return baseSvg(`
        <path d="M20 17.58A5 5 0 0 0 18 8h-1.26A8 8 0 1 0 4 15.25" stroke="${cloudColor}" fill="${cloudColor}" fill-opacity="0.05" />
        <path d="M1 18h22" stroke="${windColor}" opacity="0.6" />
        <path d="M3 14h18" stroke="${windColor}" opacity="0.4" />
        <path d="M5 21h14" stroke="${windColor}" opacity="0.8" />
    `);
}

// Helpers for region classification
function getCountyRegion(countyName) {
    for (const [region, counties] of Object.entries(REGIONS)) {
        if (counties.includes(countyName)) {
            return region;
        }
    }
    return "other";
}

function getRegionLabel(region) {
    switch (region) {
        case "north": return "北部地區";
        case "central": return "中部地區";
        case "south": return "南部地區";
        case "east": return "東部地區";
        case "islands": return "離島地區";
        default: return "其他";
    }
}

// Format the date/time string from CWA ISO format to readable text
function formatSlotLabel(startTimeStr, endTimeStr) {
    const start = new Date(startTimeStr);
    const end = new Date(endTimeStr);
    
    // Formats: "07/03 18:00 ~ 07/04 06:00"
    const startMD = `${start.getMonth() + 1}/${start.getDate()}`;
    const startTime = `${String(start.getHours()).padStart(2, '0')}:${String(start.getMinutes()).padStart(2, '0')}`;
    
    const endMD = `${end.getMonth() + 1}/${end.getDate()}`;
    const endTime = `${String(end.getHours()).padStart(2, '0')}:${String(end.getMinutes()).padStart(2, '0')}`;
    
    // Determine title (e.g. 今晚至明晨, 明日白天, 明日晚上)
    let periodTitle = "";
    const hours = start.getHours();
    
    if (hours === 6) {
        periodTitle = "白天";
    } else if (hours === 18) {
        periodTitle = "晚上";
    } else if (hours === 12) {
        periodTitle = "中午";
    } else {
        periodTitle = "預報";
    }
    
    // Add date context relative to today
    const today = new Date();
    const isToday = start.getDate() === today.getDate() && start.getMonth() === today.getMonth();
    const datePrefix = isToday ? "今日" : "明日";
    
    return {
        tabLabel: `${datePrefix}${periodTitle}`,
        timeRange: `${startMD} ${startTime} ~ ${endMD} ${endTime}`
    };
}

// Fetch the weather JSON data
async function loadWeatherData() {
    const grid = document.getElementById("weather-grid");
    
    try {
        // Fetch from the server served path
        const response = await fetch("data/weather.json");
        
        if (!response.ok) {
            throw new Error(`Data file not found (HTTP ${response.status})`);
        }
        
        weatherData = await response.json();
        setupDashboard();
        
    } catch (error) {
        console.warn("Weather data load failed. Displaying setup guide.", error);
        
        // Hide loader & normal controls, show setup guide
        grid.innerHTML = "";
        document.getElementById("dashboard-controls").classList.add("hidden");
        document.getElementById("status-panel").innerHTML = `
            <span class="pulse-indicator" style="background-color: #ef4444; box-shadow: 0 0 8px #ef4444;"></span>
            <span>連線中斷 / 尚無資料</span>
        `;
        document.getElementById("setup-notice").classList.remove("hidden");
    }
}

// Initialize the dashboard controls once data is loaded
function setupDashboard() {
    document.getElementById("setup-notice").classList.add("hidden");
    document.getElementById("dashboard-controls").classList.remove("hidden");
    
    // Update timestamp
    const updateTime = new Date(weatherData.updated_at);
    document.getElementById("update-time").textContent = `更新時間: ${updateTime.toLocaleDateString()} ${updateTime.toLocaleTimeString()}`;
    
    // Get time slots from first county
    const firstCounty = Object.keys(weatherData.locations)[0];
    const timeSlots = weatherData.locations[firstCounty];
    
    // Render time slot tabs
    const tabsContainer = document.getElementById("time-tabs");
    tabsContainer.innerHTML = "";
    
    timeSlots.forEach((slot, index) => {
        const formats = formatSlotLabel(slot.start_time, slot.end_time);
        
        const btn = document.createElement("button");
        btn.className = `time-tab ${index === currentSlotIndex ? 'active' : ''}`;
        btn.innerHTML = `
            <div style="font-weight: 700;">${formats.tabLabel}</div>
            <div style="font-size: 0.7rem; opacity: 0.7; margin-top: 2px;">${formats.timeRange}</div>
        `;
        btn.addEventListener("click", () => {
            // Set active class
            document.querySelectorAll(".time-tab").forEach(t => t.classList.remove("active"));
            btn.classList.add("active");
            
            currentSlotIndex = index;
            renderCards();
        });
        
        tabsContainer.appendChild(btn);
    });
    
    // Bind Event Listeners for Filters & Search
    const filterButtons = document.querySelectorAll(".filter-btn");
    filterButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            filterButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentRegion = btn.dataset.region;
            renderCards();
        });
    });
    
    const searchInput = document.getElementById("search-input");
    searchInput.addEventListener("input", (e) => {
        searchQuery = e.target.value.trim().toLowerCase();
        renderCards();
    });
    
    // Initial Render
    renderCards();
}

// Render the cards grid based on filters
function renderCards() {
    const grid = document.getElementById("weather-grid");
    grid.innerHTML = "";
    
    if (!weatherData || !weatherData.locations) return;
    
    let renderedCount = 0;
    
    for (const [locationName, slots] of Object.entries(weatherData.locations)) {
        // Filter by region
        const region = getCountyRegion(locationName);
        if (currentRegion !== "all" && region !== currentRegion) {
            continue;
        }
        
        // Filter by search query
        if (searchQuery && !locationName.toLowerCase().includes(searchQuery)) {
            continue;
        }
        
        // Get data for current slot
        const slotData = slots[currentSlotIndex];
        if (!slotData) continue;
        
        renderedCount++;
        
        // Create card element
        const card = document.createElement("div");
        card.className = "glass-card weather-card";
        
        // Build card HTML
        const rainPercent = parseInt(slotData.rain_probability) || 0;
        const regionLabel = getRegionLabel(region);
        
        card.innerHTML = `
            <div class="card-header">
                <h3 class="card-title">${locationName}</h3>
                <span class="card-badge">${regionLabel}</span>
            </div>
            <div class="card-body">
                <div class="weather-icon-wrapper">
                    ${getWeatherIcon(slotData.weather_code, slotData.weather_phenomenon)}
                </div>
                <div class="weather-desc">${slotData.weather_phenomenon}</div>
                <div class="temperature-display">
                    <span class="temp-val temp-low">${slotData.min_temp}<span class="temp-unit">°C</span></span>
                    <span class="temp-sep">~</span>
                    <span class="temp-val temp-high">${slotData.max_temp}<span class="temp-unit">°C</span></span>
                </div>
            </div>
            <div class="card-footer">
                <div class="info-item">
                    <span class="info-label">舒適度</span>
                    <span class="info-val">${slotData.comfort_index || "未知"}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">降雨機率</span>
                    <span class="info-val info-val-accent">
                        <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>
                        ${slotData.rain_probability}%
                    </span>
                </div>
                <div class="rain-bar-container">
                    <div class="rain-bar-header">
                        <span>降雨分佈</span>
                        <span>${rainPercent}%</span>
                    </div>
                    <div class="rain-bar-bg">
                        <div class="rain-bar-fill" style="width: ${rainPercent}%"></div>
                    </div>
                </div>
            </div>
        `;
        
        grid.appendChild(card);
    }
    
    // Render Empty State if no locations match filters
    if (renderedCount === 0) {
        grid.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🔍</div>
                <h3>無符合條件的縣市</h3>
                <p>試試看其他關鍵字，或者切換區域篩選器。</p>
            </div>
        `;
    }
}

// Bootstrap
document.addEventListener("DOMContentLoaded", loadWeatherData);
