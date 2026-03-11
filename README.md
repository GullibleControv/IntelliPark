# IntelliPark - Smart Parking Solutions

AI-powered parking space detection and management system using YOLO computer vision.

## Features

- **Real-time Detection**: YOLO-based vehicle detection for parking occupancy monitoring
- **Admin Panel**: Visual interface to draw parking space polygons on video frames
- **YouTube Integration**: Use YouTube parking lot videos as detection sources
- **Video Slowdown**: Process timelapse videos at reduced speed for accurate detection
- **User Authentication**: JWT-based secure authentication system
- **Online Booking**: Reserve parking spaces in advance with conflict detection
- **Live Status**: Real-time parking availability dashboard
- **RESTful API**: Complete backend API for all operations

## Tech Stack

- **Backend**: Flask, SQLAlchemy, PostgreSQL, JWT
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **Detection**: YOLO (Ultralytics), OpenCV, Python
- **Video Processing**: yt-dlp, ffmpeg
- **Deployment**: Docker, Nginx, Gunicorn

---

## Quick Start with Docker

### 1. Clone and Configure

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/IntelliPark.git
cd IntelliPark

# Create environment file (required)
cp .env.example .env

# Edit .env and set your values:
# - DB_PASSWORD: Your database password (any secure string)
# - SECRET_KEY: Generate with: python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Start Services

```bash
docker-compose up --build -d
```

### 3. Access the Application

| Service | URL |
|---------|-----|
| Frontend | http://localhost:8080 |
| Admin Panel | http://localhost:8080/admin.html |
| Backend API | http://localhost:5000 |

### 4. Default Admin Login

```
Email: admin@intellipark.com
Password: Admin@123
```

---

## Step-by-Step Usage Guide

### Step 1: Configure Parking Spaces (Admin Panel)

1. Open http://localhost:8080/admin.html
2. Login with admin credentials
3. Enter a YouTube parking lot video URL (e.g., `https://www.youtube.com/watch?v=VIDEO_ID`)
4. Click **Extract Frame** to capture a frame from the video
5. **Draw parking spaces** by clicking on the canvas:
   - Click to add polygon points
   - Double-click or press **Enter** to complete a polygon
   - Press **Escape** to cancel current drawing
   - Click on a polygon to select it, then press **Delete** to remove
6. Click **Save All Spaces** to store the parking space coordinates

### Step 2: Run Detection System

```bash
cd detection

# Install dependencies (first time only)
pip install -r requirements.txt

# Run with YouTube video (auto-downloads)
python detector.py --source "https://www.youtube.com/watch?v=VIDEO_ID"

# For timelapse videos, slow them down (0.25 = 4x slower)
python detector.py --source "https://www.youtube.com/watch?v=VIDEO_ID" --speed 0.25

# Run with webcam
python detector.py --source 0

# Run with local video file
python detector.py --source path/to/video.mp4

# Run with RTSP stream (live camera)
python detector.py --source "rtsp://camera_ip:port/stream"
```

### Step 3: View Live Status

1. Open http://localhost:8080
2. The dashboard shows real-time parking availability
3. Green = Available, Red = Occupied

---

## Detection System

### Video Sources

The detection system supports multiple video sources:

| Source Type | Example |
|-------------|---------|
| Webcam | `--source 0` |
| YouTube URL | `--source "https://www.youtube.com/watch?v=..."` |
| Local File | `--source video.mp4` |
| RTSP Stream | `--source "rtsp://192.168.1.100:554/stream"` |

### Video Slowdown (For Timelapse Videos)

If your parking lot video is a timelapse (fast-paced), use the `--speed` option:

```bash
# 4x slower (recommended for timelapses)
python detector.py --source "https://www.youtube.com/watch?v=VIDEO_ID" --speed 0.25

# 2x slower
python detector.py --source "https://www.youtube.com/watch?v=VIDEO_ID" --speed 0.5

# 10x slower (very fast timelapses)
python detector.py --source "https://www.youtube.com/watch?v=VIDEO_ID" --speed 0.1
```

Videos are cached in `detection/video_cache/` to avoid re-downloading.

### Configuration (detection/config.yaml)

```yaml
# YOLO Model Settings
model_path: models/yolo11s.pt
confidence: 0.5

# Video Processing
skip_frames: 2          # Process every Nth frame
resize_factor: 0.7      # Resize for performance

# Video Slowdown (for timelapse videos)
playback_speed: 1.0     # 0.25 = 4x slower, 0.5 = 2x slower

# API Connection
api_url: http://localhost:5000

# Vehicle Classes (COCO dataset IDs)
vehicle_classes:
  - 2  # car
  - 3  # motorcycle
  - 5  # bus
  - 7  # truck
```

### Command Line Options

```bash
python detector.py --help

Options:
  --config, -c    Config file path (default: config.yaml)
  --source, -s    Video source (webcam index, URL, or file path)
  --speed         Playback speed (0.25 = 4x slower)
  --no-display    Run without video display (headless)
  --clear-cache   Clear downloaded video cache
```

