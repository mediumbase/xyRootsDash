import cv2
import numpy as np
import freenect
import open3d as o3d
import os
from datetime import datetime
import matplotlib.pyplot as plt
import threading
import time
import logging
from sklearn.cluster import DBSCAN
from scipy.interpolate import splprep, splev

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Settings
OUTPUT_DIR = os.path.expanduser("/BASE/dev_inference/dashboard/media/plant_snapshots")
os.makedirs(OUTPUT_DIR, exist_ok=True)
DEPTH_RANGE = (200, 1500)  # Depth range in mm for plant
VOXEL_SIZE = 0.01  # Voxel size in meters
VIEW_WIDTH, VIEW_HEIGHT = 640, 480
CROP_WIDTH, CROP_HEIGHT = 320, 360  # Cropped dimensions for centered plant
NUM_POINTS = 20  # Increased for smoother spline

# Global state
snapshots = []  # List of {'ply_path': str, 'stem_points': np.array, 'height': float}
latest_data = {'rgb': None, 'depth': None, 'stem_points': None, 'height': None}
lock = threading.Lock()

def get_depth():
    try:
        depth, timestamp = freenect.sync_get_depth()
        if depth is None or depth.shape != (VIEW_HEIGHT, VIEW_WIDTH):
            logging.error(f"Invalid depth data: shape={depth.shape if depth is not None else None}, timestamp={timestamp}")
            return None
        return np.clip(depth, 0, 2**10 - 1).astype(np.uint16)
    except Exception as e:
        logging.error(f"Failed to get depth data: {e}")
        return None

def get_rgb():
    try:
        rgb, timestamp = freenect.sync_get_video()
        if rgb is None or rgb.shape != (VIEW_HEIGHT, VIEW_WIDTH, 3):
            logging.error(f"Invalid RGB data: shape={rgb.shape if rgb is not None else None}, timestamp={timestamp}")
            return None
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    except Exception as e:
        logging.error(f"Failed to get RGB data: {e}")
        return None

def depth_to_point_cloud(depth, rgb):
    if depth is None or rgb is None:
        return np.array([]), np.array([]), None, None
    # Crop to center (assuming plant is centered)
    h, w = depth.shape
    x_start = (w - CROP_WIDTH) // 2
    x_end = x_start + CROP_WIDTH
    y_start = (h - CROP_HEIGHT) // 2
    y_end = y_start + CROP_HEIGHT
    depth_cropped = depth[y_start:y_end, x_start:x_end]
    rgb_cropped = rgb[y_start:y_end, x_start:x_end]
    fx, fy = 594.21, 591.04
    cx, cy = 339.5, 242.7
    cx_cropped = cx - x_start
    cy_cropped = cy - y_start
    h_cropped, w_cropped = depth_cropped.shape
    x, y = np.meshgrid(np.arange(w_cropped), np.arange(h_cropped))
    valid = (depth_cropped > DEPTH_RANGE[0]) & (depth_cropped < DEPTH_RANGE[1])
    z = depth_cropped[valid] / 1000.0
    x = (x[valid] - cx_cropped) * z / fx
    y = (y[valid] - cy_cropped) * z / fy
    points = np.vstack((x, y, z)).T
    colors = rgb_cropped[valid] / 255.0
    return points, colors, rgb_cropped, depth_cropped

