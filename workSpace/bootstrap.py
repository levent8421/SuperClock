import gc

import network
import ntptime
from dht import DHT11

from beeos import TimerOSKernel, SuspendOSKernel, Process, OSKernel, Context, state_pin
from board_driver import TH_SENSOR, Buttons
from led_display import DEFAULT_COLOR_RULE, FixedColorRule
from log import Log
from rtc import RTCHelper

log = Log(tag="strap")
MODE = 'mode'
MODE_TIME = 0
MODE_TH = 1
MODE_LIST = (MODE_TIME, MODE_TH)


class LEDCTLTask(Process):
    NAME = 'LED_task'
    STR_1 = 'display_str_1'
    STR_2 = 'display_str_2'
    SEG_VISIBLE = 'display_seg_visible'
    FLUSH = 'display_flush'
    COLOR_RULE = 'display_color_rule'
    FORCE_FLUSH = 'display_force_flush'

    def __init__(self):
        self.str1 = ''
        self.str2 = ''
        self.seg_visible = False
        self.color_rule = DEFAULT_COLOR_RULE
        self.target1 = None
        self.target2 = None
        self.target_seg = None

    def setup(self):
        from led_display import group1, group2, seg_screen
        self.target1 = group1
        self.target2 = group2
        self.target_seg = seg_screen

    def loop(self, ctx):
        _s = LEDCTLTask
        flush = ctx.get_var(_s.FLUSH, False)
        if not flush:
            return
        ctx.set_var(_s.FLUSH, False)
        str1 = ctx.get_var(_s.STR_1)
        str2 = ctx.get_var(_s.STR_2)
        seg_visible = ctx.get_var(_s.SEG_VISIBLE)
        self.color_rule = ctx.get_var(_s.COLOR_RULE, DEFAULT_COLOR_RULE)
        force = ctx.get_var(_s.FORCE_FLUSH, False)

        self.target1.set_color_rule(self.color_rule)
        self.target2.set_color_rule(self.color_rule)
        self.target_seg.set_color_rule(self.color_rule)

        if str1 != self.str1 or force:
            self.target1.show(str1)
            self.str1 = str1
        if str2 != self.str2 or force:
            self.target2.show(str2)
            self.str2 = str2
        if seg_visible != self.seg_visible or force:
            self.seg_visible = seg_visible
            if seg_visible:
                self.target_seg.show()
            else:
                self.target_seg.hide()


class THSensorTask(Process):
    NAME = "th_task"

    def __init__(self):
        self.dht = DHT11(TH_SENSOR)
        self.last_mes = 0

    def loop(self, ctx):
        mode = ctx.get_var(MODE)
        if mode != MODE_TH:
            return
        now = ctx.get_var(OSKernel.TICKS_MS, 0)
        if now - self.last_mes < 10000:
            return
        self.last_mes = now
        self.dht.measure()
        temp = str(self.dht.temperature())
        hum = str(self.dht.humidity())
        ctx.set_var(LEDCTLTask.STR_1, temp)
        ctx.set_var(LEDCTLTask.STR_2, hum)
        ctx.set_var(LEDCTLTask.SEG_VISIBLE, False)
        ctx.set_var(LEDCTLTask.FLUSH, True)
        log.debug('TH:[%s/%s]' % (temp, hum))


class TimeTask(Process):
    def loop(self, ctx):
        mode = ctx.get_var(MODE)
        ticks = ctx.get_var(TimerOSKernel.TICKS, 0)
        if mode != MODE_TIME:
            return
        tt = RTCHelper.current_time_tuple6()
        h = tt[3]
        m = tt[4]
        ctx.set_var(LEDCTLTask.STR_1, str(m))
        ctx.set_var(LEDCTLTask.STR_2, str(h))
        ctx.set_var(LEDCTLTask.FLUSH, True)
        seg_visible = ctx.get_var(LEDCTLTask.SEG_VISIBLE, False)
        if ticks % 5 == 0:
            ctx.set_var(LEDCTLTask.SEG_VISIBLE, not seg_visible)


BEEP_SEQ_A = ((2500, 1), (2900, 1), (3000, 1))
BEEP_SEQ_B = ((3000, 1), (2900, 1), (2500, 1))


