#!/usr/bin/env python3
"""
X870E System Monitor - Backend Server
Provides real sensor data via REST API to the web dashboard

Installation:
    pip install --break-system-packages flask psutil

Usage:
    python3 am5_monitor_server.py
    Then open: http://localhost:5000/dashboard
"""

import os
import json
import subprocess
import re
import socket
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from urllib import error as urlerror
from urllib import request as urlrequest

try:
    from flask import Flask, jsonify, render_template_string
    from flask_cors import CORS
except ImportError:
    print("Flask not installed. Install with:")
    print("  pip install --break-system-packages flask flask-cors")
    exit(1)

app = Flask(__name__)
CORS(app)

UPSTREAM_API_BASE = os.getenv('UPSTREAM_API_BASE', '').strip().rstrip('/')
BOARD_NAME_OVERRIDE = os.getenv('BOARD_NAME', '').strip()
CHIPSET_NAME_OVERRIDE = os.getenv('CHIPSET_NAME', '').strip()


def proxy_enabled() -> bool:
    """Return True when running in remote API proxy mode."""
    return bool(UPSTREAM_API_BASE)


def proxy_json(path: str):
    """Fetch JSON from upstream API and return Flask response or None when disabled."""
    if not proxy_enabled():
        return None

    upstream_url = f"{UPSTREAM_API_BASE}{path}"
    try:
        with urlrequest.urlopen(upstream_url, timeout=4) as response:
            payload = response.read().decode('utf-8')
            data = json.loads(payload)
            return jsonify(data)
    except urlerror.HTTPError as e:
        return jsonify({
            'status': 'error',
            'message': f'Upstream HTTP error: {e.code}',
            'upstream_url': upstream_url
        }), 502
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Upstream unavailable: {e}',
            'upstream_url': upstream_url
        }), 502


