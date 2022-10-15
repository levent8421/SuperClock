import sys

from rtc import RTCHelper

TRACE = 0
DEBUG = 1
INFO = 2
WARN = 3
ERROR = 4

LOG_LEVEL_TABLE = {TRACE: 'trace', DEBUG: 'debug', INFO: 'info', WARN: 'warn', ERROR: 'error'}


def exception_info(e=None):
    if not e:
        return ''
    if hasattr(sys, 'print_exception'):
        sys.print_exception(e)
    return ' exception=%s' % repr(e)


class Log:
    _TEMPLATE = '==[%s-%s][%s]:%s %s'

    def __init__(self, tag='Default', level=DEBUG):
        self._tag = tag
        self._level = level

    def log(self, level, msg, e=None):
        if level < self._level:
            return
        time = RTCHelper.current_time_as_string()
        if level in LOG_LEVEL_TABLE:
            level_str = LOG_LEVEL_TABLE[level]
        else:
            level_str = 'USER-%d' % level
        log_info = Log._TEMPLATE % (time, level_str, self._tag, msg, exception_info(e))
        print(log_info)

    def trace(self, msg, e=None):
        self.log(TRACE, msg, e)

    def debug(self, msg, e=None):
        self.log(DEBUG, msg, e)

    def info(self, msg, e=None):
        self.log(INFO, msg, e)

    def warn(self, msg, e=None):
        self.log(WARN, msg, e)

    def error(self, msg, e=None):
        self.log(ERROR, msg, e)


log = Log()
