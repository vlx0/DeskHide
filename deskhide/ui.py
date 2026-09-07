"""DeskHide GUI."""

from __future__ import annotations

import ctypes
import tkinter as tk

from . import __version__
from .desktop import icons_visible, set_icons_visible, toggle_icons
from .hotkeys import HotkeyManager, format_hotkey
from .instance import WINDOW_TITLE
from .tray import TrayIcon

BG = "#111111"
FG = "#ffffff"
MUTED = "#999999"
CARD = "#1a1a1a"
LINE = "#2a2a2a"
OK = "#86efac"
WARN = "#f87171"
ACCENT = "#93c5fd"


class DeskHideApp(tk.Tk):
    def __init__(self, start_hidden: bool = False) -> None:
        super().__init__()
        self.title(WINDOW_TITLE)
        self.geometry("420x320")
        self.minsize(360, 280)
        self.configure(bg=BG)
        self._exiting = False
        self._start_hidden = start_hidden
        self._tray: TrayIcon | None = None
        self._hotkeys = HotkeyManager(self, self._on_hotkey_toggle)

        from . import autostart

        # autostart so one notify on PC boot makes sense
        if not autostart.is_enabled():
            autostart.enable()

        pad = tk.Frame(self, bg=BG)
        pad.pack(fill="both", expand=True, padx=24, pady=20)

        tk.Label(pad, text="DeskHide", bg=BG, fg=FG, font=("Segoe UI Semibold", 18)).pack(anchor="w")
        tk.Label(
            pad,
            text="Спрятать или показать иконки рабочего стола",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(4, 18))

        card = tk.Frame(pad, bg=CARD, padx=20, pady=18)
        card.pack(fill="x")

        self._state_lbl = tk.Label(card, text="…", bg=CARD, fg=FG, font=("Segoe UI Semibold", 14))
        self._state_lbl.pack(anchor="center")

        self._toggle_btn = self._mk_btn(card, "Спрятать", self._toggle, primary=True)
        self._toggle_btn.pack(anchor="center", pady=(16, 0))

        self._hint = tk.Label(card, text="", bg=CARD, fg=MUTED, font=("Segoe UI", 9), justify="center")
        self._hint.pack(anchor="center", pady=(12, 0))

        self._status = tk.Label(
            pad,
            text=f"хоткей: {format_hotkey()} · v{__version__}",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 9),
            anchor="w",
        )
        self._status.pack(fill="x", pady=(16, 0))

        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        self._refresh_state()
        self._hotkeys.start()
        if not self._hotkeys.registered:
            self._status.configure(text=f"хоткей {format_hotkey()} занят", fg=WARN)
        self.after(20, self._place_on_primary)
        self.after(200, self._start_tray)
        if start_hidden:
            self.after(300, self.hide_to_tray)

    def _mk_btn(self, parent, text, cmd, primary=False, danger=False) -> tk.Label:
        if danger:
            bg, fg = WARN, BG
        elif primary:
            bg, fg = ACCENT, BG
        else:
            bg, fg = "#333333", FG
        lbl = tk.Label(
            parent,
            text=text,
            bg=bg,
            fg=fg,
            font=("Segoe UI", 9),
            padx=14,
            pady=8,
            cursor="hand2",
        )
        lbl.bind("<Button-1>", lambda _e: cmd())
        return lbl

    def _place_on_primary(self) -> None:
        self.update_idletasks()
        w = self.winfo_width() or 420
        h = self.winfo_height() or 320
        sw = ctypes.windll.user32.GetSystemMetrics(0)
        sh = ctypes.windll.user32.GetSystemMetrics(1)
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 3)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _start_tray(self) -> None:
        try:
            self._tray = TrayIcon(self, on_show=self.show_window, on_toggle=self._toggle, on_quit=self.quit_app)
            self._tray.start()
            vis = icons_visible()
            if vis is not None:
                self._tray.set_hidden(not vis)
            # One notify only when started with Windows / --tray (PC on)
            if self._start_hidden:
                self.after(
                    800,
                    lambda: self._tray
                    and self._tray.notify(
                        f"DeskHide запущен · {format_hotkey()}",
                        "DeskHide",
                    ),
                )
        except Exception as e:
            self._status.configure(text=f"трей: {e}", fg=WARN)

    def show_window(self) -> None:
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self.after(80, lambda: self.attributes("-topmost", False))
        self.focus_force()
        self._refresh_state()

    def hide_to_tray(self) -> None:
        self.withdraw()

    def quit_app(self) -> None:
        if self._exiting:
            return
        self._exiting = True
        self._hotkeys.stop()
        if self._tray is not None:
            try:
                self._tray.stop()
            except Exception:
                pass
        self.destroy()

    def _refresh_state(self) -> None:
        vis = icons_visible()
        if vis is None:
            self._state_lbl.configure(text="не найдено", fg=WARN)
            self._hint.configure(text="Не удалось найти список иконок рабочего стола.")
            self._toggle_btn.configure(text="Повторить")
            return
        if vis:
            self._state_lbl.configure(text="Иконки видны", fg=OK)
            self._hint.configure(text="Нажми кнопку или Ctrl+Alt+D — спрятать.")
            self._toggle_btn.configure(text="Спрятать")
        else:
            self._state_lbl.configure(text="Иконки скрыты", fg=ACCENT)
            self._hint.configure(text="Нажми кнопку или Ctrl+Alt+D — показать.")
            self._toggle_btn.configure(text="Показать")
        if self._tray is not None:
            self._tray.set_hidden(not vis)

    def _toggle(self) -> None:
        new_state = toggle_icons()
        if new_state is None:
            self._status.configure(text="не удалось переключить", fg=WARN)
            self._refresh_state()
            return
        self._refresh_state()
        msg = "иконки показаны" if new_state else "иконки скрыты"
        self._status.configure(text=msg, fg=OK)

    def _set(self, visible: bool) -> None:
        if not set_icons_visible(visible):
            self._status.configure(text="не удалось изменить", fg=WARN)
            self._refresh_state()
            return
        self._refresh_state()
        self._status.configure(
            text="иконки показаны" if visible else "иконки скрыты",
            fg=OK,
        )

    def _on_hotkey_toggle(self) -> None:
        self._toggle()


def run(start_hidden: bool = False) -> None:
    app = DeskHideApp(start_hidden=start_hidden)
    app.mainloop()
