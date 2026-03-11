# IntelliPark Improvement Action Plan

**Goal:** Transform this college project into a production-ready portfolio piece.

**Time Estimate:** 6-8 weeks (working 1-2 hours/day)

---

## Project Structure (Target)

```
IntelliPark/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py          # Configuration management
│   │   ├── models.py          # Database models
│   │   ├── routes/
│   │   │   ├── auth.py        # Login/Register endpoints
│   │   │   ├── parking.py     # Parking CRUD endpoints
│   │   │   └── booking.py     # Booking endpoints
│   │   ├── services/
│   │   │   ├── detection.py   # YOLO detection logic
│   │   │   └── parking.py     # Parking business logic
│   │   └── utils/
│   │       ├── auth.py        # JWT helpers
│   │       └── validators.py  # Input validation
│   ├── requirements.txt
│   ├── .env.example
│   └── run.py
├── frontend/
│   ├── index.html
│   ├── css/
│   ├── js/
│   └── assets/
├── detection/
│   ├── detector.py            # Refactored detection script
│   ├── config.yaml            # Detection configuration
│   └── models/
│       └── yolo11s.pt
├── docker-compose.yml
├── Dockerfile
├── README.md
└── .gitignore
```

---

## Phase 1: Foundation (Week 1)

### Day 1-2: Project Setup & Configuration

- [ ] **Create proper project structure**
  ```bash
  mkdir -p backend/app/routes backend/app/services backend/app/utils
  mkdir -p frontend/css frontend/js frontend/assets
  mkdir -p detection/models
  ```

- [ ] **Create configuration system**

  File: `backend/app/config.py`
  ```python
  import os
  from dotenv import load_dotenv

  load_dotenv()

  class Config:
      SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-change-in-production')
      DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///intellipark.db')
      JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', 24))
      CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:8000').split(',')
      DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
  ```

- [ ] **Create .env.example**
  ```
  SECRET_KEY=your-secret-key-here
  DATABASE_URL=sqlite:///intellipark.db
  JWT_EXPIRATION_HOURS=24
  CORS_ORIGINS=http://localhost:8000
  DEBUG=True
  ```

- [ ] **Update .gitignore**
  ```
  .env
  __pycache__/
  *.pyc
  *.db
  .venv/
  venv/
  *.pt
  node_modules/
  ```

### Day 3-4: Database Setup

- [ ] **Install dependencies**
  ```bash
  pip install flask flask-sqlalchemy flask-cors python-dotenv pyjwt bcrypt
  ```

- [ ] **Create database models**

  File: `backend/app/models.py`
  ```python
  from flask_sqlalchemy import SQLAlchemy
  from datetime import datetime

  db = SQLAlchemy()

  class User(db.Model):
      id = db.Column(db.Integer, primary_key=True)
      email = db.Column(db.String(120), unique=True, nullable=False)
      password_hash = db.Column(db.String(256), nullable=False)
      name = db.Column(db.String(100), nullable=False)
      phone = db.Column(db.String(20))
      created_at = db.Column(db.DateTime, default=datetime.utcnow)
      bookings = db.relationship('Booking', backref='user', lazy=True)

  class ParkingSpace(db.Model):
      id = db.Column(db.Integer, primary_key=True)
      name = db.Column(db.String(50), nullable=False)
      location = db.Column(db.String(100), nullable=False)
      coordinates = db.Column(db.JSON, nullable=False)  # Polygon points
      is_occupied = db.Column(db.Boolean, default=False)
      hourly_rate = db.Column(db.Float, default=50.0)
      created_at = db.Column(db.DateTime, default=datetime.utcnow)
      bookings = db.relationship('Booking', backref='space', lazy=True)

  class Booking(db.Model):
      id = db.Column(db.Integer, primary_key=True)
      user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
      space_id = db.Column(db.Integer, db.ForeignKey('parking_space.id'), nullable=False)
      start_time = db.Column(db.DateTime, nullable=False)
      end_time = db.Column(db.DateTime, nullable=False)
      total_amount = db.Column(db.Float, nullable=False)
      status = db.Column(db.String(20), default='pending')  # pending, confirmed, completed, cancelled
      created_at = db.Column(db.DateTime, default=datetime.utcnow)
  ```

### Day 5-6: Authentication System

