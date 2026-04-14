# 🛰 ISRO — Operation Climate Shield
**Live weather + NASA fire data + cinematic UI**

---

## Project Structure

```
isro-project/
├── backend/
│   ├── app.py            ← Flask API server (your API keys are here)
│   └── requirements.txt  ← Python dependencies
└── frontend/
    └── index.html        ← Full cinematic app (open in browser)
```

---

## Setup & Run

### Step 1 — Install Python dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Step 2 — Start the Flask backend

```bash
python app.py
```

You should see:
```
🛰  ISRO Mission Control Backend — Starting on http://localhost:5000
```

### Step 3 — Open the frontend

Just open `frontend/index.html` in your browser.
(Double-click the file, or use VS Code Live Server)

---

## API Keys (already set in app.py)

| Service | Key |
|---------|-----|
| OpenWeather | `88bbf3f986ba60dfb9ccc618a2de715f` |
| NASA FIRMS | `dd02c75b937553e6edc1e3657ac758ab` |

---

## Live API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/weather/current?city=Mumbai` | Live weather for any city |
| `GET /api/weather/multi` | Weather for 10 major Indian cities |
| `GET /api/weather/forecast?city=Delhi` | 5-day forecast |
| `GET /api/aqi/{lat}/{lon}` | Air Quality Index |
| `GET /api/fires/india?days=1` | NASA FIRMS fire hotspots (last 24h) |
| `GET /api/fires/summary?days=1` | Fire count + FRP stats |
| `GET /api/health` | Server health check |

---

## Features

- 🌍 **3D rotating Earth** with orbiting satellites (Three.js)
- ✨ **Shooting star particles** — animated canvas
- 🌤 **Live weather** — search any city via OpenWeather API
- 📅 **5-day forecast** with precipitation probability
- 🌫 **Air Quality Index** with PM2.5, PM10, O₃, NO₂
- 🏙 **10 Indian cities** — live weather grid (click to expand)
- 🔥 **NASA FIRMS fire map** — real hotspots plotted on India map
- 📊 **Fire stats** — total count, high-confidence fires, FRP in MW
- 🔄 **Auto-refresh** every 5 min (weather) / 10 min (fires)
- 🎬 **Cinematic HUD** with live UTC clock & coordinates

---

## Troubleshooting

**"Cannot connect to backend"** → Make sure `python app.py` is running in the backend folder.

**CORS error** → Flask-CORS is already configured. Refresh after starting the server.

**No fire data** → NASA FIRMS free tier may have a short delay. Try `days=2` or `days=7`.

---

## Deploy To Vercel

This project can be deployed to Vercel using the Flask Python runtime.

### Before deploying

Set these environment variables in your Vercel project:

- `OPENWEATHER_API_KEY`
- `FIRMS_MAP_KEY`

### Deploy steps

1. Push this project to GitHub.
2. Import the repo into Vercel.
3. Vercel should detect it as a Python project automatically.
4. Add the two environment variables in Project Settings → Environment Variables.
5. Deploy.

### After deploy

- The site root `/` serves the frontend.
- The Flask API stays available at `/api/...`
- Example health check: `/api/health`