def detect_stem_points(pcd, depth_cropped):
    points = np.asarray(pcd.points)
    if points.shape[0] == 0 or depth_cropped is None:
        logging.warning("No points in point cloud or invalid depth data")
        return np.array([]), 0.0
    try:
        point_density = points.shape[0] / (CROP_WIDTH * CROP_HEIGHT)
        eps = max(0.03, min(0.1, point_density * 0.5))
        clustering = DBSCAN(eps=eps, min_samples=5).fit(points)
        labels = clustering.labels_
        if np.max(labels) < 0:
            logging.warning("No valid clusters found; using depth-based fallback")
            min_depth_idx = np.argmin(depth_cropped)
            min_depth_y, min_depth_x = np.unravel_index(min_depth_idx, depth_cropped.shape)
            min_depth = depth_cropped[min_depth_y, min_depth_x] / 1000.0
            fx = 594.21
            cx = CROP_WIDTH / 2
            x_center = (min_depth_x - cx) * min_depth / fx
            valid_points = points[(points[:, 2] >= min_depth - 0.1) & (points[:, 2] <= min_depth + 0.1)]
            if valid_points.shape[0] < 5:
                return np.array([]), 0.0
            y_min, y_max = valid_points[:, 1].min(), valid_points[:, 1].max()
            z_min, z_max = valid_points[:, 2].min(), valid_points[:, 2].max()
        else:
            largest_cluster_label = np.argmax([np.sum(labels == i) for i in np.unique(labels) if i != -1])
            plant_points = points[labels == largest_cluster_label]
            if plant_points.shape[0] < 5:
                logging.warning("Largest cluster too small")
                return np.array([]), 0.0
            y_min, y_max = plant_points[:, 1].min(), plant_points[:, 1].max()
            z_min, z_max = plant_points[:, 2].min(), plant_points[:, 2].max()

        valid_depth = depth_cropped[(depth_cropped > DEPTH_RANGE[0]) & (depth_cropped < DEPTH_RANGE[1])]
        if valid_depth.size == 0:
            logging.warning("No valid depth values in range")
            return np.array([]), 0.0
        min_depth_idx = np.argmin(depth_cropped)
        min_depth_y, min_depth_x = np.unravel_index(min_depth_idx, depth_cropped.shape)
        min_depth = depth_cropped[min_depth_y, min_depth_x] / 1000.0
        fx = 594.21
        cx = CROP_WIDTH / 2
        x_center = (min_depth_x - cx) * min_depth / fx

        height = y_max - y_min
        y_vals = np.linspace(y_max, y_min, NUM_POINTS)
        z_vals = np.linspace(z_max, z_min, NUM_POINTS)
        x_vals = np.full(NUM_POINTS, x_center)
        points_3d = np.vstack((x_vals, y_vals, z_vals)).T
        tck, u = splprep(points_3d.T, s=0.01)
        u_fine = np.linspace(0, 1, NUM_POINTS)
        x_spline, y_spline, z_spline = splev(u_fine, tck)
        stem_points = np.vstack((x_spline, y_spline, z_spline)).T

        logging.info(f"Detected plant at x={x_center:.3f}, depth={min_depth:.3f}, height={height*100:.1f}cm, points={NUM_POINTS}")
        return stem_points, height
    except Exception as e:
        logging.error(f"Stem detection failed: {e}")
        return np.array([]), 0.0

