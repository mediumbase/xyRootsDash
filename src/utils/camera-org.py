import cv2

def get_camera():
    """Initialize the USB camera."""
    try:
        camera = cv2.VideoCapture(0)  # Use the default camera (index 0)
        if not camera.isOpened():
            print("Error: Could not open camera.")
            return None
        print("USB Camera initialized successfully!")
        return camera
    except Exception as e:
        print(f"Error initializing USB Camera: {e}")
        return None