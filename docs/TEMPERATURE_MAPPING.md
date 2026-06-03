# ASUS X870E + AMD System - Temperature Mapping Reference

## Your Hardware Detected

```
Motherboard:    ASUS ROG Strix X870E-E Gaming WiFi
Chipset:        AMD X870E
CPU:            AMD Ryzen (assumed - based on sensor data)
GPU:            AMD Radeon (dGPU or integrated)
Storage:        3x NVMe SSDs
OS:             Arch Linux
```

---

## Temperature Sensors Explained

### Motherboard Sensors (gigabyte_wmi)

```
temp1: +30.0°C  → Chipset or power stage temp (VRM area)
temp2: +48.0°C  → CPU Package temp or Chipset
temp3: +43.0°C  → Another voltage regulator or sensor
temp4: +34.0°C  → Possible Board temp
temp5: +39.0°C  → Another power stage
temp6: +43.0°C  → SoC or peripheral temp
```

**Most Important**: These are **ambient/chipset readings**, not CPU die temp.

### CPU Temperature

Your actual CPU die temperature is available via:

```bash
cat /sys/class/thermal/thermal_zone0/temp
# Divide by 1000 to get Celsius
# Example: 38000 = 38.0°C
```

This is your **primary thermal indicator**.

### GPU (amdgpu-pci-0300)

```
edge:       +38.0°C     → GPU die temperature
junction:   +44.0°C     → GPU core temp (more accurate)
mem:        +50.0°C     → GPU memory temperature
fan1:       0 RPM       → GPU fan (0 when cool)
pwm1:       0%          → GPU fan PWM control
```

**GPU is idle** (0 RPM, 38°C).

### NVMe Temperatures

```
nvme-pci-0f00  Composite: +40.9°C
nvme-pci-0400  Composite: +36.9°C
nvme-pci-1200  Composite: +38.9°C
```

**All SSDs healthy** (well under 60°C limit).

---

## Normal Temperature Ranges

| Component | Idle | Load | Throttle | Emergency |
|-----------|------|------|----------|-----------|
| **CPU** | 30-45°C | 60-85°C | 85-95°C | 100°C+ |
| **GPU** | 25-45°C | 60-85°C | 90°C | 115°C |
| **Chipset (MB)** | 30-50°C | 50-70°C | N/A | N/A |
| **NVMe** | 25-40°C | 50-65°C | 70°C | 80°C |
| **VRM** | 35-50°C | 60-80°C | N/A | N/A |

---

## Monitoring Commands for Your System

### Quick Temperature Check
```bash
# All sensors
sensors

# CPU only
cat /sys/class/thermal/thermal_zone0/temp | awk '{printf "CPU: %.1f°C\n", $1/1000}'

# Motherboard
sensors gigabyte_wmi-virtual-0

# GPU
sensors amdgpu-pci-0300

# SSDs
sensors nvme-pci-0f00
sensors nvme-pci-0400
sensors nvme-pci-1200
```

### Real-Time Monitoring
```bash
# All temps every 1 second
watch -n1 sensors

# CPU temp with graph
watch -n1 'cat /sys/class/thermal/thermal_zone0/temp | awk "{printf \"CPU: %.1f°C\n\", \$1/1000}"'

# GUI monitoring
psensor
```

### During CPU Stress
```bash
# Terminal 1: Run stress test
sudo pacman -S stress-ng
stress-ng --cpu 0 --timeout 60s

# Terminal 2: Monitor temps
watch -n1 'echo "CPU:" && cat /sys/class/thermal/thermal_zone0/temp | awk "{printf \"%.1f°C\n\", \$1/1000}" && echo "" && echo "Motherboard:" && sensors gigabyte_wmi-virtual-0 | head -5'
```

---

## BIOS Fan Control Configuration

Since you **cannot** control motherboard fans via Linux (not exposed), use BIOS:

### Access BIOS
1. Reboot system
2. Press **DEL** or **F2** immediately after power button
3. Enter BIOS Setup

### Navigate to Fan Settings
```
Power
  ↓
Thermal Management (or Smart Fan Control)
  ↓
CPU Fan / SYS Fan / AIO Pump
```

### Recommended Settings

**Conservative Profile (Quiet)**
```
CPU Fan:
  30°C: 30%
  40°C: 35%
  50°C: 45%
  60°C: 60%
  70°C: 80%
  80°C: 100%

SYS Fan:
  30°C: 25%
  40°C: 30%
  50°C: 45%
  60°C: 65%
  70°C: 85%
  80°C: 100%
```

**Balanced Profile (Recommended)**
```
CPU Fan:
  30°C: 35%
  45°C: 45%
  60°C: 65%
  75°C: 90%
  80°C: 100%

SYS Fan:
  30°C: 30%
  45°C: 40%
  60°C: 60%
  75°C: 85%
  80°C: 100%
```

**Aggressive Profile (Max Cooling)**
```
CPU Fan:
  30°C: 50%
  50°C: 75%
  70°C: 100%

SYS Fan:
  30°C: 45%
  50°C: 70%
  70°C: 100%
```

### Save Changes
1. Press **F10**
2. Select **Yes** to save
3. System reboots

---

## Testing Fan Curves

### After Configuring BIOS

**Test 1: Idle (Fans should be quiet)**
```bash
# Let system sit 5 minutes
sleep 300

# Check temp
sensors gigabyte_wmi-virtual-0
cat /sys/class/thermal/thermal_zone0/temp | awk '{printf "CPU: %.1f°C\n", $1/1000}'

# Expected: CPU 30-45°C, fans at 30-40% speed
```

