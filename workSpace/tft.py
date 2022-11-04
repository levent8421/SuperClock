import time

import framebuf
from machine import SPI

from ST7735 import TFT
from beeos import Process, OSKernel
from board_driver import D_MOSI, D_MISO, D_SCLK, D_DC, D_RES, D_CS, D_BKL
from font import ASCIIFont
from log import Log

log = Log(tag='tft')


class TFTBuf:
    def __init__(self, tft):
        self.buf = bytearray(80 * 160 * 2)
        self.fbuf = framebuf.FrameBuffer(self.buf, 80, 160, framebuf.RGB565)
        self.tft = tft
        self.font = ASCIIFont('ascii.font')

    def show(self):
        start = time.ticks_ms()
        self.tft.image(26, 1, 105, 160, self.buf)
        end = time.ticks_ms()
        log.debug('SHOW(FLUSH):%s ms' % (end - start))

    def text8x8_h(self, x, y, text, c=0):
        start = time.ticks_ms()
        self.fbuf.text(text, x, y, c)
        end = time.ticks_ms()
        log.debug('TEXT_8-8[%s]:%s ms' % (text, (end - start)))

    def text8x16_v(self, x, y, text, fc, bc=None):
        start = time.ticks_ms()
        yoffset = y
        for cc in text:
            font_m = self.font.find_font(cc)
            rows = len(font_m)
            for ri in range(rows):
                r = font_m[rows - ri - 1]
                for i in range(8):
                    if r & (0x80 >> i):
                        self.fbuf.pixel(x + ri, yoffset + i, fc)
                    elif bc:
                        self.fbuf.pixel(x + ri, yoffset + i, bc)
            yoffset += 8
        end = time.ticks_ms()
        log.debug('TEXT_8-16[%s]:%s ms' % (text, (end - start)))

    def clear(self, c):
        self.fbuf.fill(c)

    def image(self, file, x, y, w):
        start = time.ticks_ms()
        with open(file, 'rb') as f:
            yoff = 0
            while True:
                row = f.read(w * 2)
                for i in range(0, len(row), 2):
                    color = row[i] | (row[i + 1] << 8)
                    self.fbuf.pixel(x + int(i / 2), y + yoff, color)
                yoff += 1
                if len(row) < (w * 2):
                    break
        end = time.ticks_ms()
        log.debug('FILL_IMG:%s ms' % (end - start))

    def fill_img(self, file, w):
        start = time.ticks_ms()
        with open(file, 'rb') as f:
            y = 0
            while True:
                row = f.read(w * 2)
                offset = y * w * 2
                row_len = len(row)
                for x in range(row_len):
                    self.buf[offset + x] = row[x]
                y += 1
                if row_len < (w * 2):
                    break
        end = time.ticks_ms()
        log.debug('FILL_IMG(FULL):%s ms' % (end - start))


class TFTTask(Process):
    NAME = 'tft_task'
    BC = 'tft_bc'
    FLUSH = 'tft_flush'
    TITLE = 'tft_title'
    TEXT_1 = 'tft_text1'
    TEXT_2 = 'tft_text2'
    TEXT_3 = 'tft_text3'
    BC_CLOCK = 'bg_clock.data'
    BC_TH = 'bg_th.data'
    ENABLE = 'tft_enable'

    def __init__(self):
        spi = SPI(2, baudrate=20000000, polarity=0, phase=0, sck=D_SCLK, mosi=D_MOSI, miso=D_MISO)
        self.bkl_pin = D_BKL
        self.tft = TFT(spi, D_DC, D_RES, D_CS, size=(106, 160))
        self.buf = TFTBuf(self.tft)
        self.bc = self.BC_CLOCK
        self.t1 = ''
        self.t2 = ''
        self.t3 = ''
        self.t = 'Levent'
        self.flush = False
        self.bkl = True
        self.last_act = 0

    def setup(self):
        self.tft.initr()
        self.tft.invertcolor(True)

    def loop(self, ctx):
        now = ctx.get_var(OSKernel.TICKS_MS, 0)
        enable = ctx.get_var(TFTTask.ENABLE, False)
        if enable:
            ctx.set_var(TFTTask.ENABLE, False)
            self.last_act = now
        if now - self.last_act > 20 * 1000:
            self.bkl_pin.off()
            self.bkl = False
        else:
            self.bkl_pin.on()
            self.bkl = True
        self.read_value(ctx)
        if not self.flush or not self.bkl:
            return
        self.reset_flush(ctx)
        start = time.ticks_ms()
        self.buf.fill_img(self.bc, 80)
        self.buf.text8x8_h(0, 150, self.t)
        self.buf.text8x16_v(60, 6, self.t1, 0xFF)
        self.buf.text8x16_v(40, 6, self.t2, 0xFF)
        self.buf.text8x16_v(20, 6, self.t3, 0xFF)
        self.buf.show()
        end = time.ticks_ms()
        log.debug('TFT_FLUSH:%s ms' % (end - start))

    def read_value(self, ctx):
        s = TFTTask
        self.bc = ctx.get_var(s.BC, s.BC_CLOCK)
        self.t = ctx.get_var(s.TITLE, '')
        self.t1 = ctx.get_var(s.TEXT_1, '')
        self.t2 = ctx.get_var(s.TEXT_2, '')
        self.t3 = ctx.get_var(s.TEXT_3, '')
        self.flush = ctx.get_var(s.FLUSH, False)

    @staticmethod
    def reset_flush(ctx):
        ctx.set_var(TFTTask.FLUSH, False)
