xyRootDash
Description
xyRootDash is a Flask-based web application designed for monitoring plant growth and environmental conditions. It leverages a Kinect device for depth sensing to capture plant snapshots and perform growth analysis, alongside other sensors for environmental data collection. Key features include a live video feed with object detection, sensor data visualization, growth graphs, time-lapse photography, and a harvest scheduler, all accessible through an intuitive web dashboard.
Prerequisites

Ubuntu server on x86 architecture
Python 3.8 or higher
MariaDB server
Kinect device connected to the system
Internet connection for installing dependencies

Installation

Ensure the Project Directory

Verify that the project is located at /mnt/HUB/enterprise/apps/python/app_xyrootdash. If not, move or clone it there:mv /path/to/xyrootdash /mnt/HUB/enterprise/apps/python/app_xyrootdash

orgit clone <repository_url> /mnt/HUB/enterprise/apps/python/app_xyrootdash




Set Up a Virtual Environment
cd /mnt/HUB/enterprise/apps/python/app_xyrootdash
python3 -m venv venv
source venv/bin/activate


Install Dependencies
pip install -r requirements.txt


Set Up libfreenect (Kinect Support)

Navigate to the libfreenect directory:cd libfreenect


Build and install:mkdir build && cd build
cmake ..
make
sudo make install


Install Python bindings:sudo pip install -e ../wrappers/python


Set up udev rules for Kinect (non-root access):sudo cp ../platform/linux/udev/99-kinect.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger




Set Up MariaDB

Install MariaDB:sudo apt-get update
sudo apt-get install mariadb-server


Start the service:sudo systemctl start mariadb


Secure the installation:sudo mysql_secure_installation


Create the database and user:sudo mysql -u root -p
CREATE DATABASE xyrootdash;
CREATE USER 'xyrootdash_user'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON xyrootdash.* TO 'xyrootdash_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;




Configure Environment Variables

Create a .env file in the project root:nano .env


Add the following content (replace your_secure_password and your_unique_secret_key with secure values):MYSQL_HOST=localhost
MYSQL_USER=xyrootdash_user
MYSQL_PASSWORD=your_secure_password
MYSQL_DB=xyrootdash
SECRET_KEY=your_unique_secret_key


Optionally, override default paths:TIME_LAPSE_FOLDER=/mnt/HUB/enterprise/apps/python/app_xyrootdash/media/time_lapse
PLANT_SNAPSHOTS_FOLDER=/mnt/HUB/enterprise/apps/python/app_xyrootdash/media/plant_snapshots




Initialize the Database

Activate the virtual environment if not already active:source venv/bin/activate


Run the application once to create tables and insert sample data:python app.py


Stop the server with Ctrl+C after initialization.


Run the Application

For development:python app.py


For production, install Gunicorn:pip install gunicorn


Run with Gunicorn:gunicorn -w 4 -b 0.0.0.0:8086 app:app


Optional: Set up as a systemd service:
Create a service file:sudo nano /etc/systemd/system/xyrootdash.service


Add:[Unit]
Description=xyRootDash Flask Application
After=network.target

[Service]
User=boss
WorkingDirectory=/mnt/HUB/enterprise/apps/python/app_xyrootdash
ExecStart=/mnt/HUB/enterprise/apps/python/app_xyrootdash/venv/bin/gunicorn -w 4 -b 0.0.0.0:8086 app:app
Restart=always

[Install]
WantedBy=multi-user.target


Enable and start:sudo systemctl enable xyrootdash
sudo systemctl start xyrootdash







Usage

Access the dashboard at http://<server_ip>:8086
Live Feed: View the Kinect video feed with object detection overlays.
Snapshot: Click "Snapshot" to capture plant height and save a point cloud file.
Time-Lapse: Click "Time-Lapse" to start a sequence (configure interval and number via JSON payload if needed).
Analyze: Click "Analyze" to process images for growth metrics.
Monitor sensor data, growth graphs, and harvest schedules on the dashboard.

Troubleshooting

Kinect Not Detected: Verify udev rules and device connection (lsusb to check).
Database Errors: Check .env settings and MariaDB status (sudo systemctl status mariadb).
Path Issues: Ensure media/time_lapse and media/plant_snapshots exist or adjust paths in .env.
Server Not Starting: Review logs in terminal or /var/log/syslog for errors.
