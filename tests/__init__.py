import os.path

from PIL import ImageMath


def respath(*path):
    return os.path.join('tests', 'images', *path)


def avg_diff(im1, im2, *, threshold=0):
    assert im1.size == im2.size
    assert im1.mode == im2.mode

    size = im1.width * im1.height

    histos = [
        ImageMath.eval("abs(ch1 - ch2)", ch1=ch1, ch2=ch2).convert('L').histogram()
        for ch1, ch2 in zip(im1.split(), im2.split())
    ]
    return [
        sum(i * val for i, val in enumerate(histo[threshold:])) / size / 256
        for histo in histos
    ]