def create_stem_outline(stem_points, height):
    img = np.zeros((VIEW_HEIGHT, VIEW_WIDTH, 3), dtype=np.uint8)
    if len(stem_points) < 2:
        logging.warning("Insufficient stem points for outline")
        cv2.putText(img, "No Stem Outline", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        return img
    fx, fy = 594.21, 591.04
    cx, cy = 339.5, 242.7
    pixels = []
    for point in stem_points:
        x, y, z = point
        if z <= 0:
            continue
        x_pixel = int((x * fx / z) + cx)
        y_pixel = int((y * fy / z) + cy)
        if 0 <= x_pixel < VIEW_WIDTH and 0 <= y_pixel < VIEW_HEIGHT:
            pixels.append((x_pixel, y_pixel))
    if len(pixels) < 2:
        logging.warning("No valid pixels for stem outline")
        cv2.putText(img, "No Stem Outline", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        return img
    pixels = np.array(pixels, dtype=np.int32)
    cv2.polylines(img, [pixels], isClosed=False, color=(0, 255, 0), thickness=3)
    cv2.polylines(img, [pixels], isClosed=False, color=(0, 0, 0), thickness=5)  # Shadow
    cv2.polylines(img, [pixels], isClosed=False, color=(0, 255, 0), thickness=3)  # Overlay
    for x, y in pixels[::len(pixels)//3]:
        cv2.circle(img, (x, y), 5, (0, 255, 0), -1)
    height_cm = height * 100
    height_in = height * 39.3701
    height_text = f"Height: {height_in:.1f}in/{height_cm:.1f}cm"
    cv2.putText(img, height_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(img, "Stem Outline", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    return img

def capture_snapshot():
    with lock:
        depth = get_depth()
        rgb = get_rgb()
        if depth is None or rgb is None:
            logging.error("Failed to capture snapshot: Invalid Kinect data")
            return None, None, 0.0
        points, colors, rgb_cropped, depth_cropped = depth_to_point_cloud(depth, rgb)
        if points.shape[0] == 0:
            logging.error("Failed to capture snapshot: Empty point cloud")
            return None, None, 0.0
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        pcd.colors = o3d.utility.Vector3dVector(colors)
        pcd = pcd.voxel_down_sample(VOXEL_SIZE)
        stem_points, height = detect_stem_points(pcd, depth_cropped)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ply_path = os.path.join(OUTPUT_DIR, f"plant_{timestamp}.ply")
        o3d.io.write_point_cloud(ply_path, pcd)
        snapshots.append({'ply_path': ply_path, 'stem_points': stem_points, 'height': height})
        logging.info(f"Snapshot captured: {ply_path}, height={height*100:.1f}cm")
        return stem_points, ply_path, height

def background_capture():
    retry_count = 0
    max_retries = 3
    while True:
        try:
            depth = get_depth()
            rgb = get_rgb()
            if depth is not None and rgb is not None:
                points, colors, rgb_cropped, depth_cropped = depth_to_point_cloud(depth, rgb)
                pcd = o3d.geometry.PointCloud()
                pcd.points = o3d.utility.Vector3dVector(points)
                pcd.colors = o3d.utility.Vector3dVector(colors)
                pcd = pcd.voxel_down_sample(VOXEL_SIZE)
                stem_points, height = detect_stem_points(pcd, depth_cropped)
                with lock:
                    latest_data.update({'rgb': rgb, 'depth': depth, 'stem_points': stem_points, 'height': height})
                retry_count = 0
            else:
                logging.warning("Skipping background capture due to invalid Kinect data")
                with lock:
                    latest_data.update({'rgb': None, 'depth': None, 'stem_points': None, 'height': 0.0})
                retry_count += 1
            if retry_count >= max_retries:
                logging.error(f"Failed to capture Kinect data after {max_retries} retries")
                time.sleep(1)
                retry_count = 0
        except Exception as e:
            logging.error(f"Background capture error: {e}")
            retry_count += 1
            if retry_count >= max_retries:
                time.sleep(1)
                retry_count = 0
        time.sleep(0.1)

threading.Thread(target=background_capture, daemon=True).start()

def get_real_feed():
    with lock:
        rgb = latest_data['rgb']
    if rgb is None:
        logging.warning("No valid RGB feed; returning placeholder")
        img = np.zeros((VIEW_HEIGHT, VIEW_WIDTH, 3), dtype=np.uint8)
        cv2.putText(img, "No Kinect Feed", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        return img
    return rgb

def get_stem_outline():
    with lock:
        stem_points = latest_data['stem_points']
        height = latest_data['height']
    if stem_points is None or len(stem_points) < 2:
        logging.warning("No valid stem points; returning placeholder")
        img = np.zeros((VIEW_HEIGHT, VIEW_WIDTH, 3), dtype=np.uint8)
        cv2.putText(img, "No Stem Outline", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        return img
    return create_stem_outline(stem_points, height)

def generate_view3_image(current_idx):
    with lock:
        if not snapshots or current_idx < 0 or current_idx >= len(snapshots):
            logging.warning("No snapshots available; returning placeholder")
            img = np.zeros((VIEW_HEIGHT, VIEW_WIDTH, 3), dtype=np.uint8)
            cv2.putText(img, "No Timelapse Data", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            return img
        stem_points_list = [snap['stem_points'] for snap in snapshots]
        height_list = [snap['height'] for snap in snapshots]
    return create_2d_view3(stem_points_list, height_list, current_idx)

def create_2d_view3(stem_points_list, height_list, current_idx):
    fig, ax = plt.subplots(figsize=(VIEW_WIDTH/100, VIEW_HEIGHT/100))
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Z (m)")
    ax.set_title("Growth Timelapse")
    for i, (stem_points, height) in enumerate(zip(stem_points_list[:current_idx + 1], height_list[:current_idx + 1])):
        if len(stem_points) > 0:
            ax.scatter(stem_points[:, 0], stem_points[:, 2], c=[plt.cm.viridis(i / max(1, len(snapshots)))], s=50)
            ax.text(stem_points[0, 0], stem_points[0, 2], f"{height*100:.1f}cm", fontsize=8)
    ax.legend([f"Snapshot {i+1}" for i in range(len(snapshots[:current_idx + 1]))])
    fig.canvas.draw()
    img = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8)
    img = img.reshape(fig.canvas.get_width_height()[::-1] + (4,))[:, :, :3]
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    plt.close(fig)
    return cv2.resize(img, (VIEW_WIDTH, VIEW_HEIGHT))

def get_snapshot_count():
    with lock:
        return len(snapshots)