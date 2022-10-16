from machine import Pin, PWM


class Buttons:
    LEFT = 13
    BOTTOM = 35
    RIGHT = 5
    _ins = None

    @staticmethod
    def get():
        s = Buttons
        if s._ins:
            return s._ins
        s._ins = Buttons()
        return s._ins

    def __init__(self):
        self.btns = {
            Buttons.LEFT: Pin(Buttons.LEFT, Pin.IN),
            Buttons.RIGHT: Pin(Buttons.RIGHT, Pin.IN),
            Buttons.BOTTOM: Pin(Buttons.BOTTOM, Pin.IN),
        }
        self.status = {}
        for i in self.btns:
            pin = self.btns[i]
            self.status[i] = pin.value()
        self.cb = None

    def read(self, btn):
        if btn in self.btns:
            return self.btns[btn].value()
        return 0

    def listen(self, cb):
        self.cb = cb
        _self = self

        def cb_wrapper(btn):
            _self.on_change(btn)

        for i in self.btns:
            btn = self.btns[i]
            btn.irq(cb_wrapper)

    def on_change(self, btn):
        btn_no = None
        for i in self.btns:
            b = self.btns[i]
            if b == btn:
                btn_no = i
        nv = btn.value()
        if nv == self.status[btn_no]:
            return
        self.status[btn_no] = nv
        if not self.cb:
            return
        self.cb(btn_no, nv)


class Beep:
    _ins = None

    @staticmethod
    def get():
        s = Beep
        if s._ins:
            return s._ins
        s._ins = Beep()
        return s._ins

    def __init__(self):
        self.out = PWM(Pin(19))
        self.out.duty(0)
        self.vol = 100

    def volume(self, vol):
        self.vol = vol

    def enable(self):
        self.out.duty(self.vol)

    def disable(self):
        self.out.duty(0)

    def freq(self, freq):
        self.out.freq(freq)


LED4 = Pin(27)
LED3 = Pin(26)
LED2 = Pin(25)
LED1 = Pin(33)
WAKEUP = Pin(14, Pin.IN)
TH_SENSOR = Pin(4)

D_MOSI = Pin(23)
D_MISO = Pin(12)
D_SCLK = Pin(18)
D_DC = 21
D_RES = 22
D_CS = 16
D_BKL = Pin(17, Pin.OUT)
