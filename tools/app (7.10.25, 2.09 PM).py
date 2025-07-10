from flask import Flask, render_template, jsonify, Response, request
from collections import deque
from dotenv import load_dotenv
import random
import time
import matplotlib.pyplot as plt
import io
import os
import subprocess
import base64
import mariadb
from dbutils.pooled_db import PooledDB
from datetime import datetime, timedelta
from src.models.time_lapse import capture_single_photo
from src.models.analyze_image import analyze_image
from src.models.plant_growth import capture_snapshot, get_real_feed, get_stem_outline, generate_view3_image, get_snapshot_count
from src.models.object_detection import ObjectDetector
import cv2
import numpy as np
import threading
import logging

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

# Application configuration
app.config.update({
    'MYSQL_HOST': os.getenv('MYSQL_HOST'),
    'MYSQL_USER': os.getenv('MYSQL_USER'),
    'MYSQL_PASSWORD': os.getenv('MYSQL_PASSWORD'),
    'MYSQL_DB': os.getenv('MYSQL_DB'),
    'TIME_LAPSE_FOLDER': os.path.expanduser(os.getenv('TIME_LAPSE_FOLDER', '/BASE/dev_inference/dashboard/media/time_lapse')),
    'PLANT_SNAPSHOTS_FOLDER': os.path.expanduser(os.getenv('PLANT_SNAPSHOTS_FOLDER', '/BASE/dev_inference/dashboard/media/plant_snapshots')),
    'SECRET_KEY': os.getenv('SECRET_KEY'),
    'JPEG_QUALITY': int(os.getenv('JPEG_QUALITY', 95)),
})

# Validate required environment variables
required_vars = ['MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DB', 'SECRET_KEY']
missing_vars = [var for var in required_vars if app.config[var] is None]
if missing_vars:
    logging.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Database connection pool
try:
    db_pool = PooledDB(
        creator=mariadb,
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB'],
        maxconnections=5
    )
except mariadb.Error as e:
    logging.error(f"Failed to initialize database connection pool: {e}")
    raise

# Ensure directories exist
os.makedirs(app.config['TIME_LAPSE_FOLDER'], exist_ok=True)
os.makedirs(app.config['PLANT_SNAPSHOTS_FOLDER'], exist_ok=True)

# Global variables
is_feed_paused = False
last_detections = deque(maxlen=5)
detector = ObjectDetector()

