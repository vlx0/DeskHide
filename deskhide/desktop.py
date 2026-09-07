"""Hide / show Windows desktop icons."""

from __future__ import annotations

import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

SW_HIDE = 0
SW_SHOW = 5
GW_CHILD = 5
GW_HWNDNEXT = 2
SMTO_NORMAL = 0x0000
SMTO_ABORTIFHUNG = 0x0002

EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND
user32.FindWindowExW.argtypes = [wintypes.HWND, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowExW.restype = wintypes.HWND
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClassNameW.restype = ctypes.c_int
user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetWindow.restype = wintypes.HWND
user32.SendMessageTimeoutW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
    wintypes.UINT,
    wintypes.UINT,
    ctypes.POINTER(ctypes.c_size_t),
]
user32.SendMessageTimeoutW.restype = wintypes.LPARAM
user32.EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL


def _class_name(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def _find_defview_under(parent: int) -> int:
    return int(user32.FindWindowExW(parent, None, "SHELLDLL_DefView", None) or 0)


def _listview_from_defview(defview: int) -> int:
    if not defview:
        return 0
    # Prefer FolderView title, then any SysListView32
    lv = int(user32.FindWindowExW(defview, None, "SysListView32", "FolderView") or 0)
    if lv:
        return lv
    return int(user32.FindWindowExW(defview, None, "SysListView32", None) or 0)


def find_desktop_listview() -> int:
    """Return HWND of the desktop icon ListView, or 0."""
    progman = int(user32.FindWindowW("Progman", None) or 0)
    if progman:
        # Spawns WorkerW on some Windows builds (wallpaper host).
        result = ctypes.c_size_t(0)
        user32.SendMessageTimeoutW(
            progman,
            0x052C,
            0,
            0,
            SMTO_NORMAL | SMTO_ABORTIFHUNG,
            1000,
            ctypes.byref(result),
        )
        defview = _find_defview_under(progman)
        lv = _listview_from_defview(defview)
        if lv:
            return lv

    found: list[int] = []

    @EnumWindowsProc
    def _enum(hwnd, _lp):
        if _class_name(int(hwnd)) == "WorkerW":
            defview = _find_defview_under(int(hwnd))
            lv = _listview_from_defview(defview)
            if lv:
                found.append(lv)
                return False
        return True

    user32.EnumWindows(_enum, 0)
    return found[0] if found else 0


def icons_visible() -> bool | None:
    hwnd = find_desktop_listview()
    if not hwnd or not user32.IsWindow(hwnd):
        return None
    return bool(user32.IsWindowVisible(hwnd))


def set_icons_visible(visible: bool) -> bool:
    hwnd = find_desktop_listview()
    if not hwnd or not user32.IsWindow(hwnd):
        return False
    user32.ShowWindow(hwnd, SW_SHOW if visible else SW_HIDE)
    return True


def toggle_icons() -> bool | None:
    """Toggle icons. Returns new visible state, or None on failure."""
    state = icons_visible()
    if state is None:
        return None
    ok = set_icons_visible(not state)
    if not ok:
        return None
    return not state
