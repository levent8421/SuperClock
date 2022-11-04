import time

import machine

TFTRotations = [0x00, 0x60, 0xC0, 0xA0]
TFTBGR = 0x08  # When set color is bgr else rgb.
TFTRGB = 0x00


def clamp(aValue, aMin, aMax):
    return max(aMin, min(aMax, aValue))


def TFTColor(aR, aG, aB):
    return ((aR & 0xF8) << 8) | ((aG & 0xFC) << 3) | (aB >> 3)


ScreenSize = (80, 160)


class TFT(object):
    NOP = 0x0
    SWRESET = 0x01
    RDDID = 0x04
    RDDST = 0x09

    SLPIN = 0x10
    SLPOUT = 0x11
    PTLON = 0x12
    NORON = 0x13

    INVOFF = 0x20
    INVON = 0x21
    DISPOFF = 0x28
    DISPON = 0x29
    CASET = 0x2A
    RASET = 0x2B
    RAMWR = 0x2C
    RAMRD = 0x2E

    VSCRDEF = 0x33
    VSCSAD = 0x37

    COLMOD = 0x3A
    MADCTL = 0x36

    FRMCTR1 = 0xB1
    FRMCTR2 = 0xB2
    FRMCTR3 = 0xB3
    INVCTR = 0xB4
    DISSET5 = 0xB6

    PWCTR1 = 0xC0
    PWCTR2 = 0xC1
    PWCTR3 = 0xC2
    PWCTR4 = 0xC3
    PWCTR5 = 0xC4
    VMCTR1 = 0xC5

    RDID1 = 0xDA
    RDID2 = 0xDB
    RDID3 = 0xDC
    RDID4 = 0xDD

    PWCTR6 = 0xFC

    GMCTRP1 = 0xE0
    GMCTRN1 = 0xE1

    BLACK = 0
    WHITE = TFTColor(0xFF, 0xFF, 0xFF)

    @staticmethod
    def color(aR, aG, aB):
        return TFTColor(aR, aG, aB)

    def __init__(self, spi, aDC, aReset, aCS, size=ScreenSize):
        self._size = size
        self._offset = bytearray([0, 0])
        self.rotate = 0  # Vertical with top toward pins.
        self._rgb = True  # color order of rgb.
        self.tfa = 0  # top fixed area
        self.bfa = 0  # bottom fixed area
        self.dc = machine.Pin(aDC, machine.Pin.OUT, machine.Pin.PULL_DOWN)
        self.reset = machine.Pin(aReset, machine.Pin.OUT, machine.Pin.PULL_DOWN)
        self.cs = machine.Pin(aCS, machine.Pin.OUT, machine.Pin.PULL_DOWN)
        self.cs(1)
        self.spi = spi
        self.colorData = bytearray(2)
        self.windowLocData = bytearray(4)

    def size(self):
        return self._size

    def on(self, aTF=True):
        self._writecommand(TFT.DISPON if aTF else TFT.DISPOFF)

    def invertcolor(self, aBool):
        self._writecommand(TFT.INVON if aBool else TFT.INVOFF)

    def rgb(self, aTF=True):
        self._rgb = aTF
        self._setMADCTL()

    def image(self, x0, y0, x1, y1, data):
        self._setwindowloc((x0, y0), (x1, y1))
        self._writedata(data)

    def _vscrolladdr(self, addr):
        self._writecommand(TFT.VSCSAD)
        data2 = bytearray([addr >> 8, addr & 0xff])
        self._writedata(data2)

    def _setColor(self, aColor):
        self.colorData[0] = aColor >> 8
        self.colorData[1] = aColor
        self.buf = bytes(self.colorData) * 32

    def _draw(self, aPixels):
        self.dc(1)
        self.cs(0)
        for i in range(aPixels // 32):
            self.spi.write(self.buf)
        rest = (int(aPixels) % 32)
        if rest > 0:
            buf2 = bytes(self.colorData) * rest
            self.spi.write(buf2)
        self.cs(1)

    def _setwindowpoint(self, aPos):
        x = self._offset[0] + int(aPos[0])
        y = self._offset[1] + int(aPos[1])
        self._writecommand(TFT.CASET)  # Column address set.
        self.windowLocData[0] = self._offset[0]
        self.windowLocData[1] = x
        self.windowLocData[2] = self._offset[0]
        self.windowLocData[3] = x
        self._writedata(self.windowLocData)

        self._writecommand(TFT.RASET)  # Row address set.
        self.windowLocData[0] = self._offset[1]
        self.windowLocData[1] = y
        self.windowLocData[2] = self._offset[1]
        self.windowLocData[3] = y
        self._writedata(self.windowLocData)
        self._writecommand(TFT.RAMWR)  # Write to RAM.

    def _setwindowloc(self, aPos0, aPos1):
        self._writecommand(TFT.CASET)  # Column address set.
        self.windowLocData[0] = self._offset[0]
        self.windowLocData[1] = self._offset[0] + int(aPos0[0])
        self.windowLocData[2] = self._offset[0]
        self.windowLocData[3] = self._offset[0] + int(aPos1[0])
        self._writedata(self.windowLocData)

        self._writecommand(TFT.RASET)  # Row address set.
        self.windowLocData[0] = self._offset[1]
        self.windowLocData[1] = self._offset[1] + int(aPos0[1])
        self.windowLocData[2] = self._offset[1]
        self.windowLocData[3] = self._offset[1] + int(aPos1[1])
        self._writedata(self.windowLocData)

        self._writecommand(TFT.RAMWR)  # Write to RAM.

    def _writecommand(self, aCommand):
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([aCommand]))
        self.cs(1)

    def _writedata(self, aData):
        self.dc(1)
        self.cs(0)
        self.spi.write(aData)
        self.cs(1)

    def _pushcolor(self, aColor):
        self.colorData[0] = aColor >> 8
        self.colorData[1] = aColor
        self._writedata(self.colorData)

    def _setMADCTL(self):
        self._writecommand(TFT.MADCTL)
        rgb = TFTRGB if self._rgb else TFTBGR
        self._writedata(bytearray([TFTRotations[self.rotate] | rgb]))

    def _reset(self):
        self.dc(0)
        self.reset(1)
        time.sleep_us(500)
        self.reset(0)
        time.sleep_us(500)
        self.reset(1)
        time.sleep_us(500)

    def initr(self):
        self._reset()

        self._writecommand(TFT.SWRESET)  # Software reset.
        time.sleep_us(150)
        self._writecommand(TFT.SLPOUT)  # out of sleep mode.
        time.sleep_us(500)

        data3 = bytearray([0x01, 0x2C, 0x2D])  # fastest refresh, 6 lines front, 3 lines back.
        self._writecommand(TFT.FRMCTR1)  # Frame rate control.
        self._writedata(data3)

        self._writecommand(TFT.FRMCTR2)  # Frame rate control.
        self._writedata(data3)

        data6 = bytearray([0x01, 0x2c, 0x2d, 0x01, 0x2c, 0x2d])
        self._writecommand(TFT.FRMCTR3)  # Frame rate control.
        self._writedata(data6)
        time.sleep_us(10)

        data1 = bytearray(1)
        self._writecommand(TFT.INVCTR)  # Display inversion control
        data1[0] = 0x07  # Line inversion.
        self._writedata(data1)

        self._writecommand(TFT.PWCTR1)  # Power control
        data3[0] = 0xA2
        data3[1] = 0x02
        data3[2] = 0x84
        self._writedata(data3)

        self._writecommand(TFT.PWCTR2)  # Power control
        data1[0] = 0xC5  # VGH = 14.7V, VGL = -7.35V
        self._writedata(data1)

        data2 = bytearray(2)
        self._writecommand(TFT.PWCTR3)  # Power control
        data2[0] = 0x0A  # Opamp current small
        data2[1] = 0x00  # Boost frequency
        self._writedata(data2)

        self._writecommand(TFT.PWCTR4)  # Power control
        data2[0] = 0x8A  # Opamp current small
        data2[1] = 0x2A  # Boost frequency
        self._writedata(data2)

        self._writecommand(TFT.PWCTR5)  # Power control
        data2[0] = 0x8A  # Opamp current small
        data2[1] = 0xEE  # Boost frequency
        self._writedata(data2)

        self._writecommand(TFT.VMCTR1)  # Power control
        data1[0] = 0x0E
        self._writedata(data1)

        self._writecommand(TFT.INVOFF)

        self._writecommand(TFT.MADCTL)  # Power control
        data1[0] = 0xC8
        self._writedata(data1)

        self._writecommand(TFT.COLMOD)
        data1[0] = 0x05
        self._writedata(data1)

        self._writecommand(TFT.CASET)  # Column address set.
        self.windowLocData[0] = 0x00
        self.windowLocData[1] = 0x00
        self.windowLocData[2] = 0x00
        self.windowLocData[3] = self._size[0] - 1
        self._writedata(self.windowLocData)

        self._writecommand(TFT.RASET)  # Row address set.
        self.windowLocData[3] = self._size[1] - 1
        self._writedata(self.windowLocData)

        dataGMCTRP = bytearray([0x0f, 0x1a, 0x0f, 0x18, 0x2f, 0x28, 0x20, 0x22, 0x1f,
                                0x1b, 0x23, 0x37, 0x00, 0x07, 0x02, 0x10])
        self._writecommand(TFT.GMCTRP1)
        self._writedata(dataGMCTRP)

        dataGMCTRN = bytearray([0x0f, 0x1b, 0x0f, 0x17, 0x33, 0x2c, 0x29, 0x2e, 0x30,
                                0x30, 0x39, 0x3f, 0x00, 0x07, 0x03, 0x10])
        self._writecommand(TFT.GMCTRN1)
        self._writedata(dataGMCTRN)
        time.sleep_us(10)

        self._writecommand(TFT.DISPON)
        time.sleep_us(100)

        self._writecommand(TFT.NORON)  # Normal display on.
        time.sleep_us(10)

        self.cs(1)
