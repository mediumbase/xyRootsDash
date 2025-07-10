import cv2

def get_camera():
    """Initialize the ONN 1440P Webcam with minimal settings for real-time performance."""
    try:
        # Initialize the camera
        camera = cv2.VideoCapture(0)  # Use the default camera (index 0)
        if not camera.isOpened():
            print("Error: Could not open camera.")
            return None

        # Set camera properties for real-time performance
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)  # Lower resolution for speed (1280x720)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        camera.set(cv2.CAP_PROP_FPS, 30)  # Set frame rate to 30 FPS
        camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))  # Use MJPEG compression
        camera.set(cv2.CAP_PROP_AUTOFOCUS, 1)  # Enable autofocus

        print("ONN 1440P Webcam initialized successfully!")
        return camera
    except Exception as e:
        print(f"Error initializing camera: {e}")
        return None

def main():
    # Initialize the camera
    camera = get_camera()
    if camera is None:
        print("Failed to initialize camera.")
        return

    # Capture and display frames
    while True:
        ret, frame = camera.read()
        if not ret:
            print("Error: Could not read frame.")
            break

        # Display the frame
        cv2.imshow("ONN 1440P Webcam - Real-Time Feed", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):  # Press 'q' to exit
            break

    # Release the camera and close windows
    camera.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()