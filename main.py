import fastapi
import uvicorn
import os
import requests
import ipaddress
import logging
import asyncio
import platform
import sys
import psutil
import datetime # Для расчета времени работы
import subprocess # Для получения более детальной информации о CPU

from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Настройка логирования
activity_logger = logging.getLogger("activity_logger")
activity_logger.setLevel(logging.INFO)
handler = logging.FileHandler("activity.log", mode='a', encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
activity_logger.addHandler(handler)

api = fastapi.FastAPI()

api.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def get_cpu_model_name():
    """Пытается получить более детальное название модели CPU."""
    if platform.system() == "Linux":
        try:
            # Используем lscpu для детального названия модели CPU на Linux
            result = subprocess.run(['lscpu'], capture_output=True, text=True, check=True, timeout=5)
            for line in result.stdout.splitlines():
                if "Model name:" in line:
                    return line.split(":", 1)[1].strip()
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            pass
    elif platform.system() == "Windows":
        try:
            # Используем wmic для названия CPU на Windows
            result = subprocess.run(['wmic', 'cpu', 'get', 'name'], capture_output=True, text=True, check=True, timeout=5)
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                return lines[1].strip()
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            pass
    elif platform.system() == "Darwin": # macOS
        try:
            result = subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'], capture_output=True, text=True, check=True, timeout=5)
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            pass
    return platform.processor() # Возврат к platform.processor() в случае неудачи

def detect_virtualization():
    """Пытается определить, работает ли система в виртуализированной среде."""
    if platform.system() == "Linux":
        # Проверяем наличие общих файлов/директорий гипервизоров
        if os.path.exists("/proc/xen"):
            return "Xen"
        if os.path.exists("/proc/vz"):
            return "OpenVZ"
        if os.path.exists("/dev/vboxguest"):
            return "VirtualBox"
        if os.path.exists("/dev/vmware/vmci") or os.path.exists("/sys/class/dmi/id/product_name") and "VMware" in open("/sys/class/dmi/id/product_name").read():
            return "VMware"
        # Проверяем /proc/cpuinfo на наличие флага hypervisor
        try:
            with open("/proc/cpuinfo", "r") as f:
                content = f.read()
                if "hypervisor" in content:
                    return "Generic Hypervisor (e.g., KVM, Hyper-V)"
        except Exception:
            pass
    # Для Windows можно использовать WMI запросы, но это усложнит кроссплатформенность
    return "Физическая или неизвестная"


@api.get("/", response_class=HTMLResponse)
async def get_root(request: fastapi.Request):
    """
    Обрабатывает корневой URL и возвращает HTML-страницу.
    """
    return templates.TemplateResponse("index.html", {"request": request})

@api.get("/get_server_info")
async def get_server_info_endpoint(request: fastapi.Request):
    """
    Собирает и возвращает подробную информацию о среде сервера в формате JSON.
    """
    server_info = {}

    # 1. Информация о местоположении сервера (переиспользуем логику из исходного проекта)
    server_geo = {"ip": "Недоступно", "country": "Недоступно", "city": ""}
    try:
        res = requests.get("http://ip-api.com/json/", timeout=5)
        res.raise_for_status()
        data = res.json()
        if data.get("status") == "success":
            server_geo["ip"] = data.get("query", "Неизвестно")
            server_geo["country"] = data.get("country", "Неизвестно")
            server_geo["city"] = data.get("city", "Неизвестно")
    except requests.RequestException as e:
        activity_logger.error(f"Server Geo lookup failed: {e}")
    server_info["location"] = server_geo

    # 2. Информация об операционной системе
    boot_time_timestamp = psutil.boot_time()
    boot_time_datetime = datetime.datetime.fromtimestamp(boot_time_timestamp)
    uptime_seconds = (datetime.datetime.now() - boot_time_datetime).total_seconds()
    uptime_str = str(datetime.timedelta(seconds=int(uptime_seconds)))

    server_info["os"] = {
        "system": platform.system(),
        "node_name": platform.node(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor_arch": platform.processor(), # Архитектура процессора
        "uptime": uptime_str,
        "boot_time": boot_time_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "virtualization": detect_virtualization()
    }

    # 3. Информация о процессоре (CPU)
    cpu_freq = psutil.cpu_freq()
    # psutil.getloadavg() доступен только на Unix-подобных системах
    load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
    
    server_info["cpu"] = {
        "model_name": get_cpu_model_name(), # Более детальное название модели CPU
        "physical_cores": psutil.cpu_count(logical=False),
        "logical_cores": psutil.cpu_count(logical=True),
        "current_frequency_mhz": f"{cpu_freq.current:.2f}" if cpu_freq else "N/A",
        "min_frequency_mhz": f"{cpu_freq.min:.2f}" if cpu_freq else "N/A",
        "max_frequency_mhz": f"{cpu_freq.max:.2f}" if cpu_freq else "N/A",
        "usage_percent": psutil.cpu_percent(interval=0.1), # Кратковременное измерение использования
        "load_average_1_min": f"{load_avg[0]:.2f}",
        "load_average_5_min": f"{load_avg[1]:.2f}",
        "load_average_15_min": f"{load_avg[2]:.2f}",
    }

    # 4. Информация об оперативной памяти (RAM)
    virtual_memory = psutil.virtual_memory()
    swap_memory = psutil.swap_memory()
    server_info["memory"] = {
        "total_gb": f"{(virtual_memory.total / (1024**3)):.2f}",
        "available_gb": f"{(virtual_memory.available / (1024**3)):.2f}",
        "used_gb": f"{(virtual_memory.used / (1024**3)):.2f}",
        "percent_used": virtual_memory.percent,
        "swap_total_gb": f"{(swap_memory.total / (1024**3)):.2f}",
        "swap_used_gb": f"{(swap_memory.used / (1024**3)):.2f}",
        "swap_free_gb": f"{(swap_memory.free / (1024**3)):.2f}",
        "swap_percent_used": swap_memory.percent,
    }

    # 5. Информация о дисковом пространстве и I/O
    disk_partitions = []
    for partition in psutil.disk_partitions(all=False): # Только физические разделы
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            disk_partitions.append({
                "device": partition.device,
                "mountpoint": partition.mountpoint,
                "fstype": partition.fstype,
                "total_gb": f"{(usage.total / (1024**3)):.2f}",
                "used_gb": f"{(usage.used / (1024**3)):.2f}",
                "free_gb": f"{(usage.free / (1024**3)):.2f}",
                "percent_used": usage.percent,
            })
        except Exception as e:
            activity_logger.warning(f"Could not get disk usage for {partition.mountpoint}: {e}")
            disk_partitions.append({
                "device": partition.device,
                "mountpoint": partition.mountpoint,
                "fstype": partition.fstype,
                "error": "Не удалось получить информацию о диске"
            })
    server_info["disk_partitions"] = disk_partitions

    disk_io = psutil.disk_io_counters()
    if disk_io:
        server_info["disk_io"] = {
            "read_count": disk_io.read_count,
            "write_count": disk_io.write_count,
            "read_bytes_gb": f"{(disk_io.read_bytes / (1024**3)):.2f}",
            "write_bytes_gb": f"{(disk_io.write_bytes / (1024**3)):.2f}",
        }
    else:
        server_info["disk_io"] = {"error": "Не удалось получить статистику дискового I/O"}


    # 6. Информация о среде Python
    server_info["python"] = {
        "version": sys.version.split('\n')[0], # Берем только первую строку версии
        "executable": sys.executable,
        "platform": sys.platform,
    }
    
    # 7. Информация о сетевых интерфейсах и I/O
    net_if_addrs = psutil.net_if_addrs()
    network_interfaces = {}
    for interface_name, addresses in net_if_addrs.items():
        interface_ips = []
        for addr in addresses:
            if addr.family == ipaddress.AF_INET: # Только IPv4
                interface_ips.append(addr.address)
        if interface_ips:
            network_interfaces[interface_name] = interface_ips
    server_info["network_interfaces"] = network_interfaces

    net_io = psutil.net_io_counters()
    if net_io:
        server_info["network_io"] = {
            "bytes_sent_gb": f"{(net_io.bytes_sent / (1024**3)):.2f}",
            "bytes_recv_gb": f"{(net_io.bytes_recv / (1024**3)):.2f}",
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv,
            "errin": net_io.errin,
            "errout": net_io.errout,
            "dropin": net_io.dropin,
            "dropout": net_io.dropout,
        }
    else:
        server_info["network_io"] = {"error": "Не удалось получить статистику сетевого I/O"}


    return JSONResponse(content=server_info)

if __name__ == "__main__":
    uvicorn.run(api, host="0.0.0.0", port=8000)
