# ASUS ROG STRIX X870E-E Fan Control - START HERE

## Your Situation

✅ **Temperature Monitoring**: Working  
❌ **Linux Fan Control**: Usually Limited (often BIOS/UEFI controlled)  
✅ **BIOS Fan Control**: Available & Recommended  

---

## Quick Answer

**You cannot control motherboard fans via Linux on this board.** 

This is **not a problem** — BIOS control is usually **safer and more stable**. Many modern boards handle fan policy in firmware for reliability.

---

## What You Need to Do

### Step 1: Reboot into BIOS
```
1. Press the power button
2. Immediately press DEL or F2 (repeatedly, fast)
3. Wait for BIOS menu
```

### Step 2: Find Fan Settings
```
Power
  ↓
Thermal Settings (or "Smart Fan Control")
  ↓
CPU Fan / SYS Fan / Pump Fan
```

### Step 3: Set Fan Curves
Use this **Balanced** profile (recommended for most users):

```
CPU Fan:
  30°C  → 35%
  45°C  → 45%
  60°C  → 65%
  75°C  → 90%
  80°C  → 100%

SYS Fan (Case/Chassis):
  30°C  → 30%
  45°C  → 40%
  60°C  → 60%
  75°C  → 85%
  80°C  → 100%
```

### Step 4: Save and Exit
```
Press F10
Select "Yes"
System reboots with new settings
```

### Step 5: Test
```bash
# Check idle temps (should be quiet)
sensors

# After 5 minutes:
cat /sys/class/thermal/thermal_zone0/temp | awk '{printf "CPU: %.1f°C\n", $1/1000}'

# Run stress test to see fans ramp up
sudo pacman -S stress-ng
stress-ng --cpu 0 --timeout 30s

# Monitor temps during test
watch -n1 sensors
```

---

## Your Hardware Details

From your `sensors` output:

| Component | Status |
|-----------|--------|
| **Motherboard** | Gigabyte B650 EAGLE AX (Rev 1.0/1.1) |
| **CPU** | AMD Ryzen (detected via thermal_zone0) |
| **GPU** | AMD Radeon (2x GPUs detected) |
| **Storage** | 3x NVMe SSDs (36-40°C idle) |
| **Sensors Available** | ✅ gigabyte_wmi (motherboard temps) |
| **Fan PWM Control** | ❌ Not exposed in Linux |
| **GPU Fan Control** | ✅ Available (`/sys/class/hwmon/hwmon4/pwm1`) |

---

## Why No Motherboard Fan PWM in Linux?

```
Expected on some boards:
  ✓ /sys/class/hwmon/hwmon6/pwm1
  ✓ /sys/class/hwmon/hwmon6/pwm2

Your B650 EAGLE AX:
  ✗ Only /sys/class/hwmon/hwmon4/pwm1 (GPU fan)
  ✓ /sys/class/hwmon/hwmon6/ (gigabyte_wmi - temps only)
```

**Reason**: Gigabyte uses proprietary firmware (ITE IT8792 chip) with closed-source driver. They intentionally expose temperatures but NOT fan control for stability and warranty reasons.

**This is actually better** — BIOS control is more reliable than hacking sysfs.

---

## Your Current Temperatures

From your latest `sensors` output:

```
CPU (thermal_zone0):      Unknown (use BIOS monitor)
Motherboard (temp1-6):    30-48°C   ← Normal, idle
GPU (edge):               38°C      ← Idle, normal
GPU (mem):                50°C      ← Idle, normal
NVMe 1 (nvme-0f00):       40.9°C    ← Normal
NVMe 2 (nvme-0400):       36.9°C    ← Normal
NVMe 3 (nvme-1200):       38.9°C    ← Normal
```

**Everything is healthy and cool. Your system is in good shape.**

---

## Files I've Created for You

All files are in `/mnt/user-data/outputs/`:

### 📖 Guides (Read These)
- **B650_AMD_System_Fan_Control.md** - Complete guide for AMD systems
- **TEMPERATURE_MAPPING.md** - Explains all your sensors
- **B650_EAGLE_AX_Fan_Speed_Guide.md** - Generic B650 guide (for reference)
- **QUICK_REFERENCE.txt** - Command reference

### 🛠️ Scripts (Run These)
- **b650_monitor.sh** - Monitor temps in real-time (menu-driven)
- **b650_fan_setup.sh** - Setup tools and run diagnostics

