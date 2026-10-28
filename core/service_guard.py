"""
PyMint IDE - Service Guard & Memory Monitor
Tracks system RAM (/proc/meminfo) and manages background services
(Docker, PostgreSQL, MongoDB, Redis) to preserve 3.9 GB hardware limits.
"""

import os
from PyQt6.QtCore import QObject, QTimer, QProcess, pyqtSignal
from core.config import LOW_RAM_ALERT_MB, RAM_CHECK_INTERVAL_MS


class MemoryMonitor(QObject):
    """Zero-overhead memory monitor reading /proc pseudo-filesystem."""
    # available_mb, total_mb, ide_rss_mb, is_low_ram
    memory_updated = pyqtSignal(int, int, int, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.timer = QTimer(self)
        self.timer.setInterval(RAM_CHECK_INTERVAL_MS)
        self.timer.timeout.connect(self.check_memory)
        self.timer.start()
        self.check_memory()

    def check_memory(self):
        """Reads /proc/meminfo and /proc/self/status."""
        total_mb = 3900
        avail_mb = 2000
        rss_mb = 30

        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        total_mb = int(line.split()[1]) // 1024
                    elif line.startswith("MemAvailable:"):
                        avail_mb = int(line.split()[1]) // 1024
        except Exception:
            pass

        try:
            with open("/proc/self/status", "r") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        rss_mb = int(line.split()[1]) // 1024
                        break
        except Exception:
            pass

        is_low = avail_mb < LOW_RAM_ALERT_MB
        self.memory_updated.emit(avail_mb, total_mb, rss_mb, is_low)


class ServiceGuard(QObject):
    """Manages system services (Docker, Postgres, Mongo, Redis) with 1-click."""
    service_status_changed = pyqtSignal(str, bool)      # service, is_active
    containers_updated = pyqtSignal(list)               # [{"name": ..., "status": ...}]
    action_completed = pyqtSignal(str, bool, str)       # action_desc, success, output

    SERVICES = ["docker", "postgresql", "mongod", "redis-server"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._check_processes = {}
        self._action_processes = set()

    def stop_all(self):
        """Terminates active monitoring processes."""
        for proc in list(self._check_processes.values()) + list(self._action_processes):
            try:
                proc.kill()
                proc.waitForFinished(50)
            except Exception:
                pass
        self._check_processes.clear()
        self._action_processes.clear()

    def check_all_services(self):
        """Check all tracked services."""
        for s in self.SERVICES:
            self.check_service(s)

    def check_service(self, service_name: str):
        """Checks status of single service with systemctl is-active."""
        proc = QProcess(self)
        self._check_processes[service_name] = proc

        def on_finished(exit_code, exit_status):
            try:
                output = bytes(proc.readAllStandardOutput()).decode("utf-8").strip()
                self._check_processes.pop(service_name, None)
                proc.deleteLater()
            except RuntimeError:
                return
            is_active = (output == "active")
            self.service_status_changed.emit(service_name, is_active)

        proc.finished.connect(on_finished)
        proc.start("systemctl", ["is-active", service_name])

    def toggle_service(self, service_name: str, currently_active: bool):
        """Starts or stops service using pkexec (Cinnamon polkit GUI prompt)."""
        action = "stop" if currently_active else "start"
        proc = QProcess(self)

        def on_finished(exit_code, exit_status):
            try:
                proc.deleteLater()
            except RuntimeError:
                return
            self.check_service(service_name)
            success = (exit_code == 0)
            self.action_completed.emit(
                f"{action.capitalize()} {service_name}",
                success,
                "Success" if success else "Failed or Cancelled",
            )

        proc.finished.connect(on_finished)
        proc.start("pkexec", ["systemctl", action, service_name])

    def refresh_docker_containers(self):
        """Lists active docker containers asynchronously."""
        proc = QProcess(self)
        self._action_processes.add(proc)

        def on_finished(exit_code, exit_status):
            self._action_processes.discard(proc)
            try:
                output = bytes(proc.readAllStandardOutput()).decode("utf-8").strip()
                proc.deleteLater()
            except RuntimeError:
                return

            containers = []
            if exit_code == 0 and output:
                for line in output.splitlines():
                    parts = line.split("\t")
                    if len(parts) >= 2:
                        containers.append({"name": parts[0].strip(), "status": parts[1].strip()})
                    elif len(parts) == 1:
                        containers.append({"name": parts[0].strip(), "status": "Running"})
            self.containers_updated.emit(containers)

        proc.finished.connect(on_finished)
        proc.start("docker", ["ps", "--format", "{{.Names}}\t{{.Status}}"])

    def stop_container(self, name: str):
        """Stops a container."""
        proc = QProcess(self)
        self._action_processes.add(proc)
        def on_finished(exit_code, exit_status):
            self._action_processes.discard(proc)
            proc.deleteLater()
            self.refresh_docker_containers()
        proc.finished.connect(on_finished)
        proc.start("docker", ["stop", name])

    def compose_up(self, project_dir: str):
        """Runs docker compose up -d."""
        proc = QProcess(self)
        self._action_processes.add(proc)
        def on_finished(exit_code, exit_status):
            self._action_processes.discard(proc)
            proc.deleteLater()
            self.refresh_docker_containers()
            self.action_completed.emit("Compose Up", exit_code == 0, "Finished")
        proc.finished.connect(on_finished)
        proc.setWorkingDirectory(project_dir)
        proc.start("docker", ["compose", "up", "-d"])

    def compose_down(self, project_dir: str):
        """Runs docker compose down."""
        proc = QProcess(self)
        self._action_processes.add(proc)
        def on_finished(exit_code, exit_status):
            self._action_processes.discard(proc)
            proc.deleteLater()
            self.refresh_docker_containers()
            self.action_completed.emit("Compose Down", exit_code == 0, "Finished")
        proc.finished.connect(on_finished)
        proc.setWorkingDirectory(project_dir)
        proc.start("docker", ["compose", "down"])
