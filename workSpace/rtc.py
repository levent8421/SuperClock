import re

from machine import RTC


class RTCHelper:
    rtc = RTC()
    DATETIME_STRING_TEMPLATE = '%d-%d-%d %d:%d:%d'

    @staticmethod
    def set_time(year, month, day_of_month, hour, minute, second, microsecond=0, week=0):
        RTCHelper.rtc.datetime((year, month, day_of_month, week, hour, minute, second, microsecond))

    @staticmethod
    def current_time():
        return RTCHelper.rtc.datetime()

    @staticmethod
    def current_time_tuple6():
        time = RTCHelper.current_time()
        year = time[0]
        month = time[1]
        day = time[2]
        hour = time[4]
        minute = time[5]
        second = time[6]
        return year, month, day, hour, minute, second

    @staticmethod
    def current_time_as_string():
        time = RTCHelper.current_time_tuple6()
        return RTCHelper.DATETIME_STRING_TEMPLATE % time

    @staticmethod
    def parse(time_str):
        res = re.match(r'^(\d+)-(\d+)-(\d+)\s(\d+):(\d+):(\d+)$', time_str)
        if not res:
            return None
        y = int(res.group(1))
        m = int(res.group(2))
        d = int(res.group(3))
        h = int(res.group(4))
        mm = int(res.group(5))
        s = int(res.group(6))
        return y, m, d, h, mm, s

    @staticmethod
    def format(time):
        return RTCHelper.DATETIME_STRING_TEMPLATE % time