- [ ] **Create auth utilities**

  File: `backend/app/utils/auth.py`
  ```python
  import jwt
  import bcrypt
  from datetime import datetime, timedelta
  from functools import wraps
  from flask import request, jsonify, current_app

  def hash_password(password: str) -> str:
      return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

  def verify_password(password: str, password_hash: str) -> bool:
      return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

  def generate_token(user_id: int) -> str:
      payload = {
          'user_id': user_id,
          'exp': datetime.utcnow() + timedelta(hours=current_app.config['JWT_EXPIRATION_HOURS'])
      }
      return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

  def decode_token(token: str) -> dict:
      try:
          return jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
      except jwt.ExpiredSignatureError:
          return None
      except jwt.InvalidTokenError:
          return None

  def token_required(f):
      @wraps(f)
      def decorated(*args, **kwargs):
          token = request.headers.get('Authorization', '').replace('Bearer ', '')
          if not token:
              return jsonify({'error': 'Token required'}), 401

          payload = decode_token(token)
          if not payload:
              return jsonify({'error': 'Invalid or expired token'}), 401

          request.user_id = payload['user_id']
          return f(*args, **kwargs)
      return decorated
  ```

- [ ] **Create auth routes**

  File: `backend/app/routes/auth.py`
  ```python
  from flask import Blueprint, request, jsonify
  from app.models import db, User
  from app.utils.auth import hash_password, verify_password, generate_token, token_required

  auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

  @auth_bp.route('/register', methods=['POST'])
  def register():
      data = request.get_json()

      # Validation
      required = ['email', 'password', 'name']
      if not all(field in data for field in required):
          return jsonify({'error': 'Missing required fields'}), 400

      # Check if user exists
      if User.query.filter_by(email=data['email']).first():
          return jsonify({'error': 'Email already registered'}), 409

      # Create user
      user = User(
          email=data['email'],
          password_hash=hash_password(data['password']),
          name=data['name'],
          phone=data.get('phone')
      )
      db.session.add(user)
      db.session.commit()

      token = generate_token(user.id)
      return jsonify({'token': token, 'user': {'id': user.id, 'name': user.name, 'email': user.email}}), 201

  @auth_bp.route('/login', methods=['POST'])
  def login():
      data = request.get_json()

      if not data.get('email') or not data.get('password'):
          return jsonify({'error': 'Email and password required'}), 400

      user = User.query.filter_by(email=data['email']).first()
      if not user or not verify_password(data['password'], user.password_hash):
          return jsonify({'error': 'Invalid credentials'}), 401

      token = generate_token(user.id)
      return jsonify({'token': token, 'user': {'id': user.id, 'name': user.name, 'email': user.email}})

  @auth_bp.route('/me', methods=['GET'])
  @token_required
  def get_current_user():
      user = User.query.get(request.user_id)
      if not user:
          return jsonify({'error': 'User not found'}), 404
      return jsonify({'id': user.id, 'name': user.name, 'email': user.email, 'phone': user.phone})
  ```

### Day 7: Main App Setup

- [ ] **Create main application**

  File: `backend/app/__init__.py`
  ```python
  from flask import Flask
  from flask_cors import CORS
  from app.config import Config
  from app.models import db

  def create_app():
      app = Flask(__name__)
      app.config.from_object(Config)

      # Initialize extensions
      db.init_app(app)
      CORS(app, origins=Config.CORS_ORIGINS)

      # Register blueprints
      from app.routes.auth import auth_bp
      from app.routes.parking import parking_bp
      from app.routes.booking import booking_bp

      app.register_blueprint(auth_bp)
      app.register_blueprint(parking_bp)
      app.register_blueprint(booking_bp)

      # Create tables
      with app.app_context():
          db.create_all()

      return app
  ```

  File: `backend/run.py`
  ```python
  from app import create_app

  app = create_app()

  if __name__ == '__main__':
      app.run(debug=True, port=5000)
  ```

---

## Phase 2: Core Features (Week 2-3)

### Day 8-9: Parking API

