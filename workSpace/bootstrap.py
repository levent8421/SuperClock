from dht import DHT11

from beeos import TimerOSKernel, SuspendOSKernel, Process, OSKernel, Context
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

    def setup(self):
        pass

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
    def __init__(self):
        pass

    def loop(self, ctx):
        mode = ctx.get_var(MODE)
        if mode != MODE_TIME:
            return
        tt = RTCHelper.current_time_tuple6()
        h = tt[3]
        m = tt[4]
        ctx.set_var(LEDCTLTask.STR_1, str(m))
        ctx.set_var(LEDCTLTask.STR_2, str(h))
        ctx.set_var(LEDCTLTask.FLUSH, True)
        seg_visible = ctx.get_var(LEDCTLTask.SEG_VISIBLE, False)
        ctx.set_var(LEDCTLTask.SEG_VISIBLE, not seg_visible)


BEEP_SEQ_A = ((2500, 100), (2900, 100), (3000, 100))
BEEP_SEQ_B = ((3000, 100), (2900, 100), (2500, 100))


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
        now = ctx.get_var(OSKernel.TICKS_MS, 0)
        flush = ctx.get_var(BeepTask.FLUSH, False)
        if flush:
            self.seq = ctx.get_var(BeepTask.SEQ, BEEP_SEQ_A)
            self.seq_index = 0
            self.next = now
            ctx.set_var(BeepTask.FLUSH, False)
        if self.seq_index >= len(self.seq):
            self.beep.disable()
            return
        self.beep.enable()
        if now >= self.next:
            item = self.seq[self.seq_index]
            self.next = now + item[1]
            self.beep.freq(item[0])
            self.seq_index += 1


INACTIVE_RULE = DEFAULT_COLOR_RULE
ACTIVE_RULE = FixedColorRule()
ACTIVE_RULE.set_color((5, 0, 0), (0, 5, 0), (0, 0, 5))


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
        else:
            rule = INACTIVE_RULE
        ctx.set_var(LEDCTLTask.COLOR_RULE, rule)
        ctx.set_var(LEDCTLTask.FLUSH, True)
        ctx.set_var(LEDCTLTask.FORCE_FLUSH, True)


class Entry:
    def __init__(self):
        self.ctx = Context()
        self.skernel = SuspendOSKernel(self.ctx)
        self.tkernel = TimerOSKernel(self.ctx, frq=500)

        self.skernel.exec(LEDCTLTask())
        self.skernel.exec(THSensorTask())
        self.skernel.exec(BeepTask())
        self.skernel.exec(WakeupTask())

        self.tkernel.exec(TimeTask())
        self.btns = Buttons.get()

    def start(self):
        self.init_btn()
        self.ctx.set_var(MODE, MODE_TIME)
        self.skernel.setup_os()
        self.tkernel.setup_os()
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
            log.debug('SET_MODE:%s' % mode)


