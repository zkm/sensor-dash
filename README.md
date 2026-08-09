# Sensor Dash

Web dashboard and API for monitoring Linux system temperatures. Auto-detects available sensors (CPU, GPU, chipset, VRM, NVMe) and only displays what's actually present on the host; includes extra chipset/board detection for AMD AM5 desktops.

This project provides:
- A Flask backend API for live sensor data
- A full dashboard view
- A kiosk view for small displays
- Optional Docker deployment (including Raspberry Pi proxy mode)

## Project Files

- [sensor_dash_server.py](sensor_dash_server.py): Flask server and sensor API
- [sensor_dash.html](sensor_dash.html): Full dashboard UI
- [sensor_dash_kiosk.html](sensor_dash_kiosk.html): Kiosk UI
- [docker-compose.yml](docker-compose.yml): Container orchestration
- [Dockerfile](Dockerfile): Container build image

Guides:
- [docs/DASHBOARD_GUIDE.md](docs/DASHBOARD_GUIDE.md)
- [docs/DOCKER_DEPLOYMENT.md](docs/DOCKER_DEPLOYMENT.md)
- [docs/TEMPERATURE_MAPPING.md](docs/TEMPERATURE_MAPPING.md)

## Quick Start (Local)

1. Install dependencies:
   pip install -r requirements.txt

2. Run server:
   python3 sensor_dash_server.py

3. Open:
   http://localhost:5000/dashboard

## API Endpoints

- /api/health
- /api/sensors
- /api/temps
- /api/status
- /api/system-info

## Docker

Build and run with Docker Compose:

1. docker compose up -d --build
2. Open http://localhost:5000/dashboard

For Raspberry Pi and proxy mode details, see [docs/DOCKER_DEPLOYMENT.md](docs/DOCKER_DEPLOYMENT.md).

## Notes

- Motherboard fan control may remain BIOS/UEFI-managed on many boards.
- Sensor availability depends on kernel modules and host hardware.

## License

MIT. See [LICENSE](LICENSE).