- [ ] **Create parking routes**

  File: `backend/app/routes/parking.py`
  ```python
  from flask import Blueprint, request, jsonify
  from app.models import db, ParkingSpace
  from app.utils.auth import token_required

  parking_bp = Blueprint('parking', __name__, url_prefix='/api/parking')

  @parking_bp.route('/spaces', methods=['GET'])
  def get_spaces():
      location = request.args.get('location')
      query = ParkingSpace.query

      if location:
          query = query.filter_by(location=location)

      spaces = query.all()
      return jsonify([{
          'id': s.id,
          'name': s.name,
          'location': s.location,
          'is_occupied': s.is_occupied,
          'hourly_rate': s.hourly_rate
      } for s in spaces])

  @parking_bp.route('/spaces/<int:space_id>', methods=['GET'])
  def get_space(space_id):
      space = ParkingSpace.query.get_or_404(space_id)
      return jsonify({
          'id': space.id,
          'name': space.name,
          'location': space.location,
          'coordinates': space.coordinates,
          'is_occupied': space.is_occupied,
          'hourly_rate': space.hourly_rate
      })

  @parking_bp.route('/spaces/<int:space_id>/status', methods=['PUT'])
  def update_status(space_id):
      # This endpoint is called by the detection system
      data = request.get_json()
      space = ParkingSpace.query.get_or_404(space_id)
      space.is_occupied = data.get('is_occupied', space.is_occupied)
      db.session.commit()
      return jsonify({'success': True})

  @parking_bp.route('/status', methods=['GET'])
  def get_all_status():
      spaces = ParkingSpace.query.all()
      total = len(spaces)
      occupied = sum(1 for s in spaces if s.is_occupied)
      return jsonify({
          'total': total,
          'occupied': occupied,
          'available': total - occupied,
          'spaces': [{'id': s.id, 'name': s.name, 'is_occupied': s.is_occupied} for s in spaces]
      })
  ```

### Day 10-11: Booking System

- [ ] **Create booking routes**

  File: `backend/app/routes/booking.py`
  ```python
  from flask import Blueprint, request, jsonify
  from datetime import datetime
  from app.models import db, Booking, ParkingSpace, User
  from app.utils.auth import token_required

  booking_bp = Blueprint('booking', __name__, url_prefix='/api/bookings')

  @booking_bp.route('', methods=['POST'])
  @token_required
  def create_booking():
      data = request.get_json()

      # Validation
      required = ['space_id', 'start_time', 'end_time']
      if not all(field in data for field in required):
          return jsonify({'error': 'Missing required fields'}), 400

      space = ParkingSpace.query.get(data['space_id'])
      if not space:
          return jsonify({'error': 'Space not found'}), 404

      # Parse times
      try:
          start_time = datetime.fromisoformat(data['start_time'])
          end_time = datetime.fromisoformat(data['end_time'])
      except ValueError:
          return jsonify({'error': 'Invalid datetime format'}), 400

      if end_time <= start_time:
          return jsonify({'error': 'End time must be after start time'}), 400

      # Calculate amount
      hours = (end_time - start_time).total_seconds() / 3600
      total_amount = hours * space.hourly_rate

      # Check for conflicts
      conflict = Booking.query.filter(
          Booking.space_id == space.id,
          Booking.status.in_(['pending', 'confirmed']),
          Booking.start_time < end_time,
          Booking.end_time > start_time
      ).first()

      if conflict:
          return jsonify({'error': 'Time slot already booked'}), 409

      # Create booking
      booking = Booking(
          user_id=request.user_id,
          space_id=space.id,
          start_time=start_time,
          end_time=end_time,
          total_amount=total_amount,
          status='confirmed'
      )
      db.session.add(booking)
      db.session.commit()

      return jsonify({
          'id': booking.id,
          'space': space.name,
          'start_time': booking.start_time.isoformat(),
          'end_time': booking.end_time.isoformat(),
          'total_amount': booking.total_amount,
          'status': booking.status
      }), 201

  @booking_bp.route('', methods=['GET'])
  @token_required
  def get_user_bookings():
      bookings = Booking.query.filter_by(user_id=request.user_id).order_by(Booking.created_at.desc()).all()
      return jsonify([{
          'id': b.id,
          'space': b.space.name,
          'location': b.space.location,
          'start_time': b.start_time.isoformat(),
          'end_time': b.end_time.isoformat(),
          'total_amount': b.total_amount,
          'status': b.status
      } for b in bookings])

  @booking_bp.route('/<int:booking_id>/cancel', methods=['POST'])
  @token_required
  def cancel_booking(booking_id):
      booking = Booking.query.get_or_404(booking_id)

      if booking.user_id != request.user_id:
          return jsonify({'error': 'Not authorized'}), 403

      if booking.status == 'cancelled':
          return jsonify({'error': 'Already cancelled'}), 400

      if booking.start_time < datetime.utcnow():
          return jsonify({'error': 'Cannot cancel past bookings'}), 400

      booking.status = 'cancelled'
      db.session.commit()

      return jsonify({'success': True, 'status': booking.status})
  ```