class BeepTask(Process):
    NAME = 'beep_task'
    SEQ = 'beep_seq'
    FLUSH = 'beep_flush'

    def __init__(self):
        self.seq = ()
        self.seq_index = 0
        from board_driver import Beep
        self.beep = Beep.get()
        self.next = 0

    def loop(self, ctx):
        ticks = ctx.get_var(TimerOSKernel.TICKS, 0)
        flush = ctx.get_var(BeepTask.FLUSH, False)
        if flush:
            self.seq = ctx.get_var(BeepTask.SEQ, BEEP_SEQ_A)
            self.seq_index = 0
            self.next = ticks
            ctx.set_var(BeepTask.FLUSH, False)
        if self.seq_index >= len(self.seq):
            self.beep.disable()
            return
        self.beep.enable()
        if ticks >= self.next:
            item = self.seq[self.seq_index]
            self.next = ticks + item[1]
            self.beep.freq(item[0])
            self.seq_index += 1


class TFTBKLTask(Process):
    NAME = "tft_bkl_task"
    FLUSH = 'tft_bkl_flush'
    BKL = 'tft_bkl'

    def __init__(self):
        from board_driver import D_BKL
        self.bkl = D_BKL
        self.timeout = 0

    def loop(self, ctx):
        now = ctx.get_var(OSKernel.TICKS_MS, 0)
        if now >= self.timeout:
            ctx.set_var(TFTBKLTask.BKL, False)
            self.bkl.off()
        flush = ctx.get_var(TFTBKLTask.FLUSH, False)
        if not flush:
            return
        self.bkl.on()
        ctx.set_var(TFTBKLTask.BKL, True)
        ctx.set_var(TFTBKLTask.FLUSH, False)
        self.timeout = now + 10000


class TFTTask(Process):
    NAME = 'tft_task'
    BKL = 'tft_bkl'
    TEXT_1 = 'tft_text1'
    TEXT_2 = 'tft_text2'
    TEXT_3 = 'tft_text3'
    TEXT_4 = 'tft_text4'
    MODE = 'tft_mode'
    FLUSH = 'tft_flush'
    MODE_IMG_L = 1
    MODE_IMG_R = 2

    def __init__(self):
        from ST7735 import TFT
        from machine import SPI
        from board_driver import D_MOSI, D_MISO, D_SCLK, D_DC, D_RES, D_CS
        spi = SPI(2, baudrate=20000000, polarity=0, phase=0, sck=D_SCLK, mosi=D_MOSI, miso=D_MISO)
        self.tft = TFT(spi, D_DC, D_RES, D_CS, size=(106, 160))
        self.tft.initr()
        self.tft.fill(TFT.BLACK)
        self.tft.invertcolor(True)
        from font import ASCIIFont
        self.font = ASCIIFont(file='ascii.font')
        self.text1 = ''
        self.text2 = ''
        self.text3 = ''
        self.text4 = ''
        self.mode = ''

    def _x(self, mode):
        if mode == TFTTask.MODE_IMG_L:
            return 80, 0
        else:
            return 0, 80

    def loop(self, ctx):
        bkl = ctx.get_var(TFTBKLTask.BKL, False)
        if not bkl:
            return
        s = TFTTask
        flush = ctx.get_var(s.FLUSH, False)
        if not flush:
            return
        ctx.set_var(s.FLUSH, False)
        mode = ctx.get_var(s.MODE, s.MODE_IMG_L)
        text_x, img_x = self._x(mode)
        self.tft.fillrect((26, 0), (128, 160), 0xFFFF)
        with open('icon_keqin.data') as f:
            img = f.read()
        self.tft.image(26, img_x, 105, img_x + 79, img)
        self.text1 = ctx.get_var(s.TEXT_1, '')
        self.text2 = ctx.get_var(s.TEXT_2, '')
        self.text(text_x, 90, self.text1)
        self.text(text_x, 74, self.text2)

    def text(self, x, y, s):
        if not s:
            return
        img = self.font.str_img(s, (255, 255), (0x33, 0x9F))
        self.tft.image(y, x, y + 15, x + 8 * len(s), img.getvalue())


INACTIVE_RULE = DEFAULT_COLOR_RULE
ACTIVE_RULE = FixedColorRule()
ACTIVE_RULE.set_color((1, 2, 3), (1, 2, 3), (1, 2, 3))


class WakeupTask(Process):
    def __init__(self):
        self.pin = None
        self.last_value = 0

    def setup(self):
        from board_driver import WAKEUP
        self.pin = WAKEUP

    def loop(self, ctx):
        value = self.pin.value()
        if value == self.last_value:
            return
        self.last_value = value
        log.debug('Wakeup:[%s]' % value)
        if value:
            rule = ACTIVE_RULE
            ctx.set_var(TFTBKLTask.FLUSH, True)
            ctx.set_var(TFTTask.FLUSH, True)
        else:
            rule = INACTIVE_RULE
        ctx.set_var(LEDCTLTask.COLOR_RULE, rule)
        ctx.set_var(LEDCTLTask.FLUSH, True)
        ctx.set_var(LEDCTLTask.FORCE_FLUSH, True)