# Database initialization
def init_database():
    try:
        conn = db_pool.connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sensor_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                analog_value INT,
                color_red INT,
                accel_x FLOAT,
                pressure FLOAT,
                temperature_sht FLOAT,
                cpu_usage FLOAT,
                ram_usage FLOAT,
                storage_usage FLOAT,
                ip_address VARCHAR(15),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS plants (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS growth_rate (
                id INT AUTO_INCREMENT PRIMARY KEY,
                plant_id INT,
                rate FLOAT,
                height FLOAT,
                time_after_planting INT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plant_id) REFERENCES plants(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS growth_graph (
                id INT AUTO_INCREMENT PRIMARY KEY,
                image LONGTEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS plant_heights (
                id INT AUTO_INCREMENT PRIMARY KEY,
                plant_id INT,
                height FLOAT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plant_id) REFERENCES plants(id)
            )
        ''')

        # Insert sample data if empty
        cursor.execute("SELECT COUNT(*) FROM plants")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO plants (name) VALUES ('Tomato'), ('Basil'), ('Pepper')")
        
        cursor.execute("SELECT COUNT(*) FROM growth_rate")
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO growth_rate (plant_id, rate, height, time_after_planting)
                VALUES 
                    (1, 0.5, 10.0, 10),
                    (1, 0.7, 15.0, 20),
                    (2, 0.3, 8.0, 15),
                    (3, 0.6, 12.0, 12)
            ''')

        conn.commit()
        logging.info("Database tables initialized and sample data inserted successfully")
    except mariadb.Error as e:
        logging.error(f"Failed to initialize database: {e}")
    finally:
        conn.close()

class TimeLapseController:
    def __init__(self):
        self.is_running = False
        self.thread = None
        self.lock = threading.Lock()

    def capture_time_lapse(self, output_folder, interval, num_images):
        for i in range(num_images):
            if not self.is_running:
                break
            success, message = capture_single_photo(output_folder)
            if success:
                logging.info(f"Captured image {i + 1}/{num_images}: {message}")
            else:
                logging.error(f"Failed to capture image {i + 1}/{num_images}: {message}")
            time.sleep(interval)
        self.is_running = False

    def start(self, folder, interval, num_images):
        with self.lock:
            if self.is_running:
                return False, "Time-lapse already running"
            self.is_running = True
            self.thread = threading.Thread(
                target=self.capture_time_lapse,
                kwargs={'output_folder': folder, 'interval': interval, 'num_images': num_images}
            )
            self.thread.daemon = True
            self.thread.start()
            return True, "Time-lapse started"

    def stop(self):
        with self.lock:
            if self.is_running:
                self.is_running = False
                return True, "Time-lapse stopped"
            return False, "No time-lapse running"

time_lapse_controller = TimeLapseController()

# Routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/sensor_data")
def sensor_data():
    sensor_data = {
        "analog_value": random.randint(0, 1023),
        "color_red": random.randint(0, 255),
        "accel_x": random.uniform(-10, 10),
        "pressure": random.uniform(900, 1100),
        "temperature_sht": random.uniform(10, 30),
    }
    system_stats = {
        "cpu_usage": random.uniform(0, 100),
        "ram_usage": random.uniform(0, 100),
        "storage_usage": random.uniform(0, 100),
        "ip_address": "192.168.1.1",
    }

    try:
        conn = db_pool.connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sensor_data (analog_value, color_red, accel_x, pressure, temperature_sht, 
                                   cpu_usage, ram_usage, storage_usage, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            sensor_data["analog_value"], sensor_data["color_red"], sensor_data["accel_x"],
            sensor_data["pressure"], sensor_data["temperature_sht"], system_stats["cpu_usage"],
            system_stats["ram_usage"], system_stats["storage_usage"], system_stats["ip_address"]
        ))
        conn.commit()
    except mariadb.Error as e:
        logging.error(f"Error inserting sensor data: {e}")
    finally:
        conn.close()

    return jsonify({**sensor_data, **system_stats})

@app.route("/pause_feed", methods=["POST"])
def pause_feed():
    global is_feed_paused
    is_feed_paused = True
    logging.info("Live feed paused")
    return jsonify({"message": "Live feed paused"}), 200

@app.route("/resume_feed", methods=["POST"])
def resume_feed():
    global is_feed_paused
    is_feed_paused = False
    logging.info("Live feed resumed")
    return jsonify({"message": "Live feed resumed"}), 200

@app.route("/start_time_lapse", methods=["POST"])
def start_time_lapse():
    data = request.get_json() or {}
    interval = float(data.get('interval', 3600))
    num_images = int(data.get('num_images', 1))

    if interval <= 0 or num_images <= 0:
        return jsonify({"error": "Invalid parameters"}), 400

    success, message = time_lapse_controller.start(
        app.config['TIME_LAPSE_FOLDER'], interval, num_images
    )
    return jsonify({"message": message}), 200 if success else 400

@app.route("/stop_time_lapse", methods=["POST"])
def stop_time_lapse():
    success, message = time_lapse_controller.stop()
    return jsonify({"message": message}), 200 if success else 400

@app.route("/analyze_images", methods=["POST"])
def analyze_images():
    try:
        script_path = os.path.abspath("src/models/analyze_image.py")
        if not os.path.exists(script_path):
            logging.error(f"Script not found: {script_path}")
            return jsonify({"message": "Script not found"}), 404

        logging.info(f"Running script: {script_path}")
        result = subprocess.run(
            ["python", script_path],
            capture_output=True,
            text=True,
            check=True
        )

        logging.info(f"Script output: {result.stdout}")
        return jsonify({"message": "Script executed successfully", "output": result.stdout}), 200
    except subprocess.CalledProcessError as e:
        logging.error(f"Script failed with error: {e.stderr}")
        return jsonify({"message": "Script execution failed", "error": e.stderr}), 500
    except Exception as e:
        logging.error(f"Error running script: {e}")
        return jsonify({"message": f"Failed to run script: {str(e)}"}), 500

@app.route("/inference_data")
def inference_data():
    return jsonify(list(last_detections))