### Day 12-14: Refactor Detection Script

- [ ] **Create clean detection service**

  File: `detection/detector.py`
  ```python
  import cv2
  import yaml
  import logging
  import requests
  from pathlib import Path
  from ultralytics import YOLO

  logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
  logger = logging.getLogger(__name__)

  class ParkingDetector:
      def __init__(self, config_path: str = 'config.yaml'):
          self.config = self._load_config(config_path)
          self.model = YOLO(self.config['model_path'])
          self.api_url = self.config['api_url']
          self.spaces = []

      def _load_config(self, path: str) -> dict:
          with open(path, 'r') as f:
              return yaml.safe_load(f)

      def load_spaces_from_api(self):
          try:
              response = requests.get(f"{self.api_url}/api/parking/spaces")
              response.raise_for_status()
              self.spaces = response.json()
              logger.info(f"Loaded {len(self.spaces)} parking spaces")
          except requests.RequestException as e:
              logger.error(f"Failed to load spaces: {e}")
              raise

      def update_space_status(self, space_id: int, is_occupied: bool):
          try:
              response = requests.put(
                  f"{self.api_url}/api/parking/spaces/{space_id}/status",
                  json={'is_occupied': is_occupied}
              )
              response.raise_for_status()
          except requests.RequestException as e:
              logger.error(f"Failed to update space {space_id}: {e}")

      def point_in_polygon(self, point: tuple, polygon: list) -> bool:
          x, y = point
          n = len(polygon)
          inside = False

          p1x, p1y = polygon[0]
          for i in range(1, n + 1):
              p2x, p2y = polygon[i % n]
              if y > min(p1y, p2y):
                  if y <= max(p1y, p2y):
                      if x <= max(p1x, p2x):
                          if p1y != p2y:
                              xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                          if p1x == p2x or x <= xinters:
                              inside = not inside
              p1x, p1y = p2x, p2y

          return inside

      def detect_vehicles(self, frame):
          results = self.model(frame, conf=self.config.get('confidence', 0.5), verbose=False)
          vehicles = []

          for result in results:
              for box in result.boxes:
                  if int(box.cls[0]) == 2:  # Car class
                      x1, y1, x2, y2 = map(int, box.xyxy[0])
                      center = ((x1 + x2) // 2, (y1 + y2) // 2)
                      vehicles.append({'box': (x1, y1, x2, y2), 'center': center})

          return vehicles

      def check_occupancy(self, vehicles: list):
          for space in self.spaces:
              coords = space.get('coordinates', [])
              if not coords:
                  continue

              is_occupied = False
              for vehicle in vehicles:
                  if self.point_in_polygon(vehicle['center'], coords):
                      is_occupied = True
                      break

              if space.get('is_occupied') != is_occupied:
                  self.update_space_status(space['id'], is_occupied)
                  space['is_occupied'] = is_occupied

      def process_frame(self, frame):
          vehicles = self.detect_vehicles(frame)
          self.check_occupancy(vehicles)
          return vehicles

      def run(self, video_source):
          cap = cv2.VideoCapture(video_source)

          if not cap.isOpened():
              logger.error(f"Failed to open video source: {video_source}")
              return

          self.load_spaces_from_api()
          frame_count = 0
          skip_frames = self.config.get('skip_frames', 2)

          logger.info("Starting detection loop...")

          try:
              while True:
                  ret, frame = cap.read()
                  if not ret:
                      logger.warning("Failed to read frame, reconnecting...")
                      cap.release()
                      cap = cv2.VideoCapture(video_source)
                      continue

                  frame_count += 1
                  if frame_count % skip_frames != 0:
                      continue

                  self.process_frame(frame)

          except KeyboardInterrupt:
              logger.info("Stopping detection...")
          finally:
              cap.release()

  if __name__ == '__main__':
      detector = ParkingDetector()
      detector.run(0)  # Use webcam or provide video URL
  ```

- [ ] **Create detection config**

  File: `detection/config.yaml`
  ```yaml
  model_path: models/yolo11s.pt
  api_url: http://localhost:5000
  confidence: 0.5
  skip_frames: 2
  resize_factor: 0.7
  vehicle_classes:
    - 2  # car
    - 5  # bus
    - 7  # truck
  ```

