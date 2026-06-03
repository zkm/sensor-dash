# AM5 Monitor - Docker Deployment Guide

Deploy the AM5 system monitor to a Raspberry Pi with Docker.

## Dashboard Options

- **Full Dashboard** (`/dashboard`): Feature-rich with animations, detailed info sections, control cards
- **Kiosk Mode** (`/kiosk`): Lightweight, optimized for 5" displays, shows 4 essential temps (CPU, GPU, Chipset, NVMe)

**For 5" screen displays, use the Kiosk mode** - it's stripped down to show just temperature essentials without animations or extra UI elements.

## Deployment Modes

- **Desktop Source Mode (default):** Container reads local desktop sensors and serves API/UI.
- **Pi Proxy Mode:** Container serves UI on Pi, but API is proxied from desktop via `UPSTREAM_API_BASE`.

This lets the Pi act like a HamClock display while your desktop remains the temperature data source.

## Prerequisites

- **Raspberry Pi 3, 4, or 5** (any model)
- **Raspberry Pi OS** (Lite or Desktop, 32-bit or 64-bit)
- **Docker** installed
- **Docker Compose** installed (optional but recommended)
- **5" Display** (connected to HDMI)

## Installation

### 1. Install Docker & Docker Compose on Raspberry Pi

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add current user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo apt-get install docker-compose
```

### 2. Copy Project to Raspberry Pi

Option A - Via Git:
```bash
cd ~
git clone <your-repo-url> am5-monitor
cd am5-monitor
```

Option B - Via SCP:
```bash
scp -r /path/to/b650_fans pi@<pi-ip>:~/am5-monitor
```

### 3. Build and Run Docker Container

```bash
cd ~/am5-monitor

# Using Docker Compose (recommended)
docker-compose up -d

# OR manually with Docker
docker build -t am5-monitor:latest .
docker run -d \
  --name am5-monitor \
  --restart unless-stopped \
  -p 5000:5000 \
  -v /sys:/sys:ro \
  -v /proc:/proc:ro \
  --cap-add SYS_ADMIN \
  am5-monitor:latest
```

### 3A. Desktop Source Mode (run on desktop)

Run this on your desktop machine so desktop sensors are available:

```bash
docker-compose up -d --build
curl http://localhost:5000/api/sensors
```

### 3B. Pi Proxy Mode (run on Raspberry Pi)

Set your desktop API URL and start the same container on Pi:

```bash
export UPSTREAM_API_BASE="http://<desktop-ip>:5000"
docker-compose up -d --build
```

Verify Pi is reading desktop data:

```bash
curl http://localhost:5000/api/sensors
```

The response should match desktop values, not Pi-local values.

### 4. Access Dashboard

```
http://<your-pi-ip>:5000/dashboard    # Full featured dashboard
http://<your-pi-ip>:5000/kiosk       # Simplified 5" screen mode (recommended)
```

## Running Dashboard in Fullscreen (Kiosk Mode)

**For 5" displays, use the simplified `/kiosk` endpoint which shows only essential temperatures.**

### Option 1: Chromium Fullscreen (Recommended)

Edit crontab to start on boot:
```bash
crontab -e
```

Add this line:
```
@reboot DISPLAY=:0 chromium-browser --kiosk --no-first-run http://localhost:5000/kiosk &
```

If you use Pi Proxy Mode, keep this URL as `localhost` on Pi. The Pi container will fetch data from desktop automatically through `UPSTREAM_API_BASE`.

### Option 2: Using systemd Service

Create `/etc/systemd/system/am5-kiosk.service`:

```ini
[Unit]
Description=AM5 Monitor Fullscreen Display
After=graphical.target
Requires=graphical.target

[Service]
Type=simple
User=pi
Environment=DISPLAY=:0
ExecStart=/usr/bin/chromium-browser --kiosk --no-first-run http://localhost:5000/kiosk
Restart=on-failure
RestartSec=10

[Install]
WantedBy=graphical.target
```

Enable the service:
```bash
sudo systemctl enable am5-kiosk.service
sudo systemctl start am5-kiosk.service
```

### Option 3: Firefox Fullscreen

Install firefox-esr:
```bash
sudo apt-get install firefox-esr
```

Modify the service/crontab to use:
```
firefox --kiosk http://localhost:5000/kiosk
```

## Managing the Container

```bash
# View logs
docker logs -f am5-monitor

# Stop container
docker-compose down
# or
docker stop am5-monitor

# Restart container
docker-compose restart
# or
docker restart am5-monitor

# View container status
docker ps
```

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker logs am5-monitor

# Verify sensors are accessible
docker exec am5-monitor sensors
```

### Sensors Not Reading Data
- Ensure lm-sensors is properly configured on the host Pi
- Run `sudo sensors-detect` on the Raspberry Pi
- Some sensor data may not be available on Pi (depends on hardware)

### Pi Shows Pi Temps Instead of Desktop Temps
- Check `UPSTREAM_API_BASE` is set on Pi: `echo $UPSTREAM_API_BASE`
- Ensure desktop API is reachable from Pi: `curl http://<desktop-ip>:5000/api/sensors`
- Restart Pi container after changing env: `docker-compose up -d --build`

### Dashboard Won't Load
- Check firewall: `sudo ufw allow 5000`
- Verify container is running: `docker ps`
- Check logs: `docker logs am5-monitor`

### Port Already in Use
```bash
# Change port in docker-compose.yml
# Change "5000:5000" to "8080:5000"
# Then access at http://<pi-ip>:8080/dashboard
```

## Performance Optimization for Pi Zero/3

For older Raspberry Pi models, consider:

1. **Reduce refresh rate** in HTML dashboard (edit js intervals)
2. **Use Pi OS Lite** instead of Desktop for less overhead
3. **Allocate adequate memory** in Docker:
   ```yaml
   mem_limit: 256m
   memswap_limit: 256m
   ```

## Notes

- Dashboard will auto-refresh sensor data every 2 seconds
- Container runs without root privilege for security
- Sensor access requires read-only mounts of `/sys` and `/proc`
- Container restarts automatically if it crashes

## Updating the Container

```bash
cd ~/am5-monitor

# Pull latest code
git pull

# Rebuild and restart
docker-compose down
docker-compose up -d --build
```
