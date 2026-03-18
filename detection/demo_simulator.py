#!/usr/bin/env python3
"""
IntelliPark Demo Simulator

Simulates parking detection for demonstration purposes.
Creates sample parking spaces and randomly updates occupancy status
to demonstrate real-time dashboard updates.
"""

import requests
import random
import time
import logging
import argparse
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('DemoSimulator')

API_BASE_URL = 'http://localhost:5000'

# Demo parking configurations
DEMO_LOCATIONS = [
    {
        'name': 'Main Street Parking',
        'spaces': [
            {'name': 'A1', 'coordinates': [[100, 100], [200, 100], [200, 180], [100, 180]]},
            {'name': 'A2', 'coordinates': [[210, 100], [310, 100], [310, 180], [210, 180]]},
            {'name': 'A3', 'coordinates': [[320, 100], [420, 100], [420, 180], [320, 180]]},
            {'name': 'A4', 'coordinates': [[430, 100], [530, 100], [530, 180], [430, 180]]},
            {'name': 'B1', 'coordinates': [[100, 200], [200, 200], [200, 280], [100, 280]]},
            {'name': 'B2', 'coordinates': [[210, 200], [310, 200], [310, 280], [210, 280]]},
            {'name': 'B3', 'coordinates': [[320, 200], [420, 200], [420, 280], [320, 280]]},
            {'name': 'B4', 'coordinates': [[430, 200], [530, 200], [530, 280], [430, 280]]},
        ]
    },
    {
        'name': 'Downtown Garage - Level 1',
        'spaces': [
            {'name': 'L1-01', 'coordinates': [[50, 50], [130, 50], [130, 120], [50, 120]]},
            {'name': 'L1-02', 'coordinates': [[140, 50], [220, 50], [220, 120], [140, 120]]},
            {'name': 'L1-03', 'coordinates': [[230, 50], [310, 50], [310, 120], [230, 120]]},
            {'name': 'L1-04', 'coordinates': [[320, 50], [400, 50], [400, 120], [320, 120]]},
            {'name': 'L1-05', 'coordinates': [[50, 150], [130, 150], [130, 220], [50, 220]]},
            {'name': 'L1-06', 'coordinates': [[140, 150], [220, 150], [220, 220], [140, 220]]},
        ]
    },
    {
        'name': 'Shopping Mall Parking',
        'spaces': [
            {'name': 'P1', 'coordinates': [[80, 80], [160, 80], [160, 150], [80, 150]]},
            {'name': 'P2', 'coordinates': [[170, 80], [250, 80], [250, 150], [170, 150]]},
            {'name': 'P3', 'coordinates': [[260, 80], [340, 80], [340, 150], [260, 150]]},
            {'name': 'P4', 'coordinates': [[350, 80], [430, 80], [430, 150], [350, 150]]},
            {'name': 'P5', 'coordinates': [[440, 80], [520, 80], [520, 150], [440, 150]]},
        ]
    }
]


def get_auth_token() -> str:
    """Get admin auth token for API access."""
    try:
        # Try to login as admin
        response = requests.post(
            f'{API_BASE_URL}/api/auth/login',
            json={'email': 'admin@intellipark.com', 'password': 'admin123'},
            timeout=5
        )
        if response.ok:
            return response.json().get('token')
    except Exception as e:
        logger.debug(f"Auth not needed or failed: {e}")
    return None


def create_demo_spaces(location_index: int = 0) -> list:
    """
    Create demo parking spaces in the database.

    Args:
        location_index: Which demo location to use (0-2)

    Returns:
        List of created space IDs
    """
    location = DEMO_LOCATIONS[location_index % len(DEMO_LOCATIONS)]
    location_name = location['name']
    spaces = location['spaces']

    token = get_auth_token()
    headers = {'Authorization': f'Bearer {token}'} if token else {}

    created_ids = []

    logger.info(f"Creating {len(spaces)} demo parking spaces for '{location_name}'...")

    for space_data in spaces:
        try:
            payload = {
                'name': space_data['name'],
                'location': location_name,
                'space_type': 'standard',
                'hourly_rate': round(random.uniform(2.0, 5.0), 2),
                'coordinates': space_data['coordinates'],
                'is_occupied': random.choice([True, False])  # Random initial state
            }

            response = requests.post(
                f'{API_BASE_URL}/api/admin/parking-spaces',
                json=payload,
                headers=headers,
                timeout=5
            )

            if response.ok:
                space = response.json().get('space', response.json())
                space_id = space.get('id')
                if space_id:
                    created_ids.append(space_id)
                    logger.info(f"  Created space: {space_data['name']} (ID: {space_id})")
            elif response.status_code == 409:
                # Space already exists, try to get its ID
                logger.info(f"  Space {space_data['name']} already exists")
            else:
                logger.warning(f"  Failed to create {space_data['name']}: {response.status_code}")

        except Exception as e:
            logger.error(f"  Error creating space: {e}")

    return created_ids


def get_all_spaces() -> list:
    """Get all parking spaces from the API."""
    try:
        response = requests.get(f'{API_BASE_URL}/api/parking/spaces', timeout=5)
        if response.ok:
            return response.json().get('spaces', [])
    except Exception as e:
        logger.error(f"Failed to get spaces: {e}")
    return []


def update_space_status(space_id: int, is_occupied: bool, confidence: float = None):
    """Update a parking space's occupancy status."""
    try:
        payload = {'is_occupied': is_occupied}
        if confidence:
            payload['confidence'] = confidence

        response = requests.put(
            f'{API_BASE_URL}/api/parking/spaces/{space_id}/status',
            json=payload,
            timeout=5
        )
        return response.ok
    except Exception as e:
        logger.error(f"Failed to update space {space_id}: {e}")
        return False