---

## Phase 3: Frontend Integration (Week 4-5)

### Day 15-17: JavaScript API Client

- [ ] **Create API client**

  File: `frontend/js/api.js`
  ```javascript
  const API_URL = 'http://localhost:5000/api';

  class ApiClient {
      constructor() {
          this.token = localStorage.getItem('token');
      }

      setToken(token) {
          this.token = token;
          localStorage.setItem('token', token);
      }

      clearToken() {
          this.token = null;
          localStorage.removeItem('token');
      }

      async request(endpoint, options = {}) {
          const headers = {
              'Content-Type': 'application/json',
              ...(this.token && { 'Authorization': `Bearer ${this.token}` })
          };

          try {
              const response = await fetch(`${API_URL}${endpoint}`, {
                  ...options,
                  headers: { ...headers, ...options.headers }
              });

              const data = await response.json();

              if (!response.ok) {
                  throw new Error(data.error || 'Request failed');
              }

              return data;
          } catch (error) {
              console.error('API Error:', error);
              throw error;
          }
      }

      // Auth
      async register(email, password, name, phone) {
          const data = await this.request('/auth/register', {
              method: 'POST',
              body: JSON.stringify({ email, password, name, phone })
          });
          this.setToken(data.token);
          return data;
      }

      async login(email, password) {
          const data = await this.request('/auth/login', {
              method: 'POST',
              body: JSON.stringify({ email, password })
          });
          this.setToken(data.token);
          return data;
      }

      logout() {
          this.clearToken();
          window.location.href = '/login.html';
      }

      async getProfile() {
          return this.request('/auth/me');
      }

      // Parking
      async getSpaces(location = null) {
          const query = location ? `?location=${encodeURIComponent(location)}` : '';
          return this.request(`/parking/spaces${query}`);
      }

      async getStatus() {
          return this.request('/parking/status');
      }

      // Bookings
      async createBooking(spaceId, startTime, endTime) {
          return this.request('/bookings', {
              method: 'POST',
              body: JSON.stringify({
                  space_id: spaceId,
                  start_time: startTime,
                  end_time: endTime
              })
          });
      }

      async getBookings() {
          return this.request('/bookings');
      }

      async cancelBooking(bookingId) {
          return this.request(`/bookings/${bookingId}/cancel`, {
              method: 'POST'
          });
      }
  }

  const api = new ApiClient();
  ```

### Day 18-19: Update Login/Register Pages

- [ ] **Update login.html script**
  ```javascript
  document.getElementById('loginForm').addEventListener('submit', async (e) => {
      e.preventDefault();

      const email = document.getElementById('email').value;
      const password = document.getElementById('password').value;
      const errorDiv = document.getElementById('error');

      try {
          await api.login(email, password);
          window.location.href = '/index.html';
      } catch (error) {
          errorDiv.textContent = error.message;
          errorDiv.style.display = 'block';
      }
  });
  ```

- [ ] **Update register.html script**
  ```javascript
  document.getElementById('registerForm').addEventListener('submit', async (e) => {
      e.preventDefault();

      const name = document.getElementById('name').value;
      const email = document.getElementById('email').value;
      const phone = document.getElementById('phone').value;
      const password = document.getElementById('password').value;
      const confirmPassword = document.getElementById('confirmPassword').value;
      const errorDiv = document.getElementById('error');

      if (password !== confirmPassword) {
          errorDiv.textContent = 'Passwords do not match';
          errorDiv.style.display = 'block';
          return;
      }

      try {
          await api.register(email, password, name, phone);
          window.location.href = '/index.html';
      } catch (error) {
          errorDiv.textContent = error.message;
          errorDiv.style.display = 'block';
      }
  });
  ```

### Day 20-21: Update Booking Flow

- [ ] **Connect parking search to API**
- [ ] **Implement booking creation**
- [ ] **Show user's bookings from database**
- [ ] **Add cancel booking functionality**

---

## Phase 4: Polish & Deploy (Week 6-8)

### Day 22-24: Error Handling & Validation

