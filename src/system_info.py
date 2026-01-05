import asyncio
import psutil
import time
from typing import Optional, Callable, Awaitable, Any

from src.config import config
from src.logger import logger
from src.models import SystemStats, SystemMessage, THERMAL_SENSOR_PRIORITY

live_system_stats: SystemStats = SystemStats.empty()

# Will be set by main.py to avoid circular import
_broadcast_func: Optional[Callable[[dict], Awaitable[None]]] = None


def set_broadcast_func(func: Callable[[dict], Awaitable[None]]) -> None:
    """
    Set the broadcast function from main.py to avoid circular imports.

    Args:
        func: Async function that broadcasts data to all WebSocket clients
    """
    global _broadcast_func
    _broadcast_func = func


def _get_cpu_temperature() -> Optional[float]:
    """Get CPU temperature from available sensors."""
    if not hasattr(psutil, "sensors_temperatures"):
        return None

    temps = psutil.sensors_temperatures()
    if not temps:
        return None

    # Try sensors in priority order
    for sensor in THERMAL_SENSOR_PRIORITY:
        if sensor.value in temps and temps[sensor.value]:
            return temps[sensor.value][0].current

    return None


def check_wifi_connectivity() -> bool:
    """Check if WiFi/network connectivity is available."""
    try:
        net_stats = psutil.net_if_stats()
        net_addrs = psutil.net_if_addrs()

        # Check if any network interface is up and has an IP address
        for iface_name, stats in net_stats.items():
            if stats.isup and iface_name in net_addrs:
                for addr in net_addrs[iface_name]:
                    # Check for IPv4 address (AF_INET = 2)
                    if addr.family == 2 and not addr.address.startswith('127.'):
                        return True
        return False
    except Exception as e:
        logger.debug(f"WiFi check error: {e}")
        return False


async def monitor_system() -> None:
    """Monitor system resources and update live_system_stats."""
    last_net_io = psutil.net_io_counters()
    last_net_time = time.time()

    logger.info("📊 System monitoring started")

    while True:
        try:
            # CPU & RAM
            live_system_stats.cpu = psutil.cpu_percent(interval=None)
            vm = psutil.virtual_memory()
            live_system_stats.ram_total = round(vm.total / (1024 ** 3), 1)
            live_system_stats.ram_used = round((vm.total - vm.available) / (1024 ** 3), 1)
            live_system_stats.ram_pct = vm.percent

            # Temperature (not available on all systems)
            try:
                live_system_stats.cpu_temp = _get_cpu_temperature()
            except Exception as e:
                logger.debug(f"Temperature monitoring not available: {e}")
                live_system_stats.cpu_temp = None

            # Network statistics
            try:
                curr_io = psutil.net_io_counters()
                curr_time = time.time()
                elapsed = curr_time - last_net_time
                if elapsed > 0:
                    live_system_stats.net_sent = round(
                        (curr_io.bytes_sent - last_net_io.bytes_sent) / elapsed / 1024, 1
                    )
                    live_system_stats.net_recv = round(
                        (curr_io.bytes_recv - last_net_io.bytes_recv) / elapsed / 1024, 1
                    )
                last_net_io, last_net_time = curr_io, curr_time
            except Exception as e:
                logger.debug(f"Network monitoring error: {e}")

            # Disk usage (handle macOS special case)
            try:
                path = '/'
                for p in psutil.disk_partitions():
                    if p.mountpoint == '/System/Volumes/Data':
                        path = '/System/Volumes/Data'
                        break

                usage = psutil.disk_usage(path)
                live_system_stats.disk_total = round(usage.total / (1024 ** 3), 1)
                live_system_stats.disk_used = round(usage.used / (1024 ** 3), 1)
                live_system_stats.disk_pct = usage.percent
            except Exception as e:
                logger.debug(f"Disk monitoring error: {e}")

            # Broadcast system stats to all connected clients
            if _broadcast_func:
                message = SystemMessage(system=live_system_stats)
                await _broadcast_func(message.to_dict())

        except Exception as e:
            logger.warning(f"⚠️ System monitor error: {e}")

        await asyncio.sleep(config.SYSTEM_MONITOR_INTERVAL)
