import threading
import webbrowser
import requests
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem


class TrayIcon:
    def __init__(self, port: int = 8080, on_exit=None):
        self.port = port
        self.on_exit = on_exit
        self.icon = None
        self._thread = None

    def _create_image(self) -> Image.Image:
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse([8, 8, 56, 56], fill="#1DB954")
        draw.ellipse([24, 20, 44, 40], fill="white")
        draw.rectangle([30, 40, 38, 52], fill="white")
        return image

    def _open_review(self, icon, item):
        webbrowser.open(f"http://localhost:{self.port}")

    def _refresh_review(self, icon, item):
        try:
            requests.post(f"http://localhost:{self.port}/api/review/refresh", timeout=5)
        except Exception:
            pass

    def _open_settings(self, icon, item):
        webbrowser.open(f"http://localhost:{self.port}#settings")

    def _quit(self, icon, item):
        icon.stop()
        if self.on_exit:
            self.on_exit()

    def _run(self):
        menu = pystray.Menu(
            MenuItem("查看乐评", self._open_review, default=True),
            MenuItem("刷新乐评", self._refresh_review),
            MenuItem("设置", self._open_settings),
            pystray.Menu.SEPARATOR,
            MenuItem("退出", self._quit),
        )

        self.icon = pystray.Icon(
            "Mylody",
            self._create_image(),
            "Mylody - 音乐意评",
            menu,
        )
        self.icon.run()

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        if self.icon:
            self.icon.stop()
