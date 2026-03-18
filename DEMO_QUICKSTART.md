# IntelliPark Demo Quick Start Guide

This guide will help you run the IntelliPark demo with simulated parking detection.

## Prerequisites

- Python 3.10+
- Node.js (optional, for serving frontend)

## Quick Start (3 Steps)

### Step 1: Start the Backend Server

```bash
cd backend
pip install -r requirements.txt
python run.py
```

The API will be available at: http://localhost:5000

### Step 2: Setup Demo Parking Spaces

In a new terminal:

```bash
cd detection
pip install requests
python demo_simulator.py --setup
```

This creates sample parking spaces in the database.

### Step 3: Open the Dashboard & Run Simulation

1. Open `frontend/dashboard.html` in your browser (double-click or use Live Server)

2. Start the simulation:
```bash
cd detection
python demo_simulator.py --simulate
```

You should now see parking spaces updating in real-time on the dashboard!

## Simulation Options

```bash
# Faster updates (every 1 second)
python demo_simulator.py --simulate --interval 1

# Higher activity (50% chance of change per space)
python demo_simulator.py --simulate --probability 0.5

# Run for 60 seconds only
python demo_simulator.py --simulate --duration 60

# Combine options
python demo_simulator.py --simulate --interval 2 --probability 0.4 --duration 120
```

## Using Real Detection (With YOLO)

If you have ultralytics installed and want to use actual video detection:

### 1. Install YOLO Dependencies

```bash
pip install ultralytics torch
```

Note: On Windows, you may need to enable Long Paths. Run as Administrator:
```powershell
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

### 2. Run Detection on a Video File

```bash
cd detection
python detector.py --source path/to/parking_video.mp4 --speed 0.25
```

### 3. Run Detection on Webcam

```bash
python detector.py --source 0
```

## Dashboard Features

- **Real-time Updates**: WebSocket connection shows live parking status
- **Occupancy Statistics**: Total, available, occupied spaces with percentages
- **Visual Parking Map**: Color-coded spaces (green = available, red = occupied)
- **Activity Feed**: Recent status changes with timestamps
- **Detection Logs**: System logs for debugging

## Troubleshooting

### "Cannot connect to API"
- Make sure the backend is running: `cd backend && python run.py`
- Check if port 5000 is available

### "No parking spaces found"
- Run the setup: `python demo_simulator.py --setup`

### CORS errors in browser
- The backend has CORS enabled for localhost by default
- If using a different origin, set `CORS_ORIGINS` environment variable

### Dashboard shows "Offline"
- Refresh the page
- Check browser console for WebSocket errors
- Ensure backend has Flask-SocketIO installed
