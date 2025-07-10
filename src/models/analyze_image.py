import cv2
import numpy as np
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Settings
ANALYSIS_DIR = os.path.expanduser("/BASE/dev_inference/dashboard/media/analysis")
os.makedirs(ANALYSIS_DIR, exist_ok=True)
VIEW_WIDTH, VIEW_HEIGHT = 640, 480

def analyze_image(image_path):
    """Analyze an image for basic features (e.g., green pixel count)."""
    try:
        if not os.path.exists(image_path):
            logging.error(f"Image not found: {image_path}")
            return None
        img = cv2.imread(image_path)
        if img is None or img.shape != (VIEW_HEIGHT, VIEW_WIDTH, 3):
            logging.error(f"Invalid image: {image_path}")
            return None
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        lower_green = np.array([35, 50, 50])
        upper_green = np.array([85, 255, 255])
        mask = cv2.inRange(hsv, lower_green, upper_green)
        green_pixels = cv2.countNonZero(mask)
        total_pixels = VIEW_WIDTH * VIEW_HEIGHT
        green_percentage = (green_pixels / total_pixels) * 100
        result = {
            "image_path": image_path,
            "green_percentage": green_percentage,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        logging.info(f"Image analyzed: {image_path}, green_percentage={green_percentage:.2f}%")
        return result
    except Exception as e:
        logging.error(f"Error analyzing image {image_path}: {e}")
        return None

def analyze_images():
    """Analyze all images in the timelapse directory."""
    try:
        results = []
        for filename in os.listdir(TIMELAPSE_DIR):
            if filename.endswith(".jpg"):
                image_path = os.path.join(TIMELAPSE_DIR, filename)
                result = analyze_image(image_path)
                if result:
                    results.append(result)
        if not results:
            logging.warning("No images analyzed")
            return {"error": "No images found for analysis"}
        output_path = os.path.join(ANALYSIS_DIR, f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        with open(output_path, 'w') as f:
            for result in results:
                f.write(f"{result['timestamp']}: {result['image_path']} - Green: {result['green_percentage']:.2f}%\n")
        logging.info(f"Analysis completed, results saved to {output_path}")
        return {"message": f"Analysis completed, results saved to {output_path}"}
    except Exception as e:
        logging.error(f"Error analyzing images: {e}")
        return {"error": str(e)}