def run_simulation(
    interval: float = 3.0,
    change_probability: float = 0.3,
    duration: int = None
):
    """
    Run the parking simulation.

    Args:
        interval: Seconds between updates
        change_probability: Probability (0-1) of changing a space's status each cycle
        duration: Total simulation duration in seconds (None for infinite)
    """
    logger.info("=" * 50)
    logger.info("IntelliPark Demo Simulation")
    logger.info("=" * 50)

    # Get existing spaces or create demo ones
    spaces = get_all_spaces()

    if not spaces:
        logger.info("No parking spaces found. Creating demo spaces...")
        create_demo_spaces(0)  # Main Street Parking
        create_demo_spaces(1)  # Downtown Garage
        spaces = get_all_spaces()

    if not spaces:
        logger.error("No parking spaces available. Is the backend running?")
        logger.error(f"Make sure the API is accessible at {API_BASE_URL}")
        return

    logger.info(f"Simulating {len(spaces)} parking spaces")
    logger.info(f"Update interval: {interval}s, Change probability: {change_probability}")
    logger.info("Press Ctrl+C to stop")
    logger.info("-" * 50)

    start_time = time.time()
    update_count = 0

    try:
        while True:
            # Check duration limit
            if duration and (time.time() - start_time) >= duration:
                logger.info(f"Simulation duration ({duration}s) reached")
                break

            # Randomly select spaces to update
            for space in spaces:
                if random.random() < change_probability:
                    # Toggle or randomize occupancy
                    current = space.get('is_occupied', False)
                    new_status = not current if random.random() < 0.7 else random.choice([True, False])

                    # Generate realistic confidence
                    confidence = round(random.uniform(0.75, 0.99), 2)

                    if update_space_status(space['id'], new_status, confidence):
                        status_str = "OCCUPIED" if new_status else "AVAILABLE"
                        logger.info(
                            f"[{datetime.now().strftime('%H:%M:%S')}] "
                            f"Space {space['name']}: {status_str} "
                            f"(confidence: {confidence:.0%})"
                        )
                        space['is_occupied'] = new_status
                        update_count += 1

            # Show summary periodically
            if update_count > 0 and update_count % 10 == 0:
                occupied = sum(1 for s in spaces if s.get('is_occupied', False))
                logger.info(
                    f"[Summary] {occupied}/{len(spaces)} spaces occupied "
                    f"({100 * occupied // len(spaces)}%)"
                )

            time.sleep(interval)

    except KeyboardInterrupt:
        logger.info("\nSimulation stopped by user")

    # Final summary
    elapsed = time.time() - start_time
    logger.info("-" * 50)
    logger.info(f"Simulation ended. Duration: {elapsed:.1f}s, Updates: {update_count}")


def setup_demo():
    """One-time setup: create demo parking spaces."""
    logger.info("Setting up demo environment...")

    # Check API connection
    try:
        response = requests.get(f'{API_BASE_URL}/api/health', timeout=5)
        if not response.ok:
            logger.error(f"API health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot connect to API at {API_BASE_URL}")
        logger.error("Please start the backend server first:")
        logger.error("  cd backend && python run.py")
        return False

    # Create spaces for all demo locations
    total_created = 0
    for i, location in enumerate(DEMO_LOCATIONS):
        created = create_demo_spaces(i)
        total_created += len(created)

    logger.info(f"\nSetup complete! Created {total_created} parking spaces.")
    logger.info("You can now:")
    logger.info("  1. Open the dashboard: frontend/dashboard.html")
    logger.info("  2. Run the simulation: python demo_simulator.py --simulate")

    return True


def main():
    parser = argparse.ArgumentParser(
        description='IntelliPark Demo Simulator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Setup demo parking spaces (run once)
  python demo_simulator.py --setup

  # Run simulation with default settings
  python demo_simulator.py --simulate

  # Run faster simulation (1 second interval)
  python demo_simulator.py --simulate --interval 1

  # Run for 60 seconds only
  python demo_simulator.py --simulate --duration 60

  # Higher activity (more changes)
  python demo_simulator.py --simulate --probability 0.5
        """
    )

    parser.add_argument(
        '--setup',
        action='store_true',
        help='Create demo parking spaces (run once)'
    )
    parser.add_argument(
        '--simulate',
        action='store_true',
        help='Run the parking simulation'
    )
    parser.add_argument(
        '--interval', '-i',
        type=float,
        default=3.0,
        help='Seconds between updates (default: 3)'
    )
    parser.add_argument(
        '--probability', '-p',
        type=float,
        default=0.3,
        help='Probability of status change per space per cycle (default: 0.3)'
    )
    parser.add_argument(
        '--duration', '-d',
        type=int,
        default=None,
        help='Simulation duration in seconds (default: infinite)'
    )
    parser.add_argument(
        '--api-url',
        default='http://localhost:5000',
        help='API base URL (default: http://localhost:5000)'
    )

    args = parser.parse_args()

    global API_BASE_URL
    API_BASE_URL = args.api_url

    if args.setup:
        setup_demo()
    elif args.simulate:
        run_simulation(
            interval=args.interval,
            change_probability=args.probability,
            duration=args.duration
        )
    else:
        # Default: setup + simulate
        if setup_demo():
            print("\nStarting simulation in 2 seconds...")
            time.sleep(2)
            run_simulation(
                interval=args.interval,
                change_probability=args.probability,
                duration=args.duration
            )


if __name__ == '__main__':
    main()
