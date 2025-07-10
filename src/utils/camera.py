# src/utils/camera.py
import cv2
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class CameraManager:
    def __init__(self, index=0, width=1920, height=1080):
        self.camera = None
        self.index = index
        self.width = width
        self.height = height

    def get_camera(self):
        if self.camera and self.camera.isOpened():
            return self.camera

        try:
            self.camera = cv2.VideoCapture(self.index)
            if not self.camera.isOpened():
                logging.error(f"Failed to open camera at index {self.index}")
                self.camera = None
                return None

            # Set properties
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
            self.camera.set(cv2.CAP_PROP_AUTOFOCUS, 1)

            # Verify settings
            actual_width = self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
            fps = self.camera.get(cv2.CAP_PROP_FPS)
            logging.info(f"Camera initialized: {actual_width}x{actual_height} @ {fps} FPS")

            # Test frame read
            success, frame = self.camera.read()
            if not success or frame is None or not frame.any():
                logging.error("Initial frame read failed or returned empty frame")
                self.release()
                return None
            logging.info(f"Initial frame shape: {frame.shape}")
            return self.camera
        except Exception as e:
            logging.error(f"Error initializing camera: {e}")
            self.release()
            return None

    def release(self):
        if self.camera:
            self.camera.release()
            self.camera = None
            logging.info("Camera released")

    def __del__(self):
        self.release()

    @staticmethod
    def diagnose_camera_issues(max_devices=10):
        diagnostics = {"available_devices": [], "permissions": {}, "tips": []}
        for i in range(max_devices):
            device = f"/dev/video{i}"
            if os.path.exists(device):
                diagnostics["available_devices"].append(device)
                perms = os.stat(device)
                diagnostics["permissions"][device] = {
                    "readable": os.access(device, os.R_OK),
                    "writable": os.access(device, os.W_OK),
                }
        if not diagnostics["available_devices"]:
            diagnostics["tips"].append("No video devices found. Check USB connections.")
        return diagnostics