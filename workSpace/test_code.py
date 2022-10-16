from machine import SPI

from ST7735 import TFT
from board_driver import D_MOSI, D_MISO, D_SCLK, D_DC, D_RES, D_CS

spi = SPI(2, baudrate=20000000, polarity=0, phase=0, sck=D_SCLK, mosi=D_MOSI, miso=D_MISO)
tft = TFT(spi, D_DC, D_RES, D_CS, size=(126, 160))
tft.initr()
tft.invertcolor(True)


from font import ASCIIFont

font = ASCIIFont(file='ascii.font')
img = font.str_img('ABCD', (0, 0), (0xF8, 0))
img = img.getvalue()
tft.image(30, 0, 45, 32, img)


x = 26

w = 126