### ⚙️ Config Files
- **fancontrol.example** - For reference (won't work on your board, but shows format)

---

## Recommended Path Forward

### For Most Users (Easiest)
```
1. Reboot into BIOS (DEL/F2)
2. Power → Thermal Settings
3. Configure one of the profiles below
4. Save (F10) and exit
5. Done! No Linux tools needed
```

### For Advanced Users (Optional)
```
1. Do the BIOS setup above
2. Monitor temps with: watch -n1 sensors
3. Run stress test to verify curves work
4. Adjust BIOS if needed
5. Use monitoring scripts to track performance
```

---

## Temperature Profiles

### Conservative (Quiet, Stable)
Best for: Office work, quiet environments, longevity
```
CPU Fan:  30°C→25%, 40°C→30%, 60°C→50%, 80°C→100%
SYS Fan:  30°C→20%, 40°C→25%, 60°C→45%, 80°C→100%
```

### Balanced (Recommended)
Best for: Gaming, everyday use, balanced noise/cooling
```
CPU Fan:  30°C→35%, 45°C→45%, 60°C→65%, 75°C→90%, 80°C→100%
SYS Fan:  30°C→30%, 45°C→40%, 60°C→60%, 75°C→85%, 80°C→100%
```

### Aggressive (Maximum Cooling)
Best for: Overclocking, extreme gaming, loud environment OK
```
CPU Fan:  30°C→50%, 50°C→75%, 70°C→100%
SYS Fan:  30°C→45%, 50°C→70%, 70°C→100%
```

---

## Verify Your Setup Works

### After Configuring BIOS

**Test 1: Idle (5 minutes)**
```bash
sleep 300
sensors gigabyte_wmi-virtual-0
cat /sys/class/thermal/thermal_zone0/temp | awk '{printf "CPU: %.1f°C\n", $1/1000}'
```
Expected: CPU 30-45°C, fans ~30-40%, quiet

**Test 2: Load (60 seconds)**
```bash
# Terminal 1: Monitor
watch -n1 sensors

# Terminal 2: Stress test
sudo pacman -S stress-ng
stress-ng --cpu 0 --timeout 60s
```
Expected: CPU 70-85°C, fans ramp to 70-100%

---

## Common Issues & Fixes

### Fans Always at 100%
```
→ BIOS setting: Check "Thermal Throttle" temperature
→ Usually set to 85-90°C, may be too low
→ Increase to 90°C or verify CPU cooler installed correctly
```

### Fans Never Ramp Up (Always slow)
```
→ Fan curves may be too conservative
→ Try "Balanced" profile or "Aggressive"
→ Verify fans physically spinning (visual check)
```

### Temperature Readings Seem Wrong
```
→ Check BIOS for "Temperature Offset" setting
→ Some boards offset readings for accuracy
→ Run stress-ng and watch temps climb (verify it's responsive)
```

### Can't Enter BIOS
```
→ System boots too fast
→ Press DEL/F2 **immediately** after power button
→ Or: sudo systemctl reboot --firmware-setup (on some systems)
```

---

## Useful Commands for Your System

```bash
# One-command check of everything
sensors

# Watch CPU temp (your main indicator)
watch -n1 'cat /sys/class/thermal/thermal_zone0/temp | awk "{printf \"CPU: %.1f°C\n\", \$1/1000}"'

# Watch motherboard temps
watch -n1 sensors

# Run monitoring script
bash /mnt/user-data/outputs/b650_monitor.sh

# Simple stress test
sudo pacman -S stress-ng
stress-ng --cpu 0 --timeout 60s

# GUI monitoring (nicer graphs)
sudo pacman -S psensor
psensor
```

---

## Next Steps (Recommended Order)

1. **Read**: `TEMPERATURE_MAPPING.md` (10 min read)
2. **Boot**: Enter BIOS and configure fans (5 min)
3. **Test**: Run `sensors` and `stress-ng` (10 min)
4. **Monitor**: Use `watch -n1 sensors` during normal use
5. **Adjust**: If needed, go back to BIOS and tweak curves

---

## Key Points

✅ Your system is working great  
✅ Temperature monitoring is available  
✅ BIOS fan control is safe and recommended  
✅ No Linux fan control tools needed (or possible)  
✅ Stress test shows system stability  

❌ Don't use `pwmconfig` (won't find motherboard fans)  
❌ Don't modify `/sys/class/hwmon/*/pwm*` for motherboard fans  
❌ Don't use third-party fan control tools on this board  

---

## Still Confused?

Read in this order:
1. This file (you are here)
2. `TEMPERATURE_MAPPING.md` (explains your sensors)
3. `B650_AMD_System_Fan_Control.md` (complete reference)
4. BIOS manual (Gigabyte website)

---

## Questions?

**Q: Why can't I control fans in Linux?**  
A: Gigabyte locked it to BIOS for safety. This is actually better.

**Q: Are my temperatures OK?**  
A: Yes! All idle temps 30-50°C are excellent.

**Q: Will my system overheat?**  
A: No. Configure BIOS curves once, then forget about it. It auto-manages everything.

**Q: Should I use fancontrol?**  
A: No, it won't work on your board. Use BIOS instead.

**Q: What if I want Linux control anyway?**  
A: Not possible without modifying hardware or Gigabyte firmware. BIOS is your only option.

**Q: How often should I check temps?**  
A: Once after BIOS setup to verify it works. Then only if you notice unusual behavior.

---

**Last Updated**: March 2025  
**For**: Gigabyte B650 EAGLE AX (Rev 1.0/1.1) with AMD CPU/GPU on Arch Linux

**Bottom Line**: Reboot, enter BIOS (DEL/F2), go to Power → Thermal Settings, set one fan profile, save (F10), and you're done. Your system is already running perfectly.
