"""Windows autostart via HKCU Run registry."""

from __future__ import annotations

import sys
import winreg
from pathlib import Path

REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
REG_NAME = "DeskHide"


def launcher_command() -> str:
    root = Path(__file__).resolve().parent.parent
    script = (root / "run_deskhide.pyw").resolve()
    exe = Path(sys.executable).resolve()
    pythonw = exe.with_name("pythonw.exe")
    if not pythonw.is_file():
        pythonw = exe
    return f'"{pythonw}" "{script}" --tray'


def is_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, REG_NAME)
        return True
    except OSError:
        return False


def enable() -> None:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, REG_NAME, 0, winreg.REG_SZ, launcher_command())


def disable() -> None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, REG_NAME)
    except OSError:
        pass


def sync(enabled: bool) -> None:
    if enabled:
        enable()
    else:
        disable()