**Test 2: Load (Fans should ramp up)**
```bash
# Install stress test (if not already)
sudo pacman -S stress-ng

# Run 60-second CPU test
stress-ng --cpu 0 --timeout 60s

# In another terminal, monitor temps
watch -n1 sensors
```

Expected behavior:
- CPU temp climbs to 70-85°C
- Fans ramp to 70-100%
- After stress ends, temps drop and fans slow down
- No sudden temperature spikes

---

## GPU Fan Control (Optional)

If you want to control your GPU fan manually:

```bash
# Check current GPU status
sensors amdgpu-pci-0300

# Set GPU fan to specific speed (0-255)
# Examples:
echo 0 | sudo tee /sys/class/hwmon/hwmon4/pwm1    # Off
echo 100 | sudo tee /sys/class/hwmon/hwmon4/pwm1  # ~40%
echo 150 | sudo tee /sys/class/hwmon/hwmon4/pwm1  # ~60%
echo 200 | sudo tee /sys/class/hwmon/hwmon4/pwm1  # ~80%
echo 255 | sudo tee /sys/class/hwmon/hwmon4/pwm1  # 100%

# Verify
sensors amdgpu-pci-0300 | grep pwm1
```

**Note**: GPU fan control changes at runtime are **not persistent** after reboot. For permanent control, use BIOS or create a systemd service.

---

## Why You Don't See Motherboard Fan PWM in Linux

```
Expected (some boards):
  /sys/class/hwmon/hwmon6/pwm1  ← For CPU fan
  /sys/class/hwmon/hwmon6/pwm2  ← For SYS fan

Your System:
  /sys/class/hwmon/hwmon4/pwm1  ← GPU fan only
  /sys/class/hwmon/hwmon6/      ← gigabyte_wmi (temperature monitoring only)
```

**Why?**
- Gigabyte B650 EAGLE AX uses proprietary firmware for fan control
- ITE IT8792 chip handles fans but doesn't expose PWM via standard Linux drivers
- Gigabyte locked it to BIOS for stability/warranty reasons
- This is actually **safer** than Linux-based control

---

## Troubleshooting

### CPU Running Hot (85°C+)
```bash
1. Check BIOS settings (temperatures correct?)
2. Verify CPU cooler is properly installed
3. Check fan curves are aggressive enough
4. Monitor CPU frequency (may be throttling)
5. Clean cooler and case of dust
```

### Fans Always at 100%
```bash
1. Check BIOS throttle temperature (set too low?)
2. Verify fan is actually spinning (visual check)
3. Check if there's a sensor failure (unreliable reading)
4. Reset BIOS to defaults (Q-Flash → CMOS)
```

### One Fan Not Working
```bash
1. Check physical connection at motherboard header
2. Verify fan header is enabled in BIOS
3. Test with manual PWM control (if available)
4. Replace fan if defective
```

### Inconsistent Temperature Readings
```bash
1. Ensure sensors-detect ran successfully
2. Check BIOS temperature offsets (if option exists)
3. Verify thermal paste on CPU cooler
4. Run multiple monitoring tools to cross-check
```

---

## Useful Commands for Your System

```bash
# One-liner: All temps at once
sensors

# Watch CPU temp constantly
watch -n1 'cat /sys/class/thermal/thermal_zone0/temp | awk "{printf \"CPU: %.1f°C\n\", \$1/1000}"'

# Motherboard specific
sensors gigabyte_wmi-virtual-0

# GPU with fan status
sensors amdgpu-pci-0300 | grep -E "fan1|edge|pwm1"

# All NVMe temps
echo "=== NVMe 1 ===" && sensors nvme-pci-0f00 | head -4
echo "=== NVMe 2 ===" && sensors nvme-pci-0400 | head -4
echo "=== NVMe 3 ===" && sensors nvme-pci-1200 | head -4

# CPU frequency (during load)
watch -n1 'cat /proc/cpuinfo | grep MHz | head -4'

# Real-time system stats (includes temps)
btop

# GUI monitoring
psensor
```

---

## Your Next Steps

1. **Boot into BIOS** (DEL/F2 during startup)
2. **Go to Power → Thermal Settings**
3. **Choose a profile** (Balanced recommended)
4. **Save and exit** (F10)
5. **Test idle**: Wait 5 min, check temps
6. **Test load**: Run `stress-ng --cpu 0 --timeout 60s`
7. **Monitor**: Use `watch -n1 sensors`
8. **Adjust if needed**: Reboot to BIOS and tweak

---

## Files on Your System

```
/sys/class/hwmon/hwmon0/          ← ACPI (minimal data)
/sys/class/hwmon/hwmon4/          ← AMD GPU (amdgpu)
/sys/class/hwmon/hwmon6/          ← Motherboard (gigabyte_wmi)
/sys/class/thermal/thermal_zone0/ ← CPU thermal zone
/proc/cpuinfo                      ← CPU info + frequency
/sys/class/hwmon/hwmon*/temp*_input ← All temp sensors (in millidegrees)
```

---

## Summary Table

| Aspect | Your System | Status |
|--------|-------------|--------|
| Temperature Monitoring | ✅ Working | gigabyte_wmi, thermal_zone0 |
| Motherboard PWM Control | ❌ Not Available | Use BIOS instead |
| GPU Fan Control | ✅ Available | Manual PWM possible |
| SSD Monitoring | ✅ Working | All 3 NVMe visible |
| CPU Frequency Scaling | ✅ Working | /proc/cpuinfo shows dynamic freq |
| BIOS Control | ✅ Recommended | DEL/F2 at boot |

---

**Last Updated**: 2025  
**Your Hardware**: B650 EAGLE AX + AMD CPU/GPU, Arch Linux  
**Recommended Action**: Configure fan curves in BIOS (Power → Thermal Settings)
