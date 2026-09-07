"""Single instance guard."""

from __future__ import annotations

import ctypes
import sys

from . import __version__

_MUTEX_HANDLE = None
MUTEX_NAME = "Global\\DeskHide_Mutex_vlx0"
WINDOW_TITLE = "DeskHide — darkshade"

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
SW_RESTORE = 9
MB_ICONINFORMATION = 0x40


def claim_or_exit() -> None:
    global _MUTEX_HANDLE
    kernel32.SetLastError(0)
    _MUTEX_HANDLE = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if kernel32.GetLastError() == 183:
        if not _focus_existing():
            user32.MessageBoxW(
                0,
                "DeskHide уже работает в фоне.\nИконка — у часов в трее.",
                f"DeskHide {__version__}",
                MB_ICONINFORMATION,
            )
        sys.exit(0)


def _focus_existing() -> bool:
    hwnd = user32.FindWindowW(None, WINDOW_TITLE)
    if not hwnd:
        return False
    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.SetForegroundWindow(hwnd)
    return True