def safe_read_text(path: str) -> str:
    """Read text file, returning an empty string when unavailable."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return ''


def detect_chipset_from_board(board_name: str) -> str:
    """Best-effort chipset hint from board model name."""
    name = board_name.upper()
    if 'X870E' in name:
        return 'AMD X870E'
    if 'X870' in name:
        return 'AMD X870'
    if 'B650E' in name:
        return 'AMD B650E'
    if 'B650' in name:
        return 'AMD B650'
    if 'X670E' in name:
        return 'AMD X670E'
    if 'X670' in name:
        return 'AMD X670'
    return 'AMD AM5 (detected)'


def get_board_identity() -> Dict[str, str]:
    """Return board name/chipset using env override or DMI auto-detection."""
    if BOARD_NAME_OVERRIDE:
        return {
            'board_name': BOARD_NAME_OVERRIDE,
            'chipset': CHIPSET_NAME_OVERRIDE or detect_chipset_from_board(BOARD_NAME_OVERRIDE),
            'source': 'env_override'
        }

    board_vendor = safe_read_text('/sys/devices/virtual/dmi/id/board_vendor')
    board_name_raw = safe_read_text('/sys/devices/virtual/dmi/id/board_name')
    board_version = safe_read_text('/sys/devices/virtual/dmi/id/board_version')

    if board_name_raw:
        board_name = f"{board_vendor} {board_name_raw}".strip() if board_vendor else board_name_raw
        if board_version and board_version not in ('Default string', 'To be filled by O.E.M.'):
            board_name = f"{board_name} ({board_version})"
        return {
            'board_name': board_name,
            'chipset': CHIPSET_NAME_OVERRIDE or detect_chipset_from_board(board_name_raw),
            'source': 'dmi'
        }

    return {
        'board_name': 'AMD AM5 Motherboard',
        'chipset': CHIPSET_NAME_OVERRIDE or 'AMD AM5',
        'source': 'fallback'
    }

# Color codes for terminal output
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

class SensorReader:
    """Read sensor data from lm_sensors"""

    CPU_LABEL_PATTERNS = (
        r'tctl',
        r'tdie',
        r'cpu',
        r'package',
    )

    CHIPSET_LABEL_PATTERNS = (
        r'chipset',
        r'pch',
        r'motherboard',
        r'system',
        r'systin',
        r't[_ -]?sensor',
        r'board',
    )

    VRM_LABEL_PATTERNS = (
        r'vrm',
        r'mos',
        r'vcore',
        r'power',
        r'soc',
    )

    MOTHERBOARD_CHIP_PATTERNS = (
        r'gigabyte_wmi',
        r'asus',
        r'nct',
        r'it8',
        r'it86',
        r'superio',
    )
    
    @staticmethod
    def run_command(cmd: str) -> str:
        """Execute shell command and return output"""
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            return result.stdout
        except subprocess.TimeoutExpired:
            return ""
        except Exception as e:
            print(f"Error running command: {e}")
            return ""

    @staticmethod
    def parse_sensor_sections(output: str) -> List[Tuple[str, str]]:
        """Split `sensors` output into (chip_name, section_text) pairs."""
        sections: List[Tuple[str, str]] = []
        for block in output.strip().split('\n\n'):
            block = block.strip()
            if not block:
                continue
            lines = block.splitlines()
            if not lines:
                continue
            chip_name = lines[0].strip()
            sections.append((chip_name, block))
        return sections

    @staticmethod
    def normalize_label(label: str) -> str:
        """Normalize sensor labels to safe dictionary keys."""
        normalized = re.sub(r'[^a-z0-9]+', '_', label.lower()).strip('_')
        return normalized or 'temp'

    @staticmethod
    def parse_temp_lines(section_text: str) -> Dict[str, float]:
        """Extract temperature-like values from a sensor section."""
        values: Dict[str, float] = {}
        for line in section_text.splitlines()[1:]:
            line = line.rstrip()
            if ':' not in line:
                continue
            label, rest = line.split(':', 1)
            label = label.strip()
            if not label:
                continue
            if re.search(r'\b(low|high|crit|hyst|offset|min|max)\b', label, re.IGNORECASE):
                continue

            value_match = re.search(r'([+-]?\d+\.?\d*)\s*(?:°?C|C)\b', rest)
            if not value_match:
                continue

            key = SensorReader.normalize_label(label)
            if key in values:
                suffix = 2
                while f"{key}_{suffix}" in values:
                    suffix += 1
                key = f"{key}_{suffix}"
            values[key] = float(value_match.group(1))
        return values

    @staticmethod
    def pick_temp_by_patterns(temp_map: Dict[str, float], patterns: Tuple[str, ...]) -> Optional[Tuple[str, float]]:
        """Pick first matching temperature by key patterns."""
        for pattern in patterns:
            regex = re.compile(pattern, re.IGNORECASE)
            for key, value in temp_map.items():
                if regex.search(key):
                    return key, value
        return None

    @staticmethod
    def get_sysfs_cpu_temp() -> Optional[float]:
        """Read CPU temperature from thermal_zone interfaces as fallback."""
        try:
            temp_paths = SensorReader.run_command("ls /sys/class/thermal/thermal_zone*/temp 2>/dev/null").splitlines()
            for path in temp_paths:
                path = path.strip()
                if not path:
                    continue
                raw = SensorReader.run_command(f"cat {path} 2>/dev/null").strip()
                if not raw.isdigit():
                    continue
                value = int(raw)
                # Typical millidegree C values from kernel thermal zones
                if 10000 <= value <= 130000:
                    return value / 1000.0
            return None
        except Exception:
            return None

    @staticmethod
    def select_cpu_temp(sensor_data: Dict) -> Tuple[Optional[float], str]:
        """Select best CPU temperature across common Linux sensor providers."""
        # AMD CPUs typically expose Tctl/Tdie in k10temp.
        for cpu_chip in ('k10temp', 'zenpower'):
            temps = sensor_data.get('cpu_chips', {}).get(cpu_chip, {})
            selected = SensorReader.pick_temp_by_patterns(temps, SensorReader.CPU_LABEL_PATTERNS)
            if selected:
                key, temp = selected
                return temp, f"{cpu_chip}:{key}"

        # Fall back to motherboard chips when they expose CPU/package labels.
        mb_temps = sensor_data.get('motherboard', {})
        selected_mb = SensorReader.pick_temp_by_patterns(mb_temps, SensorReader.CPU_LABEL_PATTERNS)
        if selected_mb:
            key, temp = selected_mb
            return temp, f"motherboard:{key}"

        sysfs_temp = SensorReader.get_sysfs_cpu_temp()
        if sysfs_temp is not None:
            return sysfs_temp, "thermal_zone"

        return None, "unknown"
    
    @staticmethod
    def get_cpu_temp() -> Optional[float]:
        """Get best-effort CPU temperature across motherboard vendors."""
        try:
            sensor_data = SensorReader.get_sensors_data()
            temp, _source = SensorReader.select_cpu_temp(sensor_data)
            return temp
        except Exception as e:
            print(f"Error reading CPU temp: {e}")
            return None
    
    @staticmethod
    def get_sensors_data() -> Dict:
        """Parse output from 'sensors' command"""
        output = SensorReader.run_command("sensors 2>/dev/null")
        if not output:
            return {}
        
        data = {
            'motherboard': {},
            'motherboard_chip': None,
            'cpu_chips': {},
            'amdgpu_devices': {},
            'nvme': {}
        }

        sections = SensorReader.parse_sensor_sections(output)

        # Parse motherboard sensor chips (Gigabyte/ASUS/Super I/O variants).
        for chip_name, section_text in sections:
            chip_lower = chip_name.lower()
            if any(re.search(pattern, chip_lower) for pattern in SensorReader.MOTHERBOARD_CHIP_PATTERNS):
                temps = SensorReader.parse_temp_lines(section_text)
                if temps and not data['motherboard_chip']:
                    data['motherboard_chip'] = chip_name
                data['motherboard'].update(temps)

            if chip_lower.startswith('k10temp') or chip_lower.startswith('zenpower'):
                cpu_key = 'k10temp' if chip_lower.startswith('k10temp') else 'zenpower'
                data['cpu_chips'][cpu_key] = SensorReader.parse_temp_lines(section_text)

        # Parse any amdgpu device (not hardcoded IDs).
        for chip_name, section_text in sections:
            chip_lower = chip_name.lower()
            if not chip_lower.startswith('amdgpu-pci-'):
                continue

            gpu_id = chip_name
            gpu_text = section_text
            gpu_data = {}
            
            edge = re.search(r'edge:\s+([+-]?\d+\.?\d*)', gpu_text)
            junction = re.search(r'junction:\s+([+-]?\d+\.?\d*)', gpu_text)
            mem = re.search(r'mem:\s+([+-]?\d+\.?\d*)', gpu_text)
            fan = re.search(r'fan1:\s+(\d+)', gpu_text)
            pwm = re.search(r'pwm1:\s+(\d+)%', gpu_text)
            
            if edge:
                gpu_data['edge'] = float(edge.group(1))
            if junction:
                gpu_data['junction'] = float(junction.group(1))
            if mem:
                gpu_data['mem'] = float(mem.group(1))
            if fan:
                gpu_data['fan_rpm'] = int(fan.group(1))
            if pwm:
                gpu_data['pwm'] = int(pwm.group(1))
            
            data['amdgpu_devices'][gpu_id] = gpu_data

        # Parse NVMe temperatures.
        for chip_name, section_text in sections:
            chip_lower = chip_name.lower()
            if not chip_lower.startswith('nvme-pci-'):
                continue
            nvme_id = chip_name.split('-')[-1]
            nvme_data = section_text
            composite = re.search(r'Composite:\s+([+-]?\d+\.?\d*)', nvme_data)
            if composite:
                data['nvme'][f'nvme_{nvme_id}'] = float(composite.group(1))
        
        return data

    @staticmethod
    def select_motherboard_temp(sensor_data: Dict, patterns: Tuple[str, ...], fallback_keys: Tuple[str, ...] = ()) -> Tuple[Optional[float], str]:
        """Select motherboard-related temperature by label patterns and fallback keys."""
        mb = sensor_data.get('motherboard', {})
        selected = SensorReader.pick_temp_by_patterns(mb, patterns)
        if selected:
            key, value = selected
            return value, key

        for key in fallback_keys:
            if key in mb:
                return mb[key], key

        return None, 'unknown'
    
    @staticmethod
    def get_all_temps() -> Dict:
        """Get all temperature data"""
        sensor_data = SensorReader.get_sensors_data()
        cpu_temp, cpu_source = SensorReader.select_cpu_temp(sensor_data)

        chipset_temp, chipset_source = SensorReader.select_motherboard_temp(
            sensor_data,
            SensorReader.CHIPSET_LABEL_PATTERNS,
            fallback_keys=('temp2', 'temp1')
        )

        vrm_temp, vrm_source = SensorReader.select_motherboard_temp(
            sensor_data,
            SensorReader.VRM_LABEL_PATTERNS,
            fallback_keys=('temp5',)
        )

        temps = {
            'cpu': cpu_temp,
            'cpu_sensor': cpu_source,
            'motherboard': {},
            'gpu': {},
            'storage': {},
            'chipset': chipset_temp,
            'chipset_sensor': chipset_source,
            'vrm': vrm_temp,
            'vrm_sensor': vrm_source,
            'motherboard_chip': sensor_data.get('motherboard_chip'),
            'timestamp': datetime.now().isoformat()
        }
        
        # Motherboard temps
        if sensor_data.get('motherboard'):
            temps['motherboard'] = sensor_data['motherboard']
        
        # GPU temps - now supports any GPU device
        if sensor_data.get('amdgpu_devices'):
            for gpu_id, gpu_data in sensor_data['amdgpu_devices'].items():
                temps['gpu'][gpu_id] = gpu_data
        
        # Storage temps
        if sensor_data.get('nvme'):
            temps['storage'] = sensor_data['nvme']
        
        return temps

class TempAnalyzer:
    """Analyze temperature readings and provide status"""
    
    @staticmethod
    def get_status(temp: Optional[float], safe_max: float) -> Dict:
        """Determine status based on temperature"""
        if temp is None:
            return {'status': 'unknown', 'color': 'gray', 'percent': 0}
        
        percent = (temp / safe_max) * 100
        
        if temp < safe_max * 0.6:
            return {'status': 'idle', 'color': 'green', 'percent': percent}
        elif temp < safe_max * 0.85:
            return {'status': 'normal', 'color': 'yellow', 'percent': percent}
        else:
            return {'status': 'hot', 'color': 'red', 'percent': percent}
    
    @staticmethod
    def analyze_all(temps: Dict) -> Dict:
        """Analyze all temperatures"""
        analysis = {
            'cpu': TempAnalyzer.get_status(temps['cpu'], 85),
            'motherboard': {},
            'gpu': {},
            'storage': {},
            'overall_status': 'healthy'
        }
        
        # Analyze motherboard
        for key, temp in temps['motherboard'].items():
            analysis['motherboard'][key] = TempAnalyzer.get_status(temp, 80)
        
        # Analyze GPU - handles any GPU device now
        for gpu_id, gpu_data in temps['gpu'].items():
            if isinstance(gpu_data, dict) and 'edge' in gpu_data:
                analysis['gpu'][gpu_id] = TempAnalyzer.get_status(gpu_data['edge'], 85)
        
        # Analyze storage
        for drive_id, temp in temps['storage'].items():
            analysis['storage'][drive_id] = TempAnalyzer.get_status(temp, 60)
        
        # Determine overall status
        all_temps = [temps['cpu']] if temps['cpu'] else []
        all_temps.extend(temps['motherboard'].values())
        for gpu_data in temps['gpu'].values():
            if isinstance(gpu_data, dict) and 'edge' in gpu_data:
                all_temps.append(gpu_data['edge'])
        all_temps.extend(temps['storage'].values())
        
        max_temp = max(all_temps) if all_temps else 0
        if max_temp > 80:
            analysis['overall_status'] = 'critical'
        elif max_temp > 70:
            analysis['overall_status'] = 'warning'
        elif max_temp > 50:
            analysis['overall_status'] = 'elevated'
        else:
            analysis['overall_status'] = 'healthy'
        
        return analysis

# Routes
@app.route('/api/temps', methods=['GET'])
def get_temps():
    """Get current temperatures"""
    proxied = proxy_json('/api/temps')
    if proxied is not None:
        return proxied

    temps = SensorReader.get_all_temps()
    return jsonify(temps)

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get system status"""
    proxied = proxy_json('/api/status')
    if proxied is not None:
        return proxied

    temps = SensorReader.get_all_temps()
    analysis = TempAnalyzer.analyze_all(temps)
    return jsonify(analysis)