@app.route("/growth_graph")
def growth_graph():
    try:
        conn = db_pool.connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.name AS plant_name, gr.height, gr.time_after_planting
            FROM growth_rate gr
            JOIN plants p ON gr.plant_id = p.id
            ORDER BY gr.time_after_planting
        ''')
        rows = cursor.fetchall()

        if not rows:
            return jsonify({"error": "No growth data found"}), 404

        data = {}
        for row in rows:
            plant_name, height, time = row
            data.setdefault(plant_name, {"time": [], "height": []})
            data[plant_name]["time"].append(time)
            data[plant_name]["height"].append(float(height))

        plt.figure(figsize=(10, 6))
        for plant_name, values in data.items():
            plt.plot(values["time"], values["height"], label=plant_name, marker='o')
        
        plt.title("Plant Growth Over Time")
        plt.xlabel("Time (Days)")
        plt.ylabel("Height (cm)")
        plt.legend(bbox_to_anchor=(1, 1))
        plt.grid(True)
        
        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight")
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode("utf-8")
        plt.close()
        
        return jsonify({"image": image_base64})
    except mariadb.Error as e:
        logging.error(f"Database error: {e}")
        return jsonify({"error": "Database error"}), 500
    except Exception as e:
        logging.error(f"Graph generation error: {e}")
        return jsonify({"error": "Failed to generate growth graph"}), 500
    finally:
        conn.close()

@app.route("/stored_growth_graph")
def stored_growth_graph():
    try:
        conn = db_pool.connection()
        cursor = conn.cursor()
        cursor.execute("SELECT image FROM growth_graph ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            return jsonify({"image": row[0]})
        return jsonify({"error": "No graph images found"}), 404
    except mariadb.Error as e:
        logging.error(f"Database error: {e}")
        return jsonify({"error": "Database error"}), 500
    finally:
        conn.close()

@app.route("/growth_rate")
def growth_rate():
    try:
        conn = db_pool.connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT gr.rate, gr.height, gr.time_after_planting, p.name AS plant_name
            FROM growth_rate gr
            JOIN plants p ON gr.plant_id = p.id
        ''')
        data = [{
            "rate": row[0],
            "height": row[1],
            "time_after_planting": row[2],
            "plant_name": row[3]
        } for row in cursor.fetchall()]
        return jsonify(data)
    except mariadb.Error as e:
        logging.error(f"Database error: {e}")
        return jsonify([]), 500
    finally:
        conn.close()

@app.route("/plant_height")
def plant_height():
    try:
        conn = db_pool.connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ph.height, p.name AS plant_name, ph.timestamp
            FROM plant_heights ph
            JOIN plants p ON ph.plant_id = p.id
            ORDER BY ph.timestamp DESC LIMIT 1
        ''')
        row = cursor.fetchone()
        if row:
            return jsonify({
                "height": row[0] * 100,  # Convert to cm
                "plant_name": row[1],
                "timestamp": row[2].strftime("%Y-%m-%d %H:%M:%S")
            })
        return jsonify({"error": "No height data found"}), 404
    except mariadb.Error as e:
        logging.error(f"Database error: {e}")
        return jsonify({"error": "Database error"}), 500
    finally:
        conn.close()

@app.route("/seasonal_status")
def seasonal_status():
    try:
        conn = db_pool.connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT gr.time_after_planting, p.name AS plant_name
            FROM growth_rate gr
            JOIN plants p ON gr.plant_id = p.id
        ''')
        data = cursor.fetchall()
        
        seasonal_status_data = []
        for time_after_planting, plant_name in data:
            start_date = (datetime.now() - timedelta(days=time_after_planting)).strftime("%Y-%m-%d")
            current_stage = ("Early Growth" if time_after_planting < 30 else
                           "Mid Growth" if time_after_planting < 60 else
                           "Late Growth")
            seasonal_status_data.append({
                "plant_name": plant_name,
                "start_date": start_date,
                "current_stage": current_stage
            })
        return jsonify(seasonal_status_data)
    except mariadb.Error as e:
        logging.error(f"Database error: {e}")
        return jsonify([]), 500
    finally:
        conn.close()