---

## Manual Setup (Without Docker)

### Prerequisites

- Python 3.11+
- PostgreSQL (or SQLite for development)
- ffmpeg (for video processing)
- yt-dlp (for YouTube downloads)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your SECRET_KEY

# Run the server
python run.py
```

### Frontend Setup

```bash
cd frontend

# Using Python's built-in server
python -m http.server 8000

# Or using Node's serve
npx serve -l 8000
```

### Detection Setup

```bash
cd detection

# Install dependencies
pip install -r requirements.txt

# Install ffmpeg (required for video slowdown)
# Windows: choco install ffmpeg
# Mac: brew install ffmpeg
# Linux: sudo apt install ffmpeg

# Run detection
python detector.py --source 0
```

---

## API Documentation

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/register` | POST | Create new account |
| `/api/auth/login` | POST | Login and get JWT token |
| `/api/auth/me` | GET | Get current user profile |
| `/api/auth/me` | PUT | Update profile |
| `/api/auth/change-password` | POST | Change password |

### Parking

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/parking/spaces` | GET | List all parking spaces |
| `/api/parking/spaces` | POST | Create parking space |
| `/api/parking/spaces/:id/status` | PUT | Update space occupancy |
| `/api/parking/status` | GET | Get overall parking status |
| `/api/parking/locations` | GET | List unique locations |

### Bookings

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/bookings` | GET | List user's bookings |
| `/api/bookings` | POST | Create new booking |
| `/api/bookings/:id/cancel` | POST | Cancel booking |
| `/api/bookings/:id/start` | POST | Check-in to booking |
| `/api/bookings/:id/complete` | POST | Check-out from booking |

### Admin

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/admin/extract-frame` | POST | Extract frame from YouTube URL |
| `/api/admin/video-sources` | GET/POST | Manage video sources |
| `/api/admin/spaces/bulk` | POST | Create multiple spaces at once |
| `/api/admin/spaces-with-coordinates` | GET | Get spaces with polygon data |

### Example Requests

```bash
# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@intellipark.com", "password": "Admin@123"}'

# Get parking status
curl http://localhost:5000/api/parking/status

# Extract frame from YouTube (requires auth token)
curl -X POST http://localhost:5000/api/admin/extract-frame \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID"}'
```

---

## Project Structure

```
IntelliPark/
├── backend/
│   ├── app/
│   │   ├── __init__.py      # App factory, admin seeding
│   │   ├── models.py        # Database models
│   │   ├── config.py        # Configuration
│   │   ├── routes/
│   │   │   ├── auth.py      # Authentication endpoints
│   │   │   ├── parking.py   # Parking space endpoints
│   │   │   ├── booking.py   # Booking endpoints
│   │   │   └── admin.py     # Admin panel endpoints
│   │   └── utils/
│   │       ├── auth.py      # JWT & password utilities
│   │       └── validators.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── run.py
├── frontend/
│   ├── css/
│   │   ├── styles.css
│   │   └── admin.css
│   ├── js/
│   │   ├── api.js           # API client
│   │   ├── auth.js          # Auth management
│   │   ├── admin.js         # Admin panel logic
│   │   └── polygon-drawer.js # Canvas drawing
│   ├── index.html
│   ├── admin.html           # Admin panel
│   └── ...
├── detection/
│   ├── detector.py          # YOLO detection system
│   ├── config.yaml          # Detection config
│   ├── requirements.txt
│   └── video_cache/         # Downloaded videos
├── docker-compose.yml
├── nginx.conf
├── .env.example
└── README.md
```

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | JWT signing key | Yes |
| `DB_PASSWORD` | Database password | Yes (Docker) |
| `DATABASE_URL` | Database connection string | No (defaults to SQLite) |
| `JWT_EXPIRATION_HOURS` | Token expiration time | No (default: 24) |
| `CORS_ORIGINS` | Allowed origins | No |
| `ADMIN_EMAIL` | Default admin email | No |
| `ADMIN_PASSWORD` | Default admin password | No |

---

## Troubleshooting

### "No parking spaces with coordinates found"

Run the admin panel to draw parking spaces:
1. Go to http://localhost:8080/admin.html
2. Extract a frame from your video source
3. Draw parking space polygons
4. Save the spaces

### "Failed to download YouTube video"

- Ensure `yt-dlp` is installed: `pip install yt-dlp`
- Check if the video is available (not private/deleted)
- Try updating yt-dlp: `pip install -U yt-dlp`

### "ffmpeg not found" (Video slowdown)

Install ffmpeg:
- Windows: `choco install ffmpeg` or download from ffmpeg.org
- Mac: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

### Docker containers not starting

```bash
# Check logs
docker-compose logs

# Reset and rebuild
docker-compose down -v
docker-compose up --build
```

### Detection not updating parking status

- Verify the API URL in `detection/config.yaml`
- Check that parking spaces have valid coordinates
- Ensure the detection system can reach the backend API

---

## License

MIT License
