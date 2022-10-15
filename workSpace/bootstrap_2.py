import time

from beeos import SuspendOSKernel, Process, TimerOSKernel
from board_driver import Beep, Buttons, WAKEUP
from led_display import seg_screen, group1, group2, DEFAULT_COLOR_RULE, FixedColorRule
from log import Log
from rtc import RTCHelper

log = Log(tag='Bootstrap')
beep = Beep.get()
btns = Buttons.get()

DEFAULT_BEEP_SEQ = ((2500, 100), (2900, 100), (3000, 100))
BTN_BEEP_SEQ = ((3000, 100), (2900, 100), (2500, 100))


class LEDProcess(Process):
    def __init__(self):
        self.ctx = ctx

    def setup(self, kernel):
        self.ctx = kernel


class WakeupProcess(Process):
    NAME = 'wakeup_process'

    def __init__(self, display_task):
        self.display_task = display_task
        self.inactive_rule = DEFAULT_COLOR_RULE
        self.active_rule = FixedColorRule()
        self.active_rule.set_color((5, 0, 0), (0, 5, 0), (0, 0, 5))

    def loop(self):
        if WAKEUP.value():
            rule = self.active_rule
        else:
            rule = self.inactive_rule
        self.display_task.set_color_rule(rule)


class BeepProcess(Process):
    NAME = 'beep_process'

    def __init__(self):
        self.next = time.ticks_ms()
        self.seq = ()
        self.seq_index = 0

    def notity(self, seq):
        self.seq = seq
        self.seq_index = 0

    def loop(self):
        if self.seq_index >= len(self.seq):
            beep.disable()
            return
        beep.enable()
        now = time.ticks_ms()
        if now >= self.next:
            item = self.seq[self.seq_index]
            self.next = now + item[1]
            beep.freq(item[0])
            self.seq_index += 1


class DisplayProcess(Process):
    NAME = 'display_process'

    def __init__(self):
        self.seg_visible = False
        self.loop_count = 0

    def loop(self):
        if self.seg_visible:
            seg_screen.hide()
        else:
            seg_screen.show()
        self.seg_visible = not self.seg_visible
        if self.loop_count % 10 == 0:
            self.show_time()
        self.loop_count += 1

    def show_time(self):
        time_tuple = RTCHelper.current_time_tuple6()
        h = str(time_tuple[3])
        m = str(time_tuple[4])
        group1.show(m)
        group2.show(h)

    def set_color_rule(self, rule):
        group1.set_color_rule(rule)
        group2.set_color_rule(rule)
        seg_screen.set_color_rule(rule)


class Entry:
    def __init__(self):
        self.beep_task = None

    def start(self):
        kernel = SuspendOSKernel()
        timer_kernel = TimerOSKernel(frq=500)
        kernel.setup_os()
        timer_kernel.setup_os()
        self.init_beep()
        self.init_btn()
        self.init_screen()
        timer_kernel.run_forever()
        kernel.run_forever()

    def init_btn(self):
        def btn_cb(btn, v):
            log.debug('btn %s/%s' % (btn, v))
            if v:
                self.beep_task.notity(BTN_BEEP_SEQ)
            else:
                self.beep_task.notity(DEFAULT_BEEP_SEQ)

        btns.listen(btn_cb)

    def init_screen(self):
        task = DisplayProcess()
        timer_kernel.exec(task)
        wakeup_task = WakeupProcess(task)
        kernel.exec(wakeup_task)

    def init_beep(self):
        self.beep_task = BeepProcess()
        kernel.exec(self.beep_task)
        self.beep_task.notity(DEFAULT_BEEP_SEQ)
