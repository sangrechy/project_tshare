"""Dependency Verification and Auto-Installation Subsystem for T-Share v2.

Ensures that all runtime Python packages and platform-level system utilities
(Robocopy on Windows, rsync on Linux/macOS, WebView2/WebKit backends) are available
before launching the application, automatically installing missing pip packages if needed.
"""
from __future__ import annotations

import importlib
import os
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIREMENTS_FILE = os.path.join(BASE_DIR, "requirements.txt")


def check_python_version() -> tuple[bool, str]:
    """Verify minimum supported Python version (3.8+)."""
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 8):
        return False, f"Python 3.8+ is required. Found Python {major}.{minor} ({sys.executable})"
    return True, f"Python {major}.{minor}.{sys.version_info[2]}"


def check_package(package_name: str) -> bool:
    """Check if a Python package can be imported."""
    try:
        importlib.import_module(package_name)
        return True
    except ImportError:
        return False


def check_system_binary(binary_name: str) -> str | None:
    """Check if an executable binary is present in system PATH."""
    return shutil.which(binary_name)


def check_all_dependencies() -> dict[str, Any]:
    """Comprehensive environment audit returning health status and diagnostics."""
    status: dict[str, Any] = {
        "ok": True,
        "python_ok": True,
        "python_version": "",
        "missing_packages": [],
        "installed_packages": [],
        "system_tools": {},
        "warnings": [],
    }

    # 1. Python Version
    py_ok, py_ver = check_python_version()
    status["python_ok"] = py_ok
    status["python_version"] = py_ver
    if not py_ok:
        status["ok"] = False
        status["warnings"].append(py_ver)

    # 2. Python Packages
    critical_packages = ["webview"]
    if sys.platform == "darwin":
        critical_packages.extend(["objc", "WebKit"])

    for pkg in critical_packages:
        if check_package(pkg):
            status["installed_packages"].append(pkg)
        else:
            status["missing_packages"].append(pkg)
            status["ok"] = False

    # 3. Platform Transfer Tools
    if sys.platform.startswith("win"):
        robocopy_path = check_system_binary("robocopy.exe") or check_system_binary("robocopy")
        if not robocopy_path:
            # Check standard System32 location
            sys32_robocopy = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "robocopy.exe")
            if os.path.exists(sys32_robocopy):
                robocopy_path = sys32_robocopy

        status["system_tools"]["robocopy"] = robocopy_path is not None
        if not robocopy_path:
            status["warnings"].append("robocopy.exe was not found in System32 or PATH.")
    else:
        rsync_path = check_system_binary("rsync")
        status["system_tools"]["rsync"] = rsync_path is not None
        if not rsync_path:
            status["warnings"].append(
                "rsync is not installed. High-speed transfers require rsync. "
                "Install it using: 'sudo apt install rsync' (Debian/Ubuntu) or 'sudo dnf install rsync' (Fedora) "
                "or 'brew install rsync' (macOS)."
            )

        if sys.platform.startswith("linux"):
            net_path = check_system_binary("net")
            status["system_tools"]["samba_net"] = net_path is not None
            if not net_path:
                status["warnings"].append(
                    "Samba client tools ('net') are not installed for legacy SMB. "
                    "T-Share includes an autonomous Direct P2P Socket Engine that transfers without Samba! "
                    "If you still wish to enable legacy Windows SMB shares on Linux, install: 'sudo apt install samba smbclient'."
                )

    return status


def install_requirements(requirements_path: str | None = None) -> tuple[bool, str]:
    """Execute pip install for missing dependencies."""
    req_file = requirements_path or REQUIREMENTS_FILE
    if not os.path.exists(req_file):
        # Fallback to direct package install if requirements.txt is absent
        packages = ["pywebview>=5.0.0"]
        if sys.platform == "darwin":
            packages.append("pyobjc-framework-WebKit>=9.0")
        cmd = [sys.executable, "-m", "pip", "install", *packages]
    else:
        cmd = [sys.executable, "-m", "pip", "install", "-r", req_file]

    print(f"[T-Share Setup] Installing required packages using pip: {' '.join(cmd)}")
    try:
        res = subprocess.run(cmd, check=True, text=True, capture_output=True)
        return True, res.stdout
    except subprocess.CalledProcessError as exc:
        err_msg = exc.stderr or exc.stdout or str(exc)
        return False, err_msg
    except Exception as exc:
        return False, str(exc)


def ensure_dependencies(auto_install: bool = True) -> None:
    """Pre-flight check invoked before launching the GUI.

    Automatically resolves missing Python packages via pip so the user
    can simply double-click and run without manual terminal setup.
    """
    audit = check_all_dependencies()

    if audit["missing_packages"]:
        missing_str = ", ".join(audit["missing_packages"])
        print(f"[T-Share Setup] Required Python packages missing: {missing_str}")

        if auto_install:
            print("[T-Share Setup] Auto-installing dependencies now...")
            ok, output = install_requirements()
            if ok:
                print("[T-Share Setup] Dependencies installed successfully.")
                # Verify import resolution
                importlib.invalidate_caches()
                re_audit = check_all_dependencies()
                if not re_audit["ok"] and re_audit["missing_packages"]:
                    print(
                        f"[T-Share Setup] Warning: Packages still missing after installation: {re_audit['missing_packages']}"
                    )
            else:
                print(f"[T-Share Setup] Failed to auto-install dependencies:\n{output}")
                print(f"[T-Share Setup] Please manually run: {sys.executable} -m pip install -r {REQUIREMENTS_FILE}")
        else:
            raise RuntimeError(
                f"Missing required packages: {missing_str}. Run 'pip install -r requirements.txt' first."
            )

    # Print any system tool warnings (e.g. missing rsync on Linux)
    for warning in audit.get("warnings", []):
        print(f"[T-Share Setup Warning] {warning}")
