from board_driver import Buttons
from log import Log

log = Log(tag='main')
btns = Buttons.get()

entry = None


def main():
    global entry
    if btns.read(Buttons.BOTTOM):
        log.info('Starting Kernel...')
        from bootstrap import Entry
        log.info('Kernel stopped!')
    else:
        log.info('ENABLE DEBUG...')
        from debug import Entry
        log.info('ENABLE DEBUG OK')

    entry = Entry()
    entry.start()


if __name__ == '__main__':
    main()
