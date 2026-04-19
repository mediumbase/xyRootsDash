### Merged Setup Guide for xyRootDash

**Description**  
xyRootDash is a Flask-based web application for precision agriculture, monitoring plant growth and environmental conditions using a  3D snapshots and sensors for metrics (e.g., temperature, humidity). Features include live video feed with object detection, time-lapse photography, growth analysis, and a harvest scheduler, accessible via a web dashboard. Data is stored in MariaDB, with visualizations powered by Matplotlib and OpenCV. Optimized for Ubuntu 24.04 (x86).

**Prerequisites**  
- OS: Ubuntu 24.04 
- Hardware: 3d  sense camera (USB 3.0 port)  
- Software: Python 3.8.20, MariaDB 10.11.13, Git  
- Disk Space:  
  - Ensure sufficient space for media storage  
- Internet connection for dependencies  
- GitHub access: https://github.com/mediumbase/xyRootsDash.git  

**Installation**

1. **Update System**  
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install -y build-essential cmake pkg-config software-properties-common \
   libusb-1.0-0-dev libffi-dev libbz2-dev libncurses-dev libreadline-dev \
   libsqlite3-dev liblzma-dev tk-dev libgdbm-dev libc6-dev libssl-dev \
   zlib1g-dev libdb5.3-dev libexpat1-dev libbluetooth-dev pybind11-dev \
   libhdf5-dev make wget llvm libxml2-dev libxmlsec1-dev xz-utils \
   python3.8 python3.8-venv python3.8-dev python3-pip mariadb-server
   sudo apt autoremove
   sudo apt update
   sudo apt install libmariadb-dev mariadb-client gcc python3-dev
   ```

2. **Install pyenv**  
   ```bash
   curl https://pyenv.run | bash
   export PATH="$HOME/.pyenv/bin:$PATH"
   eval "$(pyenv init --path)"
   eval "$(pyenv init -)"
   pyenv install 3.8.20
   pyenv local 3.8.20
   ```

3. **Clone Repository**  
   ```bash
   git clone https://github.com/mediumbase/xyRootsDash.git /mnt/HUB/enterprise/apps/python/app_xyrootdash
   cd /mnt/HUB/enterprise/apps/python/app_xyrootdash
   git checkout development
   ```

4. **Set Up Virtual Environment**  
   ```bash
   python3 -m venv x86
   source x86/bin/activate
   pip install --upgrade pip
   ```

5. **Install Python Dependencies**  
   ```bash
   pip install flask python-dotenv matplotlib opencv-python numpy mariadb dbutils pillow open3d gunicorn
   ```

6. **Install libfreenect (Kinect Support)**  
   ```bash
   sudo apt-get install libusb-1.0-0-dev cmake build-essential
   cd libfreenect
   rm -rf build
   mkdir build && cd build
   cmake ..
   make
   sudo make install
   cd ../wrappers/python
   python setup.py install
   sudo cp /mnt/HUB/enterprise/apps/python/app_xyrootdash/libfreenect/platform/linux/udev/99-kinect.rules /etc/udev/rules.d/
   sudo udevadm control --reload-rules && sudo udevadm trigger
   sudo usermod -a -G video $USER
   ```

7. **Set Up MariaDB**  
   ```bash
   sudo systemctl start mariadb
   sudo mysql_secure_installation
   sudo mysql -u root -p
   ```
   Run in MySQL:  
   ```sql
   CREATE DATABASE rootdash_db;
   CREATE USER 'rootdash_user'@'localhost' IDENTIFIED BY 'your_secure_password';
   GRANT ALL PRIVILEGES ON rootdash_db.* TO 'rootdash_user'@'localhost';
   FLUSH PRIVILEGES;
   USE rootdash_db;
   CREATE TABLE time_lapse_data (
       id INT AUTO_INCREMENT PRIMARY KEY,
       timestamp TIMESTAMP NOT NULL,
       plant_id INT NOT NULL,
       width INT,
       height INT,
       image_path VARCHAR(255),
       FOREIGN KEY (plant_id) REFERENCES plants(id)
   );
   EXIT;
   ```

8. **Configure Environment Variables**  
   ```bash
   nano .env
   ```
   Add:  
   ```
   MYSQL_HOST=localhost
   MYSQL_USER=rootdash_user
   MYSQL_PASSWORD=your_secure_password
   MYSQL_DB=rootdash_db
   SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(16))")
   TIME_LAPSE_FOLDER=/mnt/HUB/enterprise/apps/python/app_xyrootdash/media/time_lapse
   PLANT_SNAPSHOTS_FOLDER=/mnt/HUB/enterprise/apps/python/app_xyrootdash/media/plant_snapshots
   JPEG_QUALITY=95
   ```

9. 

10. **Initialize Database**  
    ```bash
    source renv/bin/activate
    python app.py
    ```
    Stop with Ctrl+C after tables are created.

11. **Production Setup (Optional)**  
    ```bash
    sudo nano /etc/systemd/system/xyrootdash.service
    ```
    Add:  
    ```
    [Unit]
    Description=xyRootDash Flask Application
    After=network.target

    [Service]
    User=boss
    WorkingDirectory=/mnt/HUB/enterprise/apps/python/app_xyrootdash
    ExecStart=/mnt/HUB/enterprise/apps/python/app_xyrootdash/renv/bin/gunicorn -w 4 -b 0.0.0.0:8086 app:app
    Restart=always

    [Install]
    WantedBy=multi-user.target
    ```
    Enable and start:  
    ```bash
    sudo systemctl enable xyrootdash
    sudo systemctl start xyrootdash
    ```

12. **Git Setup**  
    ```bash
    git config --global user.email "youremail"
    git config --global user.name "yourusername"
    git config --global credential.helper store
    git pull origin development --rebase
    git push -u origin development
    ```
    Resolve conflicts if needed:  
    ```bash
    git add <resolved-files>
    git rebase --continue
    git push -u origin development
    ```

**Running the Application**  
- Activate virtual environment:  
  ```bash
  source renv/bin/activate
  ```
- Start for development:  
  ```bash
  python app.py
  ```
- Access dashboard: http://<server_ip>:8086  

**Usage**  
- **Live Feed**: View Kinect video with object detection.  
- **Snapshot**: Capture plant height and point cloud.  
- **Time-Lapse**: Configure interval/number via JSON payload.  
- **Analyze**: Process images for growth metrics.  
- Monitor sensor data, growth graphs, and harvest schedules on the dashboard.

**Troubleshooting**  
- **Kinect Errors**:  
  - Verify connection: `lsusb` (look for Microsoft Kinect Sensor).  
  - Test: `/usr/local/bin/freenect-glview`.  
  - Fix permissions: `sudo usermod -a -G video $USER; sudo reboot`.  
- **Database Errors**:  
  - Check credentials: `sudo mysql -u rootdash_user -p -e "SELECT 1;"`.  
  - Verify schema: `sudo mysql -u root -p -e "USE rootdash_db; SHOW TABLES;"`.  
  - Ensure MariaDB is running: `sudo systemctl status mariadb`.  
- **Git Push Errors**:  
  - Use HTTPS: `git remote set-url origin https://github.com/mediumbase/xyRootsDash.git`.  
  - Set up Personal Access Token if required.  
- **Application Errors**:  
  - Check logs: `journalctl -u xyrootdash` or terminal output.  
  - Remove problematic packages from `requirements.txt` (e.g., `cupshelpers`, `freenect==0.0.0`).  
- **Path Issues**: Ensure `media/time_lapse` and `media/plant_snapshots` exist or adjust `.env`.  

**Notes**  
- Ensure Kinect is connected before running.  
- Update `.gitignore` to exclude `renv/`, `.env`, and `media/`.  
- Monitor disk usage on `/mnt/HUB` (86% used).  
- Reboot after kernel updates (6.8.0-63-generic).
