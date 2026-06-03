# AM5 System Monitor

Web dashboard and API for monitoring AMD AM5 desktop temperatures.

This project provides:
- A Flask backend API for live sensor data
- A full dashboard view
- A kiosk view for small displays
- Optional Docker deployment (including Raspberry Pi proxy mode)

## Project Files

- [am5_monitor_server.py](am5_monitor_server.py): Flask server and sensor API
- [am5_system_monitor.html](am5_system_monitor.html): Full dashboard UI
- [am5_system_monitor_kiosk.html](am5_system_monitor_kiosk.html): Kiosk UI
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
   python3 am5_monitor_server.py

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