@app.route("/harvest_scheduler")
def harvest_scheduler():
    try:
        conn = db_pool.connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT gr.time_after_planting, p.name AS plant_name
            FROM growth_rate gr
            JOIN plants p ON gr.plant_id = p.id
        ''')
        data = cursor.fetchall()
        
        harvest_scheduler_data = []
        for time_after_planting, plant_name in data:
            planting_date = datetime.now() - timedelta(days=time_after_planting)
            predicted_harvest_date = planting_date + timedelta(days=90)
            harvest_scheduler_data.append({
                "plant_name": plant_name,
                "predicted_harvest_date": predicted_harvest_date.strftime("%Y-%m-%d")
            })
        return jsonify(harvest_scheduler_data)
    except mariadb.Error as e:
        logging.error(f"Database error: {e}")
        return jsonify([]), 500
    finally:
        conn.close()

@app.route("/capture_snapshot", methods=["POST"])
def capture_snapshot_route():
    stem_points, ply_path, height = capture_snapshot()
    if stem_points is not None and ply_path is not None:
        try:
            conn = db_pool.connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO plant_heights (plant_id, height)
                VALUES (?, ?)
            ''', (1, height))
            conn.commit()
            logging.info(f"Stored height {height*100:.1f}cm for snapshot: {ply_path}")
        except mariadb.Error as e:
            logging.error(f"Failed to store height: {e}")
        finally:
            conn.close()
        return jsonify({"message": "Snapshot captured", "ply_path": ply_path, "height": height * 100}), 200
    logging.error("Failed to capture snapshot")
    return jsonify({"error": "Failed to capture snapshot"}), 500

@app.route("/video_feed")
def video_feed():
    global is_feed_paused
    if is_feed_paused:
        logging.info("Video feed is paused")
        return jsonify({"error": "Feed is paused"}), 503

    try:
        return Response(
            detector.generate_frames(get_real_feed, last_detections),
            mimetype="multipart/x-mixed-replace; boundary=frame"
        )
    except Exception as e:
        logging.error(f"Error streaming video feed: {str(e)}")
        return jsonify({"error": "Failed to stream video feed", "details": str(e)}), 500

@app.route("/get_real_feed")
def serve_real_feed():
    img = get_real_feed()
    if img is None or img.size == 0:
        logging.error("Failed to get real feed image")
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(img, "No Kinect Feed", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    _, buffer = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), app.config['JPEG_QUALITY']])
    return Response(buffer.tobytes(), mimetype='image/jpeg')

@app.route("/get_stem_data")
def get_stem_data():
    """Serve 3D stem points and height for Three.js visualization."""
    from src.models.plant_growth import lock, latest_data
    with lock:
        stem_points = latest_data.get('stem_points')
        height = latest_data.get('height')
    
    if stem_points is None or len(stem_points) < 2:
        logging.warning("No valid stem points")
        return jsonify({'error': 'No valid stem points', 'points': [], 'height': {'inches': 0.0, 'cm': 0.0}})
    
    points = stem_points.tolist()
    height_cm = float(height * 100)  # Convert to cm
    height_in = float(height * 39.3701)  # Convert to inches
    return jsonify({
        'points': points,
        'height': {'inches': height_in, 'cm': height_cm}
    })

@app.route("/get_stem_outline")
def serve_stem_outline():
    img = get_stem_outline()
    if img is None or img.size == 0:
        logging.error("Failed to get stem outline image")
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(img, "No Stem Outline", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    _, buffer = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), app.config['JPEG_QUALITY']])
    return Response(buffer.tobytes(), mimetype='image/jpeg')

@app.route("/get_view3_image")
def get_view3_image():
    current_idx = request.args.get('idx', default=0, type=int)
    img = generate_view3_image(current_idx)
    if img is None or img.size == 0:
        logging.error("Failed to get View 3 image")
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(img, "No Timelapse Data", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    _, buffer = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), app.config['JPEG_QUALITY']])
    return Response(buffer.tobytes(), mimetype='image/jpeg')

@app.route("/get_snapshot_count")
def get_snapshot_count_route():
    count = get_snapshot_count()
    return jsonify({"count": count})

if __name__ == "__main__":
    init_database()
    try:
        app.run(host="0.0.0.0", port=8086, threaded=True)
    finally:
        pass