import ctypes
import sys

import sdl2
import skia

from .chrome import Chrome
from .layout import HEIGHT, WIDTH
from .paint import Rect
from .tab import Tab
from .url import URL


class Browser:
    def __init__(self):
        self.tabs = []
        self.active_tab = None
        self.focus = None

        self.sdl_window = sdl2.SDL_CreateWindow(
            b"Browser",
            sdl2.SDL_WINDOWPOS_CENTERED, sdl2.SDL_WINDOWPOS_CENTERED,
            WIDTH, HEIGHT, sdl2.SDL_WINDOW_SHOWN,
        )
        self.root_surface = skia.Surface.MakeRaster(
            skia.ImageInfo.Make(
                WIDTH, HEIGHT,
                ct=skia.kRGBA_8888_ColorType,
                at=skia.kUnpremul_AlphaType,
            )
        )

        if sdl2.SDL_BYTEORDER == sdl2.SDL_BIG_ENDIAN:
            self.RED_MASK = 0xff000000
            self.GREEN_MASK = 0x00ff0000
            self.BLUE_MASK = 0x0000ff00
            self.ALPHA_MASK = 0x000000ff
        else:
            self.RED_MASK = 0x000000ff
            self.GREEN_MASK = 0x0000ff00
            self.BLUE_MASK = 0x00ff0000
            self.ALPHA_MASK = 0xff000000

        self.chrome = Chrome(self)

    def new_tab(self, url):
        new_tab = Tab(HEIGHT - self.chrome.bottom)
        new_tab.load(url)
        self.active_tab = new_tab
        self.tabs.append(new_tab)
        self.draw()

    def handle_down(self):
        if self.focus == "content" and self.active_tab:
            self.active_tab.scrolldown()
        self.draw()

    def handle_click(self, e):
        if e.y < self.chrome.bottom:
            self.focus = None
            self.chrome.click(e.x, e.y)
        else:
            self.focus = "content"
            self.chrome.blur()
            if self.active_tab:
                self.active_tab.click(e.x, e.y - self.chrome.bottom)
        self.draw()

    def handle_key(self, char):
        if len(char) == 0:
            return
        if not (0x20 <= ord(char) < 0x7f):
            return
        if self.chrome.keypress(char):
            self.draw()
        elif self.focus == "content" and self.active_tab:
            self.active_tab.keypress(char)
            self.draw()

    def handle_enter(self):
        self.chrome.enter()
        if self.chrome.focus is None and self.active_tab:
            pass  # chrome.enter() already triggered active_tab.load(...)
        self.draw()

    def handle_quit(self):
        sdl2.SDL_DestroyWindow(self.sdl_window)

    def draw(self):
        canvas = self.root_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)

        if self.active_tab:
            canvas.save()
            canvas.translate(0, self.chrome.bottom)
            self.active_tab.draw(canvas)
            canvas.restore()

        for cmd in self.chrome.paint():
            cmd.execute(0, canvas)

        skia_image = self.root_surface.makeImageSnapshot()
        skia_bytes = skia_image.tobytes()
        depth = 32
        pitch = 4 * WIDTH
        sdl_surface = sdl2.SDL_CreateRGBSurfaceFrom(
            skia_bytes, WIDTH, HEIGHT, depth, pitch,
            self.RED_MASK, self.GREEN_MASK, self.BLUE_MASK, self.ALPHA_MASK,
        )
        rect = sdl2.SDL_Rect(0, 0, WIDTH, HEIGHT)
        window_surface = sdl2.SDL_GetWindowSurface(self.sdl_window)
        sdl2.SDL_BlitSurface(sdl_surface, rect, window_surface, rect)
        sdl2.SDL_UpdateWindowSurface(self.sdl_window)


def mainloop(browser):
    event = sdl2.SDL_Event()
    while True:
        while sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            if event.type == sdl2.SDL_QUIT:
                browser.handle_quit()
                sdl2.SDL_Quit()
                sys.exit()
            elif event.type == sdl2.SDL_MOUSEBUTTONUP:
                browser.handle_click(event.button)
            elif event.type == sdl2.SDL_KEYDOWN:
                if event.key.keysym.sym == sdl2.SDLK_RETURN:
                    browser.handle_enter()
                elif event.key.keysym.sym == sdl2.SDLK_DOWN:
                    browser.handle_down()
            elif event.type == sdl2.SDL_TEXTINPUT:
                browser.handle_key(event.text.text.decode("utf8"))


def main():
    if len(sys.argv) < 2:
        print("usage: python main.py <url>")
        sys.exit(1)

    sdl2.SDL_Init(sdl2.SDL_INIT_EVENTS | sdl2.SDL_INIT_VIDEO)
    browser = Browser()
    browser.new_tab(URL(sys.argv[1]))
    mainloop(browser)


if __name__ == "__main__":
    main()
