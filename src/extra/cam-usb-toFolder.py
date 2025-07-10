import cv2
import datetime
import os

# Create a folder to save images
output_folder = "/path/to/save/images"
os.makedirs(output_folder, exist_ok=True)

# Initialize the webcam
cap = cv2.VideoCapture(0)

# Capture images at regular intervals
for i in range(100):  # Capture 100 images
    ret, frame = cap.read()
    if ret:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        image_path = os.path.join(output_folder, f"image_{timestamp}.jpg")
        cv2.imwrite(image_path, frame)
        print(f"Saved {image_path}")
    sleep(3600)  # Wait 1 hour between captures

cap.release()