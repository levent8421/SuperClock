import binascii
import time

import machine
import network

from log import Log

Timer = machine.Timer
Pin = machine.Pin
log = Log(tag='kernel')


class KernelApi:
    @staticmethod
    def get_sn():
        return binascii.hexlify(machine.unique_id()).decode()


class Process:
    def setup(self):
        pass

    def loop(self, ctx):
        pass

    def finish(self):
        pass


class Context:
    def __init__(self):
        self.vars = {}

    def get_var(self, name, def_var=None):
        if name in self.vars:
            return self.vars[name]
        return def_var

    def set_var(self, name, var):
        self.vars[name] = var


class OSKernel:
    TICKS_MS = 'ticks_ms'

    def __init__(self, ctx):
        self.ctx = ctx

    def set_var(self, name, var):
        self.ctx.set_var(name, var)

    def get_var(self, name, def_var=None):
        return self.ctx.get_var(name, def_var)

    def setup_os(self):
        pass

    def run_forever(self):
        pass

    def exec(self, proc):
        pass

    def shutdown(self):
        pass


TIMER_FRQ = 100


class StatePin:
    def __init__(self):
        self.pin = Pin(32, mode=Pin.OUT)
        self.aws_on = False
        self.blk_inter = 1
        self.blk_ct = 0
        self.state = False
        self.off()

    def on(self):
        self.state = True
        self.pin.off()

    def off(self):
        if self.aws_on:
            self.on()
            return
        self.state = False
        self.pin.on()

    def set_blink_interval(self, interval):
        self.blk_inter = interval

    def set_aws_on(self, aws_on):
        self.aws_on = aws_on

    def blink(self):
        self.blk_ct += 1
        if self.blk_ct < self.blk_inter:
            return
        self.blk_ct = 0
        if self.state:
            self.off()
        else:
            self.on()


state_pin = StatePin()


class TimerOSKernel(OSKernel):
    def __init__(self, ctx, timer=0, frq=TIMER_FRQ):
        super().__init__(ctx)
        self._timer_no = timer
        self.timer = Timer(timer)
        self.frq = frq
        self._tasks = []

    def setup_os(self):
        pass

    def _loop(self):
        state_pin.blink()
        for task in self._tasks:
            cmplt = False
            try:
                ticks = time.ticks_ms()
                self.set_var(OSKernel.TICKS_MS, ticks)
                cmplt = task.loop(self)
            except Exception as e:
                log.warn('Error on run task[%s]' % task, e)
            if cmplt:
                log.debug('Task[%s] complete!' % task)
                self._tasks.remove(task)
                try:
                    task.finish()
                except Exception as e:
                    log.error('Task[%s] error on finish!' % task, e)

    def run_forever(self):
        self.timer.init(mode=Timer.PERIODIC, period=self.frq, callback=lambda t: self._loop())

    def shutdown(self):
        self.timer.deinit()

    def exec(self, proc):
        try:
            proc.setup()
            if hasattr(proc, 'NAME'):
                self.set_var(proc.NAME, proc)
        except Exception as e:
            log.error('Error on proc setup', e)
        else:
            self._tasks.append(proc)


class SuspendOSKernel(OSKernel):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.tasks = []
        self.running = False

    def setup_os(self):
        self.running = True

    def run_forever(self):
        task_index = 0
        while self.running:
            task_len = len(self.tasks)
            if not task_len:
                continue
            task = self.tasks[task_index]
            ticks = time.ticks_ms()
            self.set_var(OSKernel.TICKS_MS, ticks)
            try:
                task.loop(self)
            except Exception as e:
                log.error('Error on loop: %s' % task, e)
            task_index += 1
            task_index %= task_len

    def exec(self, proc):
        self.tasks.append(proc)
        proc.setup()
        if hasattr(proc, 'NAME'):
            self.set_var(proc.NAME, proc)

    def shutdown(self):
        self.running = False


class WifiConnectProcess(Process):
    NAME = 'wifi_task'

    def scan(self):
        return self.wifi.scan()

    def __init__(self, ssid, passwd, cb):
        self.ssid = ssid
        self.passwd = passwd
        self.wifi = network.WLAN(network.STA_IF)
        self.cb = cb
        self.connecting = False
        self.connected = False

    def setup(self):
        self.wifi.active(True)
        log.debug('Connecting WIFI with [%s/%s]:' % (self.ssid, self.passwd))

    def loop(self, ctx):
        if self.wifi.isconnected():
            state_pin.set_blink_interval(5)
            if self.connected:
                return False
            else:
                self.connected = True
                self.cb()
        else:
            state_pin.set_blink_interval(1)
            if self.connected:
                log.debug('WIFI reconnecting...')
                self.connect()
            else:
                if not self.connecting:
                    log.debug('WIFI DoConnecting...')
                    self.connect()

    def connect(self):
        self.wifi.connect(self.ssid, self.passwd)
        self.connected = False
        self.connecting = True


class Ap:
    def __init__(self, ssid, password='', ip='192.168.4.1'):
        self.ap = network.WLAN(network.AP_IF)
        self.ssid = ssid
        self.password = password
        self.ip = ip

    def start(self):
        ip = self.ip
        self.ap.active(True)
        if self.password:
            self.ap.config(essid=self.ssid, authmode=network.AUTH_WPA_WPA2_PSK, password=self.password)
        else:
            self.ap.config(essid=self.ssid, authmode=network.AUTH_OPEN)
        self.ap.ifconfig((ip, '255.255.255.0', ip, '8.8.8.8'))
        log.info('WIFI AP IP=[%s]' % ip)
        state_pin.set_aws_on(True)
        state_pin.on()

    def stop(self):
        self.ap.active(False)
        state_pin.set_aws_on(False)
        state_pin.off()

