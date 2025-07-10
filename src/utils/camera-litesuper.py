import cv2

def get_camera():
    """Initialize the USB camera with optimized settings."""
    camera = cv2.VideoCapture(0)  # Use the default camera (index 0)
    if camera.isOpened():
        # Set optimized settings
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  # Lower resolution for speed
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        camera.set(cv2.CAP_PROP_FPS, 15)  # Lower frame rate for speed
        camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))  # Use MJPEG compression
        camera.set(cv2.CAP_PROP_AUTOFOCUS, 0)  # Disable autofocus
        return camera
    return None

# Initialize the camera
camera = get_camera()
if camera is None:
    print("Failed to initialize camera.")
    exit()

# Capture and display frames
while True:
    ret, frame = camera.read()
    if not ret:
        print("Error: Could not read frame.")
        break

    # Display the frame
    cv2.imshow("Optimized Camera Feed", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):  # Press 'q' to exit
        break

# Release the camera and close windows
camera.release()
cv2.destroyAllWindows()