@app.route('/api/health', methods=['GET'])
def get_health():
    """Get overall system health"""
    proxied = proxy_json('/api/health')
    if proxied is not None:
        return proxied

    try:
        temps = SensorReader.get_all_temps()
        analysis = TempAnalyzer.analyze_all(temps)
        
        health = {
            'status': 'online',
            'overall': analysis['overall_status'],
            'cpu_temp': temps['cpu'],
            'last_update': temps['timestamp']
        }
        
        return jsonify(health)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/sensors', methods=['GET'])
def get_sensors():
    """Get sensor data in kiosk-friendly format"""
    proxied = proxy_json('/api/sensors')
    if proxied is not None:
        return proxied

    try:
        temps = SensorReader.get_all_temps()
        
        # Extract key temperatures
        data = {
            'cpu_temp': temps.get('cpu'),
            'cpu_sensor': temps.get('cpu_sensor'),
            'gpu_temp': None,
            'chipset_temp': None,
            'chipset_sensor': None,
            'vrm_temp': None,
            'vrm_sensor': None,
            'nvme_temp': None,
            'unit': 'C',
            'timestamp': temps.get('timestamp'),
            'motherboard_chip': temps.get('motherboard_chip')
        }
        
        # GPU temp selection policy:
        # 1) Prefer amdgpu-pci-0300 (matches the main dashboard label)
        # 2) Else prefer a GPU that reports fan/pwm telemetry (usually dGPU)
        # 3) Else use the highest available edge temp
        if temps.get('gpu'):
            gpu_map = temps['gpu']

            preferred_gpu = gpu_map.get('amdgpu-pci-0300')
            if isinstance(preferred_gpu, dict):
                data['gpu_temp'] = preferred_gpu.get('edge') or preferred_gpu.get('junction')

            if data['gpu_temp'] is None:
                for gpu_data in gpu_map.values():
                    if isinstance(gpu_data, dict) and ('fan_rpm' in gpu_data or 'pwm' in gpu_data):
                        data['gpu_temp'] = gpu_data.get('edge') or gpu_data.get('junction')
                        if data['gpu_temp'] is not None:
                            break

            if data['gpu_temp'] is None:
                edge_temps = []
                for gpu_data in gpu_map.values():
                    if isinstance(gpu_data, dict) and isinstance(gpu_data.get('edge'), (int, float)):
                        edge_temps.append(gpu_data['edge'])
                if edge_temps:
                    data['gpu_temp'] = max(edge_temps)
            if data['gpu_temp'] is not None:
                data['gpu_sensor'] = 'amdgpu:edge/junction'
        
        data['chipset_temp'] = temps.get('chipset')
        data['chipset_sensor'] = temps.get('chipset_sensor')

        data['vrm_temp'] = temps.get('vrm')
        data['vrm_sensor'] = temps.get('vrm_sensor')
        
        # NVMe temps (all drives)
        data['nvme_temps'] = {}
        if temps.get('storage'):
            nvme_list = [(k, v) for k, v in temps['storage'].items() if isinstance(v, (int, float))]
            # Sort by drive ID for consistent ordering
            nvme_list.sort(key=lambda x: x[0])
            for drive_id, nvme_temp in nvme_list:
                data['nvme_temps'][drive_id] = nvme_temp
        
        return jsonify(data)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/info', methods=['GET'])
