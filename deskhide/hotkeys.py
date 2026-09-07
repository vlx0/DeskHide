"""Global hotkey for toggle (message-only window)."""

from __future__ import annotations

import ctypes
import queue
import threading
from ctypes import wintypes
from typing import Callable

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
WM_HOTKEY = 0x0312
WM_USER_STOP = 0x0402
HWND_MESSAGE = wintypes.HWND(-3)
TOGGLE_ID = 1

# Default: Ctrl+Alt+D
DEFAULT_MOD = MOD_CONTROL | MOD_ALT
DEFAULT_VK = ord("D")

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = LRESULT
user32.CreateWindowExW.restype = wintypes.HWND
user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
user32.RegisterHotKey.restype = wintypes.BOOL
user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
    ]


user32.GetMessageW.argtypes = [ctypes.POINTER(MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.GetMessageW.restype = ctypes.c_int
user32.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
user32.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]
user32.DispatchMessageW.restype = LRESULT


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


def format_hotkey(mod: int = DEFAULT_MOD, vk: int = DEFAULT_VK) -> str:
    parts = []
    if mod & MOD_CONTROL:
        parts.append("Ctrl")
    if mod & MOD_SHIFT:
        parts.append("Shift")
    if mod & MOD_ALT:
        parts.append("Alt")
    parts.append(chr(vk) if ord("A") <= vk <= ord("Z") else f"0x{vk:X}")
    return "+".join(parts)


class HotkeyManager:
    def __init__(self, root, on_toggle: Callable[[], None]) -> None:
        self._root = root
        self._on_toggle = on_toggle
        self._hwnd: int | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._events: queue.SimpleQueue = queue.SimpleQueue()
        self._pump_job = None
        self._wndproc = None
        self.registered = False

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._ready.clear()
        self._thread = threading.Thread(target=self._thread_main, name="deskhide-hk", daemon=True)
        self._thread.start()
        self._ready.wait(timeout=3.0)
        self._pump_job = self._root.after(40, self._pump)

    def stop(self) -> None:
        if self._pump_job is not None:
            try:
                self._root.after_cancel(self._pump_job)
            except Exception:
                pass
        if self._hwnd:
            user32.PostMessageW(self._hwnd, WM_USER_STOP, 0, 0)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
        self._hwnd = None
        self.registered = False

    def _pump(self) -> None:
        try:
            while True:
                self._events.get_nowait()
                self._on_toggle()
        except queue.Empty:
            pass
        self._pump_job = self._root.after(40, self._pump)

    def _thread_main(self) -> None:
        class_name = "DeskHideHotkeyHidden_vlx0"

        @WNDPROC
        def wnd(hwnd, msg, wparam, lparam):
            if msg == WM_HOTKEY and int(wparam) == TOGGLE_ID:
                self._events.put("toggle")
                return 0
            if msg == WM_USER_STOP:
                if self.registered:
                    user32.UnregisterHotKey(hwnd, TOGGLE_ID)
                    self.registered = False
                user32.PostQuitMessage(0)
                return 0
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        self._wndproc = wnd
        hinst = kernel32.GetModuleHandleW(None)
        wc = WNDCLASSW()
        wc.lpfnWndProc = self._wndproc
        wc.hInstance = hinst
        wc.lpszClassName = class_name
        atom = user32.RegisterClassW(ctypes.byref(wc))
        if not atom and ctypes.GetLastError() not in (0, 1410):
            self._ready.set()
            return
        hwnd = user32.CreateWindowExW(
            0, class_name, "DeskHideHK", 0, 0, 0, 0, 0, HWND_MESSAGE, None, hinst, None
        )
        if not hwnd:
            self._ready.set()
            return
        self._hwnd = int(hwnd)
        self.registered = bool(user32.RegisterHotKey(hwnd, TOGGLE_ID, DEFAULT_MOD, DEFAULT_VK))
        self._ready.set()
        msg = MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        self._hwnd = None