- [ ] **Add input validation**

  File: `backend/app/utils/validators.py`
  ```python
  import re

  def validate_email(email: str) -> bool:
      pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
      return bool(re.match(pattern, email))

  def validate_password(password: str) -> tuple[bool, str]:
      if len(password) < 8:
          return False, 'Password must be at least 8 characters'
      if not re.search(r'[A-Z]', password):
          return False, 'Password must contain uppercase letter'
      if not re.search(r'[0-9]', password):
          return False, 'Password must contain a number'
      return True, ''

  def validate_phone(phone: str) -> bool:
      pattern = r'^\+?[0-9]{10,15}$'
      return bool(re.match(pattern, phone.replace(' ', '').replace('-', '')))
  ```

- [ ] **Add global error handler**
  ```python
  @app.errorhandler(Exception)
  def handle_error(error):
      logger.error(f"Unhandled error: {error}")
      return jsonify({'error': 'Internal server error'}), 500
  ```

### Day 25-26: Logging

- [ ] **Add structured logging**
  ```python
  import logging

  logging.basicConfig(
      level=logging.INFO,
      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
      handlers=[
          logging.FileHandler('app.log'),
          logging.StreamHandler()
      ]
  )

  logger = logging.getLogger(__name__)
  ```

### Day 27-28: Docker Setup

- [ ] **Create Dockerfile**
  ```dockerfile
  FROM python:3.11-slim

  WORKDIR /app

  COPY backend/requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt

  COPY backend/ .

  EXPOSE 5000

  CMD ["python", "run.py"]
  ```

- [ ] **Create docker-compose.yml**
  ```yaml
  version: '3.8'

  services:
    backend:
      build: .
      ports:
        - "5000:5000"
      environment:
        - DATABASE_URL=postgresql://user:pass@db:5432/intellipark
        - SECRET_KEY=${SECRET_KEY}
      depends_on:
        - db

    db:
      image: postgres:15
      environment:
        - POSTGRES_USER=user
        - POSTGRES_PASSWORD=pass
        - POSTGRES_DB=intellipark
      volumes:
        - postgres_data:/var/lib/postgresql/data

    frontend:
      image: nginx:alpine
      ports:
        - "8000:80"
      volumes:
        - ./frontend:/usr/share/nginx/html

  volumes:
    postgres_data:
  ```

### Day 29-30: Documentation

- [ ] **Update README.md**
  ```markdown
  # IntelliPark

  AI-powered parking detection and management system.

  ## Features
  - Real-time parking space detection using YOLO
  - User authentication and booking system
  - RESTful API
  - Responsive web interface

  ## Tech Stack
  - Backend: Flask, SQLAlchemy, JWT
  - Frontend: HTML, CSS, JavaScript
  - AI: YOLOv11 (Ultralytics)
  - Database: PostgreSQL
  - Deployment: Docker

  ## Quick Start

  1. Clone the repository
  2. Copy `.env.example` to `.env` and configure
  3. Run with Docker:
     ```bash
     docker-compose up -d
     ```
  4. Access at http://localhost:8000

  ## API Documentation

  See [API.md](API.md) for endpoint documentation.
  ```

- [ ] **Create API.md with endpoint docs**

### Day 31+: Testing & Deployment

- [ ] **Write unit tests**
- [ ] **Write integration tests**
- [ ] **Set up CI/CD (GitHub Actions)**
- [ ] **Deploy to cloud (Railway/Render/AWS)**

---

## Checklist Summary

### Week 1: Foundation
- [ ] Project structure
- [ ] Configuration system
- [ ] Database models
- [ ] Authentication system

### Week 2-3: Core Features
- [ ] Parking API
- [ ] Booking system
- [ ] Detection refactor

### Week 4-5: Frontend
- [ ] API client
- [ ] Login/Register integration
- [ ] Booking flow
- [ ] Profile page

### Week 6-8: Polish
- [ ] Error handling
- [ ] Logging
- [ ] Docker
- [ ] Documentation
- [ ] Testing
- [ ] Deployment

---

## Skills You'll Demonstrate

After completing this:

| Skill | Evidence |
|-------|----------|
| Python | Flask API, YOLO integration |
| Database | SQLAlchemy, PostgreSQL |
| Authentication | JWT, password hashing |
| API Design | RESTful endpoints |
| Frontend | HTML/CSS/JS integration |
| DevOps | Docker, deployment |
| AI/ML | Computer vision, YOLO |
| Testing | Unit and integration tests |

**This becomes a strong portfolio project.**

---

## Notes

- Work on one section at a time
- Test each feature before moving on
- Commit frequently with clear messages
- Ask for help when stuck

Good luck! 頑張って！
