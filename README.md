# IntelliPark - Smart Parking Solutions

AI-powered parking space detection and management system using YOLO computer vision.

## Features

- **Real-time Detection**: YOLO-based vehicle detection for parking occupancy monitoring
- **User Authentication**: JWT-based secure authentication system
- **Online Booking**: Reserve parking spaces in advance with conflict detection
- **Live Status**: Real-time parking availability dashboard
- **RESTful API**: Complete backend API for all operations

## Tech Stack

- **Backend**: Flask, SQLAlchemy, PostgreSQL, JWT
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **Detection**: YOLO (Ultralytics), OpenCV, Python
- **Deployment**: Docker, Nginx, Gunicorn

## Quick Start with Docker

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/IntelliPark.git
cd IntelliPark

# Start all services
docker-compose up --build

# Access the application
# Frontend: http://localhost:8000
# Backend API: http://localhost:5000
```

## Manual Setup

### Prerequisites

- Python 3.11+
- PostgreSQL (or SQLite for development)
- Node.js (optional, for frontend development)

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
# Edit .env with your configuration

# Run the server
python run.py
```

### Frontend Setup

The frontend is static HTML/CSS/JS. Serve it using any web server:

```bash
cd frontend

# Using Python's built-in server
python -m http.server 8000

# Or using Node's serve
npx serve -l 8000
```

### Detection System Setup

```bash
cd detection

# Install dependencies
pip install -r requirements.txt

# Download YOLO model (auto-downloaded on first run)
# Run detection
python detector.py --source 0  # Webcam
python detector.py --source video.mp4  # Video file
python detector.py --source rtsp://...  # RTSP stream
```

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
| `/api/parking/spaces` | POST | Create parking space (admin) |
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

### Example Requests

```bash
# Register
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "Password123", "name": "John"}'

# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "Password123"}'

# Get parking status
curl http://localhost:5000/api/parking/status

# Create booking (with token)
curl -X POST http://localhost:5000/api/bookings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"space_id": 1, "start_time": "2025-01-15T10:00:00", "end_time": "2025-01-15T12:00:00"}'
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key | dev-secret |
| `DATABASE_URL` | Database connection string | sqlite:///intellipark.db |
| `JWT_EXPIRATION_HOURS` | Token expiration time | 24 |
| `CORS_ORIGINS` | Allowed origins (comma-separated) | http://localhost:8000 |

## Project Structure

```
IntelliPark/
├── backend/
│   ├── app/
│   │   ├── models.py        # Database models
│   │   ├── config.py        # Configuration
│   │   ├── routes/          # API routes
│   │   └── utils/           # Utilities (auth, etc.)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── run.py
├── frontend/
│   ├── css/
│   ├── js/
│   │   ├── api.js           # API client
│   │   ├── auth.js          # Auth management
│   │   └── ...
│   ├── index.html
│   └── ...
├── detection/
│   ├── detector.py          # YOLO detection system
│   ├── config.yaml          # Detection config
│   └── requirements.txt
├── docker-compose.yml
├── nginx.conf
└── README.md
```

## Detection System

The detection system uses YOLO to detect vehicles in parking spaces.

### Configuration (detection/config.yaml)

```yaml
model_path: models/yolo11s.pt
confidence: 0.5
skip_frames: 2
resize_factor: 0.7
api_url: http://localhost:5000
vehicle_classes: [2, 3, 5, 7]  # car, motorcycle, bus, truck
```

### Adding Parking Spaces

1. Create parking spaces via API with polygon coordinates
2. Coordinates define the parking space boundaries
3. Detection system checks if vehicle centers fall within polygons

## Development

### Running Tests

```bash
cd backend
pytest
```

### Code Style

```bash
# Format Python code
black .

# Lint
flake8
```

## License

MIT License
