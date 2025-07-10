import cv2
import numpy as np
import os
import threading
import time
import logging
from datetime import datetime
from .plant_growth import get_rgb

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Settings
TIMELAPSE_DIR = os.path.expanduser("/BASE/dev_inference/dashboard/media/timelapse")
os.makedirs(TIMELAPSE_DIR, exist_ok=True)
VIEW_WIDTH, VIEW_HEIGHT = 640, 480

# Global state
timelapse_thread = None
timelapse_running = False
timelapse_lock = threading.Lock()

def capture_single_photo():
    """Capture a single photo from the Kinect RGB feed."""
    try:
        rgb = get_rgb()
        if rgb is None or rgb.shape != (VIEW_HEIGHT, VIEW_WIDTH, 3):
            logging.error("Failed to capture photo: Invalid RGB data")
            return None
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        photo_path = os.path.join(TIMELAPSE_DIR, f"photo_{timestamp}.jpg")
        cv2.imwrite(photo_path, rgb)
        logging.info(f"Photo captured: {photo_path}")
        return photo_path
    except Exception as e:
        logging.error(f"Error capturing photo: {e}")
        return None

def timelapse_capture(interval, num_images):
    """Capture photos at specified intervals for a timelapse."""
    global timelapse_running
    with timelapse_lock:
        if timelapse_running:
            logging.warning("Timelapse already running")
            return
        timelapse_running = True
    try:
        for i in range(num_images):
            if not timelapse_running:
                break
            photo_path = capture_single_photo()
            if photo_path is None:
                logging.warning("Skipping timelapse frame due to capture failure")
            time.sleep(interval)
        logging.info("Timelapse capture completed")
    except Exception as e:
        logging.error(f"Timelapse capture error: {e}")
    finally:
        with timelapse_lock:
            timelapse_running = False

def start_timelapse(interval, num_images):
    """Start a timelapse in a separate thread."""
    global timelapse_thread
    with timelapse_lock:
        if timelapse_running:
            return {"error": "Timelapse already running"}
        timelapse_thread = threading.Thread(
            target=timelapse_capture,
            args=(interval, num_images),
            daemon=True
        )
        timelapse_thread.start()
        logging.info(f"Started timelapse: interval={interval}s, num_images={num_images}")
        return {"message": "Timelapse started"}