from PIL import Image

W = 80
H = 80


def as16bit_color(c):
    return ((c[0] & 0xF8) << 8) | ((c[1] & 0xFC) << 3) | ((c[2] & 0xF8) >> 3)


def main():
    image = Image.open('./icon_keqin.jpg')
    image = image.resize((W, H))
    res = []
    for x in range(W):
        for y in range(H):
            c = image.getpixel((x, H - y - 1))
            c = as16bit_color(c)
            res.append(c.to_bytes(length=2, byteorder='big', signed=False))
    with open('icon_keqin.data', 'wb') as f:
        for b in res:
            f.write(b)


if __name__ == '__main__':
    main()
