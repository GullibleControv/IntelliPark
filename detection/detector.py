#!/usr/bin/env python3
"""
IntelliPark Parking Detection System

Uses YOLO for real-time vehicle detection and parking space occupancy monitoring.
Communicates with the IntelliPark API to update parking space status.
"""

import cv2
import yaml
import logging
import requests
import time
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('detection.log')
    ]
)
logger = logging.getLogger('ParkingDetector')


class ParkingDetector:
    """
    Parking space detection system using YOLO.

    This class handles:
    - Video stream capture
    - Vehicle detection using YOLO
    - Parking space occupancy determination
    - API communication for status updates
    """

    def __init__(self, config_path: str = 'config.yaml'):
        """Initialize the detector with configuration."""
        self.config = self._load_config(config_path)
        self.model = None
        self.spaces = []
        self.api_url = self.config.get('api_url', 'http://localhost:5000')

        # Initialize YOLO model
        self._init_model()

    def _load_config(self, path: str) -> dict:
        """Load configuration from YAML file."""
        config_file = Path(path)

        if not config_file.exists():
            logger.warning(f"Config file not found: {path}. Using defaults.")
            return self._default_config()

        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
                logger.info(f"Loaded configuration from {path}")
                return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return self._default_config()

    def _default_config(self) -> dict:
        """Return default configuration."""
        return {
            'model_path': 'models/yolo11s.pt',
            'confidence': 0.5,
            'skip_frames': 2,
            'resize_factor': 0.7,
            'api_url': 'http://localhost:5000',
            'vehicle_classes': [2, 3, 5, 7],  # car, motorcycle, bus, truck
            'log_level': 'INFO'
        }

    def _init_model(self):
        """Initialize the YOLO model."""
        try:
            from ultralytics import YOLO

            model_path = self.config.get('model_path', 'models/yolo11s.pt')

            # Check if model exists
            if not Path(model_path).exists():
                logger.info(f"Model not found at {model_path}. Downloading...")

            self.model = YOLO(model_path)
            logger.info(f"YOLO model loaded: {model_path}")

        except ImportError:
            logger.error("ultralytics not installed. Run: pip install ultralytics")
            raise
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            raise

    def load_spaces_from_api(self) -> bool:
        """Load parking spaces from the API."""
        try:
            response = requests.get(
                f"{self.api_url}/api/parking/spaces",
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            self.spaces = data.get('spaces', [])

            # Filter spaces with coordinates
            self.spaces = [s for s in self.spaces if s.get('coordinates')]

            logger.info(f"Loaded {len(self.spaces)} parking spaces with coordinates")
            return True

        except requests.RequestException as e:
            logger.error(f"Failed to load spaces from API: {e}")
            return False

    def update_space_status(self, space_id: int, is_occupied: bool, confidence: float = None):
        """Update parking space status via API."""
        try:
            payload = {'is_occupied': is_occupied}
            if confidence is not None:
                payload['confidence'] = confidence

            response = requests.put(
                f"{self.api_url}/api/parking/spaces/{space_id}/status",
                json=payload,
                timeout=5
            )
            response.raise_for_status()
            logger.debug(f"Updated space {space_id}: occupied={is_occupied}")

        except requests.RequestException as e:
            logger.warning(f"Failed to update space {space_id}: {e}")

    def point_in_polygon(self, point: Tuple[int, int], polygon: List[List[int]]) -> bool:
        """
        Check if a point is inside a polygon using ray casting algorithm.

        Args:
            point: (x, y) coordinates
            polygon: List of [x, y] coordinates forming the polygon

        Returns:
            True if point is inside polygon
        """
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

    def detect_vehicles(self, frame) -> List[Dict]:
        """
        Detect vehicles in a frame using YOLO.

        Args:
            frame: OpenCV image frame

        Returns:
            List of detected vehicles with bounding boxes and centers
        """
        confidence = self.config.get('confidence', 0.5)
        vehicle_classes = self.config.get('vehicle_classes', [2])

        results = self.model(frame, conf=confidence, verbose=False)
        vehicles = []

        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])

                if class_id in vehicle_classes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2
                    conf = float(box.conf[0])

                    vehicles.append({
                        'box': (x1, y1, x2, y2),
                        'center': (center_x, center_y),
                        'confidence': conf,
                        'class_id': class_id
                    })

        return vehicles

    def check_occupancy(self, vehicles: List[Dict]) -> Dict[int, bool]:
        """
        Check which parking spaces are occupied.

        Args:
            vehicles: List of detected vehicles

        Returns:
            Dictionary mapping space_id to occupancy status
        """
        occupancy = {}

        for space in self.spaces:
            space_id = space['id']
            coordinates = space.get('coordinates', [])

            if not coordinates or len(coordinates) < 3:
                continue

            is_occupied = False
            max_confidence = 0.0

            for vehicle in vehicles:
                if self.point_in_polygon(vehicle['center'], coordinates):
                    is_occupied = True
                    max_confidence = max(max_confidence, vehicle['confidence'])
                    break

            # Only update if status changed
            current_status = space.get('is_occupied', False)
            if current_status != is_occupied:
                self.update_space_status(space_id, is_occupied, max_confidence if is_occupied else None)
                space['is_occupied'] = is_occupied

            occupancy[space_id] = is_occupied

        return occupancy

    def draw_overlays(self, frame, vehicles: List[Dict], occupancy: Dict[int, bool]):
        """Draw detection overlays on the frame."""
        # Draw parking spaces
        for space in self.spaces:
            coordinates = space.get('coordinates', [])
            if not coordinates:
                continue

            points = [(int(p[0]), int(p[1])) for p in coordinates]
            is_occupied = occupancy.get(space['id'], False)

            color = (0, 0, 255) if is_occupied else (0, 255, 0)  # Red if occupied, green if free

            # Draw polygon
            for i in range(len(points)):
                cv2.line(frame, points[i], points[(i + 1) % len(points)], color, 2)

            # Draw label
            if points:
                label_pos = points[0]
                cv2.putText(frame, space['name'], label_pos, cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Draw vehicle bounding boxes
        for vehicle in vehicles:
            x1, y1, x2, y2 = vehicle['box']
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)

            # Draw center point
            cx, cy = vehicle['center']
            cv2.circle(frame, (cx, cy), 4, (0, 255, 255), -1)

        # Draw status
        total = len(self.spaces)
        occupied = sum(1 for v in occupancy.values() if v)
        status_text = f"Parking: {total - occupied}/{total} available"
        cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        return frame

    def process_frame(self, frame) -> Tuple[List[Dict], Dict[int, bool]]:
        """
        Process a single frame.

        Args:
            frame: OpenCV image frame

        Returns:
            Tuple of (detected vehicles, occupancy status)
        """
        # Resize frame if configured
        resize_factor = self.config.get('resize_factor', 1.0)
        if resize_factor != 1.0:
            frame = cv2.resize(frame, None, fx=resize_factor, fy=resize_factor)

        vehicles = self.detect_vehicles(frame)
        occupancy = self.check_occupancy(vehicles)

        return vehicles, occupancy

    def run(self, video_source=0, display: bool = True):
        """
        Run the detection loop.

        Args:
            video_source: Video source (0 for webcam, URL for stream, or file path)
            display: Whether to display the video with overlays
        """
        logger.info(f"Starting detection with source: {video_source}")

        # Load parking spaces
        if not self.load_spaces_from_api():
            logger.error("Failed to load parking spaces. Exiting.")
            return

        if len(self.spaces) == 0:
            logger.warning("No parking spaces with coordinates found. Please configure spaces first.")

        # Open video source
        cap = cv2.VideoCapture(video_source)

        if not cap.isOpened():
            logger.error(f"Failed to open video source: {video_source}")
            return

        frame_count = 0
        skip_frames = self.config.get('skip_frames', 2)

        logger.info("Detection loop started. Press 'q' to quit.")

        try:
            while True:
                ret, frame = cap.read()

                if not ret:
                    logger.warning("Failed to read frame. Attempting reconnect...")
                    cap.release()
                    time.sleep(2)
                    cap = cv2.VideoCapture(video_source)
                    continue

                frame_count += 1

                # Skip frames for performance
                if frame_count % skip_frames != 0:
                    continue

                # Process frame
                vehicles, occupancy = self.process_frame(frame)

                if display:
                    # Draw overlays
                    display_frame = self.draw_overlays(frame.copy(), vehicles, occupancy)

                    # Show frame
                    cv2.imshow('IntelliPark Detection', display_frame)

                    # Check for quit
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break

                # Log status periodically
                if frame_count % 100 == 0:
                    total = len(self.spaces)
                    occupied = sum(1 for v in occupancy.values() if v)
                    logger.info(f"Status: {occupied}/{total} occupied")

        except KeyboardInterrupt:
            logger.info("Detection stopped by user")

        finally:
            cap.release()
            if display:
                cv2.destroyAllWindows()
            logger.info("Detection loop ended")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='IntelliPark Parking Detection')
    parser.add_argument('--config', '-c', default='config.yaml', help='Config file path')
    parser.add_argument('--source', '-s', default='0', help='Video source (0 for webcam, URL, or file)')
    parser.add_argument('--no-display', action='store_true', help='Run without display')

    args = parser.parse_args()

    # Convert source to int if it's a number (webcam index)
    source = int(args.source) if args.source.isdigit() else args.source

    # Create detector and run
    detector = ParkingDetector(config_path=args.config)
    detector.run(video_source=source, display=not args.no_display)


if __name__ == '__main__':
    main()
