import asyncio
import psutil
import time
from typing import Dict, Any

live_system_stats: Dict[str, Any] = {
    "cpu": 0.0,
    "ram_pct": 0.0,
    "ram_used": 0.0,
    "ram_total": 0.0,
    "disk_pct": 0.0,
    "disk_used": 0.0,
    "disk_total": 0.0,
    "net_sent": 0.0,
    "net_recv": 0.0
}


async def monitor_system():
    last_net_io = psutil.net_io_counters()
    last_net_time = time.time()

    while True:
        try:
            # CPU & RAM (These are standard across all OS)
            live_system_stats["cpu"] = psutil.cpu_percent(interval=1)
            vm = psutil.virtual_memory()
            live_system_stats["ram_total"] = round(vm.total / (1024 ** 3), 1)
            live_system_stats["ram_used"] = round((vm.total - vm.available) / (1024 ** 3), 1)
            live_system_stats["ram_pct"] = vm.percent

            # --- SAFE TEMPERATURE CHECK ---
            # Not all systems (especially Mac/Windows) support this via psutil
            try:
                if hasattr(psutil, "sensors_temperatures"):
                    temps = psutil.sensors_temperatures()
                    if temps and 'cpu_thermal' in temps:
                        live_system_stats["cpu_temp"] = temps['cpu_thermal'][0].current
                    elif temps and 'coretemp' in temps:
                        live_system_stats["cpu_temp"] = temps['coretemp'][0].current
                    else:
                        live_system_stats["cpu_temp"] = None
                else:
                    live_system_stats["cpu_temp"] = None
            except Exception:
                live_system_stats["cpu_temp"] = None

            # --- NETWORK & DISK (Wrapped in safety) ---
            try:
                curr_io = psutil.net_io_counters()
                curr_time = time.time()
                elapsed = curr_time - last_net_time
                live_system_stats["net_sent"] = round((curr_io.bytes_sent - last_net_io.bytes_sent) / elapsed / 1024, 1)
                live_system_stats["net_recv"] = round((curr_io.bytes_recv - last_net_io.bytes_recv) / elapsed / 1024, 1)
                last_net_io, last_net_time = curr_io, curr_time
            except:
                pass

            # Smart Disk
            path = '/'
            for p in psutil.disk_partitions():
                if p.mountpoint == '/System/Volumes/Data':
                    path = '/System/Volumes/Data';
                    break
            usage = psutil.disk_usage(path)
            live_system_stats["disk_total"] = round(usage.total / (1024 ** 3), 1)
            live_system_stats["disk_used"] = round(usage.used / (1024 ** 3), 1)
            live_system_stats["disk_pct"] = usage.percent

        except Exception as e:
            # This catch-all ensures the loop NEVER dies
            print(f"⚠️ Internal Monitor Warning: {e}")

        await asyncio.sleep(2)
