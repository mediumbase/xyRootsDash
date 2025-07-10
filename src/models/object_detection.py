import cv2
import numpy as np
import logging
from typing import List

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class ObjectDetector:
    def __init__(self):
        self.fgbg = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=16, detectShadows=False)

    def generate_frames(self, get_frame_func, last_detections: List) -> bytes:
        """Generate frames from a frame-fetching function (e.g., Kinect RGB feed)."""
        logging.info("Starting frame generation")
        while True:
            try:
                frame = get_frame_func()
                if frame is None or frame.size == 0 or not frame.any():
                    logging.error("Failed to read valid frame")
                    frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(frame, "No Frame", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

                # Background subtraction
                fgmask = self.fgbg.apply(frame)
                _, fgmask = cv2.threshold(fgmask, 127, 255, cv2.THRESH_BINARY)
                contours, _ = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                detected = False
                for contour in contours:
                    if cv2.contourArea(contour) > 500:
                        (x, y, w, h) = cv2.boundingRect(contour)
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        detected = True
                        last_detections.append({
                            "category": "motion",
                            "label": "Moving Object",
                            "confidence": float(cv2.contourArea(contour) / 1000)
                        })
                        cv2.putText(frame, f"Motion: Area {cv2.contourArea(contour):.0f}",
                                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                if not detected:
                    last_detections.append({
                        "category": "motion",
                        "label": "No Motion",
                        "confidence": 0.0
                    })

                ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
                if not ret:
                    logging.warning("Failed to encode frame")
                    continue
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            except Exception as e:
                logging.error(f"Frame generation error: {e}")
                break

        logging.info("Frame generation stopped")