def get_info():
    """Get system information (hostname, uptime, etc)"""
    proxied = proxy_json('/api/info')
    if proxied is not None:
        return proxied

    try:
        hostname = socket.gethostname()
        uptime = subprocess.run("uptime -p 2>/dev/null || echo 'unknown'", shell=True, capture_output=True, text=True).stdout.strip()
        board = get_board_identity()
        
        info = {
            'hostname': hostname,
            'uptime': uptime,
            'board_name': board['board_name'],
            'chipset': board['chipset'],
            'board_source': board['source'],
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(info)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/dashboard')
def dashboard():
    """Serve the web dashboard (loads HTML file)"""
    try:
        dashboard_path = os.path.join(os.path.dirname(__file__), 'am5_system_monitor.html')
        if os.path.exists(dashboard_path):
            with open(dashboard_path, 'r', encoding='utf-8') as f:
                return render_template_string(f.read())
    except Exception as e:
        print(f"Error loading dashboard: {e}")
    
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>AM5 System Monitor</title>
        <style>
            body {
                background: #0f172a;
                color: #f1f5f9;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 40px;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
            }
            .container {
                text-align: center;
                background: rgba(30, 41, 59, 0.4);
                padding: 40px;
                border-radius: 12px;
                border: 1px solid #334155;
                max-width: 600px;
            }
            h1 {
                color: #00d9ff;
                margin: 0 0 20px 0;
            }
            p {
                color: #cbd5e1;
                line-height: 1.6;
                margin: 10px 0;
            }
            a {
                color: #00d9ff;
                text-decoration: none;
                font-weight: bold;
            }
            a:hover {
                text-decoration: underline;
            }
            code {
                background: #1a1f35;
                padding: 2px 6px;
                border-radius: 4px;
                color: #00d9ff;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>⚙️ AM5 System Monitor</h1>
            <p>API is running! Access temperature data at:</p>
            <p><code>/api/temps</code> - Current temperatures</p>
            <p><code>/api/status</code> - System status</p>
            <p><code>/api/health</code> - Overall health</p>
            <p style="margin-top: 30px; border-top: 1px solid #334155; padding-top: 30px;">
                The dashboard HTML file should be in the same directory as this script.
            </p>
            <p>
                <a href="/api/health">Check System Health →</a>
            </p>
        </div>
    </body>
    </html>
    '''

@app.route('/kiosk')
def kiosk():
    """Serve the simplified kiosk display (optimized for 5-inch screens)"""
    try:
        kiosk_path = os.path.join(os.path.dirname(__file__), 'am5_system_monitor_kiosk.html')
        if os.path.exists(kiosk_path):
            with open(kiosk_path, 'r', encoding='utf-8') as f:
                return render_template_string(f.read())
    except Exception as e:
        print(f"Error loading kiosk: {e}")
    
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>AM5 Kiosk</title>
        <meta http-equiv="refresh" content="0;url=/dashboard" />
    </head>
    <body>Kiosk file not found, redirecting...</body>
    </html>
    '''

@app.route('/')
def index():
    """Redirect to dashboard"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta http-equiv="refresh" content="0;url=/dashboard" />
    </head>
    <body>
        Redirecting to dashboard...
    </body>
    </html>
    '''

def print_banner():
    """Print startup banner"""
    print(f"\n{Colors.CYAN}{'='*60}")
    print(f"{Colors.BLUE}  AM5 SYSTEM MONITOR - Backend Server")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")
    print(f"{Colors.GREEN}✓ Server starting...{Colors.RESET}")
    if proxy_enabled():
        print(f"  Mode: {Colors.YELLOW}REMOTE API PROXY{Colors.RESET}")
        print(f"  Upstream: {Colors.CYAN}{UPSTREAM_API_BASE}{Colors.RESET}")
    else:
        print(f"  Mode: {Colors.GREEN}LOCAL SENSOR SOURCE{Colors.RESET}")
    print(f"  Dashboard: {Colors.CYAN}http://localhost:5000/dashboard{Colors.RESET}")
    print(f"  Kiosk (5\", small): {Colors.CYAN}http://localhost:5000/kiosk{Colors.RESET}")
    print(f"  API Temps: {Colors.CYAN}http://localhost:5000/api/temps{Colors.RESET}")
    print(f"  API Sensors: {Colors.CYAN}http://localhost:5000/api/sensors{Colors.RESET}")
    print(f"  API Info: {Colors.CYAN}http://localhost:5000/api/info{Colors.RESET}")
    print(f"  API Health: {Colors.CYAN}http://localhost:5000/api/health{Colors.RESET}")
    print(f"\n{Colors.YELLOW}Press Ctrl+C to stop{Colors.RESET}\n")

def main() -> None:
    """Run the Flask server entrypoint."""
    print_banner()
    try:
        # Test sensor reading
        print(f"{Colors.BLUE}Testing sensor access...{Colors.RESET}")
        temps = SensorReader.get_all_temps()
        if temps['cpu']:
            print(f"{Colors.GREEN}✓ CPU Temperature: {temps['cpu']}°C{Colors.RESET}")
        if temps['motherboard']:
            print(f"{Colors.GREEN}✓ Motherboard sensors available{Colors.RESET}")
        if temps['gpu']:
            print(f"{Colors.GREEN}✓ GPU sensors available{Colors.RESET}")
        if temps['storage']:
            print(f"{Colors.GREEN}✓ Storage sensors available{Colors.RESET}")
        print()
        
        # Start server
        app.run(host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Server stopped.{Colors.RESET}\n")
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.RESET}")
        print("\nMake sure to install dependencies:")
        print("  pip install --break-system-packages flask flask-cors")


if __name__ == '__main__':
    main()
