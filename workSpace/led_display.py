from neopixel import NeoPixel

from board_driver import LED2, LED3, LED4
from log import Log

log = Log(tag='SEG')
_SegTable = {
    '0': 0xFC,
    '1': 0x60,
    '2': 0xDA,
    '3': 0xF2,
    '4': 0x66,
    '5': 0xB6,
    '6': 0xBE,
    '7': 0xE0,
    '8': 0xFE,
    '9': 0xF6,
    ' ': 0x00,
}


class Seg:
    def __init__(self, np, a, b, c):
        self.np = np
        self.a = a
        self.b = b
        self.c = c

    def color(self, ca, cb, cc):
        self.np[self.a] = ca
        self.np[self.b] = cb
        self.np[self.c] = cc


class ColorRule:
    def get_color(self, index):
        pass


class FixedColorRule(ColorRule):
    def __init__(self):
        self.ca = (1, 1, 1)
        self.cb = (1, 1, 1)
        self.cc = (1, 1, 1)

    def set_color(self, ca, cb, cc):
        self.ca = ca
        self.cb = cb
        self.cc = cc

    def get_color(self, index):
        return self.ca, self.cb, self.cc


class YGradientColorRule(ColorRule):
    def __init__(self):
        self.gradient = [
            (0x1, 0x1, 0x1),
            (0x1, 0x1, 0x1),
            (0x1, 0x1, 0x1),
            (0x1, 0x1, 0x1),
            (0x1, 0x1, 0x1),
            (0x1, 0x1, 0x1),
            (0x1, 0x1, 0x1),
            (0x1, 0x1, 0x1),
            (0x1, 0x1, 0x1),
        ]

    def get_color(self, index):
        if index == 0:
            c1 = 0
            c2 = 0
            c3 = 0
        elif index == 1:
            c1 = 1
            c2 = 2
            c3 = 3
        elif index == 2:
            c1 = 5
            c2 = 6
            c3 = 7
        elif index == 3:
            c1 = 8
            c2 = 8
            c3 = 8
        elif index == 4:
            c1 = 7
            c2 = 6
            c3 = 5
        elif index == 5:
            c1 = 3
            c2 = 2
            c3 = 1
        elif index == 6:
            c1 = 4
            c2 = 4
            c3 = 4
        else:
            c1 = c2 = c3 = 0
        return self.gradient[c1], self.gradient[c2], self.gradient[c3]

    def roll(self):
        self.gradient.append(self.gradient.pop(0))


DEFAULT_COLOR_RULE = FixedColorRule()
COLOR_BLACK = (0, 0, 0)


class SegScreen:
    def __init__(self, np, offset):
        self.segs = [
            Seg(np, offset, offset + 1, offset + 2),
            Seg(np, offset + 3, offset + 4, offset + 5),
            Seg(np, offset + 6, offset + 7, offset + 8),
            Seg(np, offset + 9, offset + 10, offset + 11),
            Seg(np, offset + 12, offset + 13, offset + 14),
            Seg(np, offset + 15, offset + 16, offset + 17),
            Seg(np, offset + 18, offset + 19, offset + 20),
        ]
        self.color_rule = DEFAULT_COLOR_RULE

    def set_color_rule(self, rule):
        self.color_rule = rule

    def show(self, s):
        if s not in _SegTable:
            log.error('CantShow::' + s)
            return
        seg_code = _SegTable[s]
        for i in range(len(self.segs)):
            if seg_code & (0x80 >> i):
                color = self.color_rule.get_color(i)
            else:
                color = (COLOR_BLACK, COLOR_BLACK, COLOR_BLACK)
            seg = self.segs[i]
            seg.color(color[0], color[1], color[2])


class ColorSegScreen:
    def __init__(self, np, offset):
        self.segs = [
            Seg(np, offset, offset + 1, offset + 2),
            Seg(np, offset + 3, offset + 4, offset + 5)
        ]
        self.color_rule = DEFAULT_COLOR_RULE
        self.np = np

    def set_color_rule(self, rule):
        self.color_rule = rule

    def show(self):
        color = self.color_rule.get_color(0)
        self.segs[0].color(color[0], color[1], color[2])
        color = self.color_rule.get_color(1)
        self.segs[1].color(color[0], color[1], color[2])
        self.np.write()

    def hide(self):
        self.segs[0].color(COLOR_BLACK, COLOR_BLACK, COLOR_BLACK)
        self.segs[1].color(COLOR_BLACK, COLOR_BLACK, COLOR_BLACK)
        self.np.write()


class ScreenGroup:
    def __init__(self, np, screens):
        self.screens = screens
        self.np = np

    def show(self, s):
        if not s:
            s = ''
        width = len(self.screens)
        s = ('0' * width) + s
        sl = len(s)
        s = s[sl - width:sl]
        i = 0
        for c in s:
            self.screens[i].show(c)
            i += 1
        self.np.write()
        self.np.write()

    def set_color_rule(self, rule):
        for sc in self.screens:
            sc.set_color_rule(rule)


_np1 = NeoPixel(LED4, 42)
group1 = ScreenGroup(_np1, (SegScreen(_np1, 0), SegScreen(_np1, 21)))

_np2 = NeoPixel(LED2, 42)
group2 = ScreenGroup(_np2, (SegScreen(_np2, 0), SegScreen(_np2, 21)))

_np3 = NeoPixel(LED3, 6)
seg_screen = ColorSegScreen(_np3, 0)
