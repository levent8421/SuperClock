from io import BytesIO


class ASCIIFont:
    WIDTH = 8
    HEIGHT = 16

    def __init__(self, file):
        self.file = file
        self.codes = """ !"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz{|}~"""
        with open('ascii.font', 'rb') as f:
            self.font_bytes = f.read()

    def _find_idx(self, c):
        for i in range(len(self.codes)):
            cc = self.codes[i]
            if cc == c:
                return i
            if cc > c:
                return len(self.codes) - 1
        return len(self.codes) - 1

    def find_font(self, c):
        idx = self._find_idx(c)
        return self.font_bytes[idx * 16: idx * 16 + 16]

    def char_img(self, c, bc, fc, out):
        font = self.find_font(c)
        if not out:
            out = BytesIO()
        lines = len(font)
        for i in range(8):
            for ri in range(lines):
                r = font[lines - ri - 1]
                if r & (0x80 >> i):
                    c = fc
                else:
                    c = bc
                for ci in c:
                    out.write(ci.to_bytes(1, 'big'))
        return out

    def str_img(self, s, bc, fc):
        res = BytesIO()
        for c in s:
            self.char_img(c, bc, fc, res)
        return res
