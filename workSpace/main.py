
from machine import Pin
from neopixel import NeoPixel

from beeos import TimerOSKernel, Process
from led_display import SegScreen, SegScreenManager
from log import Log

log = Log(tag='main')


class SegScreenProcess(Process):
    def __init__(self):
        self.np = NeoPixel(Pin(27), 42)
        self.count = 0
        self.display = 0
        screen1 = SegScreen(self.np, 0)
        screen2 = SegScreen(self.np, 21)
        self.manager = SegScreenManager()
        self.manager.add_screen(screen1)
        self.manager.add_screen(screen2)
        color_rule = screen1.color_rule
        screen2.color_rule = color_rule
        gradient = color_rule.gradient
        for i in range(len(gradient)):
            gradient[i] = (5, 5, 5)

    def setup(self):
        pass

    def loop(self):
        self.count = (self.count + 1) % 10
        if self.count != 0:
            return
        self.manager.show(str(self.display))
        self.display = (self.display + 1) % 100
        self.np.write()
        self.np.write()


class Main:
    def __init__(self, kernel):
        self.kernel = kernel

    def start(self):
        self.kernel.exec(SegScreenProcess())
        log.debug('Starting...')


def main():
    kernel = TimerOSKernel()
    kernel.setup_os()
    log.info('Starting kernel...')
    kernel.run_forever()
    log.info('Starting main...')
    Main(kernel).start()


if __name__ == '__main__':
    main()

