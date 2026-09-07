"""System tray icon."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from .ui import DeskHideApp


def make_tray_image(hidden: bool = False):
    from PIL import Image, ImageDraw

    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    color = (148, 163, 184, 255) if hidden else (96, 165, 250, 255)
    draw.rounded_rectangle((6, 6, size - 6, size - 6), radius=12, fill=color)
    # mini desktop icons
    for x, y in ((18, 18), (34, 18), (18, 34), (34, 34)):
        if hidden:
            draw.rectangle((x, y, x + 10, y + 10), outline=(17, 17, 17, 180), width=1)
        else:
            draw.rectangle((x, y, x + 10, y + 10), fill=(17, 17, 17, 255))
    return img


class TrayIcon:
    def __init__(
        self,
        app: DeskHideApp,
        on_show: Callable[[], None],
        on_toggle: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        self._app = app
        self._on_show = on_show
        self._on_toggle = on_toggle
        self._on_quit = on_quit
        self._icon = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._hidden = False

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True, name="DeskHideTray")
        self._thread.start()
        self._ready.wait(timeout=5)

    def _run(self) -> None:
        import pystray
        from pystray import MenuItem as item

        menu = pystray.Menu(
            item("Открыть", lambda _i, _it: self._app.after(0, self._on_show)),
            item("Спрятать / показать", lambda _i, _it: self._app.after(0, self._on_toggle)),
            pystray.Menu.SEPARATOR,
            item("Выход", lambda _i, _it: self._app.after(0, self._on_quit)),
        )
        self._icon = pystray.Icon(
            "DeskHide",
            make_tray_image(False),
            "DeskHide — иконки рабочего стола",
            menu,
        )
        self._ready.set()
        self._icon.run()

    def set_hidden(self, hidden: bool) -> None:
        self._hidden = hidden
        if self._icon is not None:
            try:
                self._icon.icon = make_tray_image(hidden)
                self._icon.title = "Иконки скрыты" if hidden else "Иконки видны"
            except Exception:
                pass

    def notify(self, text: str, title: str = "DeskHide") -> None:
        if self._icon is not None:
            try:
                self._icon.notify(text, title)
            except Exception:
                pass

    def stop(self) -> None:
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                pass
            self._icon = None
