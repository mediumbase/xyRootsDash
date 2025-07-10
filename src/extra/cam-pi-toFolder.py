from picamera import PiCamera
from time import sleep
import datetime
import os

# Create a folder to save images
output_folder = "/path/to/save/images"
os.makedirs(output_folder, exist_ok=True)

# Initialize the camera
camera = PiCamera()
camera.resolution = (1920, 1080)  # Set resolution
camera.start_preview()

# Capture images at regular intervals
for i in range(100):  # Capture 100 images
    sleep(3600)  # Wait 1 hour between captures
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    image_path = os.path.join(output_folder, f"image_{timestamp}.jpg")
    camera.capture(image_path)
    print(f"Saved {image_path}")

camera.stop_preview()