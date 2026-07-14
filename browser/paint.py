import skia

NAMED_COLORS = {
    "black": "#000000",
    "white": "#ffffff",
    "red": "#ff0000",
    "gray": "#808080",
    "lightblue": "#add8e6",
    "orange": "#ffa500",
    "transparent": None,
}


def parse_color(color):
    if color is None or color == "transparent":
        return skia.ColorTRANSPARENT
    if color.startswith("#") and len(color) == 7:
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        return skia.Color(r, g, b)
    if color in NAMED_COLORS:
        return parse_color(NAMED_COLORS[color])
    return skia.ColorBLACK


class Rect:
    def __init__(self, left, top, right, bottom):
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom

    def contains_point(self, x, y):
        return self.left <= x < self.right and self.top <= y < self.bottom


class DrawText:
    def __init__(self, x1, y1, text, font, color):
        self.rect = skia.Rect.MakeLTRB(
            x1, y1,
            x1 + font.measureText(text),
            y1 - font.getMetrics().fAscent + font.getMetrics().fDescent,
        )
        self.x1 = x1
        self.y1 = y1
        self.text = text
        self.font = font
        self.color = color

    def execute(self, scroll, canvas):
        paint = skia.Paint(AntiAlias=True, Color=parse_color(self.color))
        baseline = self.rect.top() - scroll - self.font.getMetrics().fAscent
        canvas.drawString(self.text, float(self.rect.left()), baseline, self.font, paint)


class DrawRect:
    def __init__(self, rect, color):
        self.rect = rect
        self.color = color

    def execute(self, scroll, canvas):
        paint = skia.Paint(AntiAlias=True, Color=parse_color(self.color))
        sk_rect = skia.Rect.MakeLTRB(
            self.rect.left, self.rect.top, self.rect.right, self.rect.bottom
        )
        canvas.drawRect(sk_rect.makeOffset(0, -scroll), paint)


class DrawRRect:
    def __init__(self, rect, radius, color):
        self.rect = rect
        self.radius = radius
        self.color = color
        sk_rect = skia.Rect.MakeLTRB(rect.left, rect.top, rect.right, rect.bottom)
        self.rrect = skia.RRect.MakeRectXY(sk_rect, radius, radius)

    def execute(self, scroll, canvas):
        paint = skia.Paint(AntiAlias=True, Color=parse_color(self.color))
        canvas.drawRRect(self.rrect.makeOffset(0, -scroll), paint)


class DrawLine:
    def __init__(self, x1, y1, x2, y2, color, thickness=1):
        self.rect = skia.Rect.MakeLTRB(x1, y1, x2, y2)
        self.color = color
        self.thickness = thickness

    def execute(self, scroll, canvas):
        path = skia.Path()
        path.moveTo(self.rect.left(), self.rect.top() - scroll)
        path.lineTo(self.rect.right(), self.rect.bottom() - scroll)
        paint = skia.Paint(
            Color=parse_color(self.color),
            StrokeWidth=self.thickness,
            Style=skia.Paint.kStroke_Style,
        )
        canvas.drawPath(path, paint)


class DrawOutline:
    def __init__(self, rect, color, thickness=1):
        self.rect = rect
        self.color = color
        self.thickness = thickness

    def execute(self, scroll, canvas):
        paint = skia.Paint(
            Color=parse_color(self.color),
            StrokeWidth=self.thickness,
            Style=skia.Paint.kStroke_Style,
        )
        sk_rect = skia.Rect.MakeLTRB(
            self.rect.left, self.rect.top, self.rect.right, self.rect.bottom
        )
        canvas.drawRect(sk_rect.makeOffset(0, -scroll), paint)
