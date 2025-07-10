import cv2
import numpy as np

def get_camera():
    """Initialize the ONN 1440P Webcam with optimal settings."""
    try:
        # Initialize the camera
        camera = cv2.VideoCapture(0)  # Use the default camera (index 0)
        if not camera.isOpened():
            print("Error: Could not open camera.")
            return None

        # Set camera properties for optimal performance
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 2560)  # Set resolution to 1440p (2560x1440)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1440)
        camera.set(cv2.CAP_PROP_FPS, 30)  # Set frame rate to 30 FPS
        camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))  # Use MJPEG compression
        camera.set(cv2.CAP_PROP_AUTOFOCUS, 1)  # Enable autofocus
        camera.set(cv2.CAP_PROP_BRIGHTNESS, 0.5)  # Adjust brightness for low-light correction
        camera.set(cv2.CAP_PROP_CONTRAST, 0.5)  # Adjust contrast for better image quality
        camera.set(cv2.CAP_PROP_SATURATION, 0.5)  # Adjust saturation for vibrant colors

        print("ONN 1440P Webcam initialized successfully!")
        return camera
    except Exception as e:
        print(f"Error initializing camera: {e}")
        return None

def calculate_sharpness(image):
    """Calculate the sharpness of an image using Laplacian variance."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()

def autofocus(camera, max_iterations=5, focus_step=20):
    """
    Perform fast autofocus by adjusting the camera's focus setting to maximize image sharpness.

    Args:
        camera: The camera object (cv2.VideoCapture).
        max_iterations: Maximum number of focus adjustments.
        focus_step: Step size for focus adjustments.

    Returns:
        best_focus: The focus value that produced the sharpest image.
        best_sharpness: The sharpness value of the best-focused image.
    """
    best_focus = 0
    best_sharpness = 0

    # Iterate through focus values
    for focus in range(0, 255, focus_step):
        # Set focus value
        camera.set(cv2.CAP_PROP_FOCUS, focus)

        # Capture a frame
        ret, frame = camera.read()
        if not ret:
            print("Error: Could not read frame.")
            break

        # Calculate sharpness
        sharpness = calculate_sharpness(frame)
        print(f"Focus: {focus}, Sharpness: {sharpness:.2f}")

        # Update best focus
        if sharpness > best_sharpness:
            best_sharpness = sharpness
            best_focus = focus

        # Display the frame (optional)
        cv2.imshow("Autofocus", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):  # Press 'q' to exit early
            break

    # Set the best focus value
    camera.set(cv2.CAP_PROP_FOCUS, best_focus)
    print(f"Best Focus: {best_focus}, Best Sharpness: {best_sharpness:.2f}")

    return best_focus, best_sharpness

def enhance_image(image):
    """Enhance the image by sharpening and adjusting contrast."""
    # Sharpen the image
    kernel = np.array([[0, -1, 0],
                       [-1, 5, -1],
                       [0, -1, 0]])
    sharpened = cv2.filter2D(image, -1, kernel)

    # Adjust contrast
    contrasted = cv2.convertScaleAbs(sharpened, alpha=1.5, beta=0)

    return contrasted

def main():
    # Initialize the camera
    camera = get_camera()
    if camera is None:
        print("Failed to initialize camera.")
        return

    # Run autofocus once at startup
    autofocus(camera)

    # Capture and display frames
    while True:
        ret, frame = camera.read()
        if not ret:
            print("Error: Could not read frame.")
            break

        # Enhance the frame
        enhanced_frame = enhance_image(frame)

        # Display the enhanced frame
        cv2.imshow("ONN 1440P Webcam - Enhanced Feed", enhanced_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):  # Press 'q' to exit
            break

    # Release the camera and close windows
    camera.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()