class MEMTask(Process):
    def __init__(self):
        self.next = 0

    def loop(self, ctx):
        now = ctx.get_var(OSKernel.TICKS_MS, 0)
        if self.next > now:
            return
        self.next = now + 10000
        free = gc.mem_free()
        alloc = gc.mem_alloc()
        total = free + alloc
        rate = alloc / total * 100
        ctx.set_var(TFTTask.TEXT_2, 'MEM:%.1f%%' % rate)
        ctx.set_var(TFTTask.FLUSH, True)


class NetworkTask(Process):
    NAME = 'network_task'

    def __init__(self, ssid, passwd):
        self.ssid = ssid
        self.passwd = passwd
        self.wifi = network.WLAN(network.STA_IF)
        self.connecting = False
        self.connected = False
        self.time_last_sync = 0

    def setup(self):
        self.wifi.active(True)
        ntptime.host = 'ntp1.aliyun.com'
        ntptime.NTP_DELTA = 3155644800

    def connect(self):
        self.wifi.connect(self.ssid, self.passwd)
        self.connecting = True

    def loop(self, ctx):
        if self.wifi.isconnected():
            state_pin.set_blink_interval(5)
            self.connected = True
            if self.connecting:
                self.connecting = False
                log.info('WIFI Ready!')
        else:
            self.connected = False
            state_pin.set_blink_interval(1)
            if not self.connecting:
                self.connect()
        self.sync_time(ctx)

    def sync_time(self, ctx):
        if not self.connected:
            return
        now = ctx.get_var(OSKernel.TICKS_MS)
        if (now - self.time_last_sync) > (60 * 60 * 1000) or self.time_last_sync <= 0:
            log.info('Sync time!')
            try:
                ntptime.settime()
                self.time_last_sync = now
            except Exception as e:
                log.error('Err SYNC_TIME', e)


class Entry:
    def __init__(self):
        self.ctx = Context()
        self.skernel = SuspendOSKernel(self.ctx)
        self.tkernel = TimerOSKernel(self.ctx, frq=100)

        self.skernel.exec(LEDCTLTask())
        self.skernel.exec(THSensorTask())
        self.skernel.exec(WakeupTask())
        self.skernel.exec(TFTBKLTask())
        self.skernel.exec(TFTTask())

        self.ctx.set_var(TFTTask.FLUSH, True)
        self.ctx.set_var(TFTTask.TEXT_1, 'CLOCK')
        self.tkernel.exec(TimeTask())
        self.tkernel.exec(BeepTask())
        self.tkernel.exec(MEMTask())
        self.network_task = NetworkTask('Socket', 'qwerasdzx')
        self.tkernel.exec(self.network_task)
        self.btns = Buttons.get()

    def start(self):
        self.init_btn()
        self.ctx.set_var(MODE, MODE_TIME)
        self.skernel.setup_os()
        self.tkernel.setup_os()
        self.network_task.connect()
        self.tkernel.run_forever()
        self.skernel.run_forever()

    def init_btn(self):
        self.btns.listen(lambda b, v: self.on_btn(b, v))
        self.beep(BEEP_SEQ_A)

    def beep(self, seq):
        self.ctx.set_var(BeepTask.SEQ, seq)
        self.ctx.set_var(BeepTask.FLUSH, True)

    def on_btn(self, b, v):
        log.debug('BTN:%s/%s' % (b, v))
        if v:
            seq = BEEP_SEQ_A
        else:
            seq = BEEP_SEQ_B
        self.beep(seq)
        if b == Buttons.RIGHT and not v:
            mode = self.ctx.get_var(MODE, MODE_TIME)
            mode += 1
            mode %= len(MODE_LIST)
            self.ctx.set_var(MODE, mode)
            if mode == MODE_TH:
                self.ctx.set_var(TFTTask.MODE, TFTTask.MODE_IMG_R)
                self.ctx.set_var(TFTTask.TEXT_1, "THSensor")
            else:
                self.ctx.set_var(TFTTask.MODE, TFTTask.MODE_IMG_L)
                self.ctx.set_var(TFTTask.TEXT_1, "CLOCK")
            self.ctx.set_var(TFTTask.FLUSH, True)
            log.debug('SET_MODE:%s' % mode)
