from .dom import Text
from .paint import DrawRRect, DrawRect, DrawText, Rect
import skia

HEIGHT, WIDTH = 600, 800
HSTEP, VSTEP = 13, 18
SCROLL_STEP = 100
INPUT_WIDTH_PX = 200

BLOCK_ELEMENTS = [
    "html", "body", "article", "section", "nav", "aside", "h1",
    "h2", "h3", "h4", "h5", "h6", "hgroup", "header", "footer",
    "address", "p", "hr", "pre", "blockquote",
    "ol", "ul", "menu", "li", "dl", "dt", "dd", "figure", "figcaption",
    "main", "div", "table", "form", "fieldset", "legend", "details", "summary",
]

FONTS = {}


def get_font(size, weight, style):
    key = (weight, style, size)
    if key in FONTS:
        return FONTS[key]

    skia_weight = skia.FontStyle.kBold_Weight if weight == "bold" else skia.FontStyle.kNormal_Weight
    skia_slant = skia.FontStyle.kItalic_Slant if style == "italic" else skia.FontStyle.kUpright_Slant
    skia_width = skia.FontStyle.kNormal_Width
    style_info = skia.FontStyle(skia_weight, skia_width, skia_slant)
    typeface = skia.Typeface("Arial", style_info)
    font = skia.Font(typeface, size)
    FONTS[key] = font
    return font


def _font_for(node):
    weight = node.style.get("font-weight", "normal")
    style = node.style.get("font-style", "normal")
    if style == "normal":
        style = "roman"
    size = int(float(node.style.get("font-size", "16px")[:-2]) * 0.75)
    return get_font(size, weight, style)


class DocumentLayout:
    def __init__(self, node):
        self.node = node
        self.parent = None
        self.children = []
        self.x = HSTEP
        self.y = VSTEP
        self.width = WIDTH - 2 * HSTEP
        self.height = None

    def layout(self):
        child = BlockLayout(self.node, self, None)
        self.children = [child]
        child.layout()
        self.height = child.height

    def paint(self, cmds):
        for child in self.children:
            child.paint(cmds)


class BlockLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
        self.x = None
        self.y = None
        self.width = None
        self.height = None
        self.cursor_x = 0

    def layout_mode(self):
        if isinstance(self.node, Text):
            return "inline"
        if any(hasattr(child, "tag") and child.tag in BLOCK_ELEMENTS for child in self.node.children):
            return "block"
        if self.node.children or self.node.tag == "input":
            return "inline"
        return "block"

    def should_paint(self):
        return isinstance(self.node, Text) or self.node.tag not in ("input", "button")

    def layout(self):
        self.x = self.parent.x
        self.width = self.parent.width
        self.y = (self.previous.y + self.previous.height) if self.previous else self.parent.y

        mode = self.layout_mode()
        if mode == "block":
            previous = None
            for child in self.node.children:
                next_node = BlockLayout(child, self, previous)
                self.children.append(next_node)
                previous = next_node
        else:
            self.new_line()
            self.recurse(self.node)

        for child in self.children:
            child.layout()
        self.height = sum(child.height for child in self.children) if self.children else 0

    def paint(self, cmds):
        if self.should_paint():
            bgcolor = self.node.style.get("background-color", "transparent")
            if bgcolor != "transparent":
                radius = float(self.node.style.get("border-radius", "0px")[:-2])
                cmds.append(DrawRRect(self.self_rect(), radius, bgcolor))
        for child in self.children:
            child.paint(cmds)

    def new_line(self):
        self.cursor_x = 0
        last_line = self.children[-1] if self.children else None
        self.children.append(LineLayout(self.node, self, last_line))

    def self_rect(self):
        return Rect(self.x, self.y, self.x + self.width, self.y + self.height)

    def recurse(self, node):
        if isinstance(node, Text):
            for word in node.text.split():
                self.word(node, word)
        else:
            if node.tag == "br":
                self.new_line()
            elif node.tag in ("input", "button"):
                self.input(node)
            else:
                for child in node.children:
                    self.recurse(child)

    def word(self, node, word):
        font = _font_for(node)
        w = font.measureText(word)
        if self.cursor_x + w > self.width:
            self.new_line()
        line = self.children[-1]
        previous_word = line.children[-1] if line.children else None
        text_node = TextLayout(node, word, line, previous_word)
        line.children.append(text_node)
        self.cursor_x += w + font.measureText(" ")

    def input(self, node):
        w = INPUT_WIDTH_PX
        if self.cursor_x + w > self.width:
            self.new_line()
        line = self.children[-1]
        previous_word = line.children[-1] if line.children else None
        input_node = InputLayout(node, line, previous_word)
        line.children.append(input_node)
        font = _font_for(node)
        self.cursor_x += w + font.measureText(" ")


class LineLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
        self.x = None
        self.y = None
        self.width = None
        self.height = None

    def layout(self):
        self.width = self.parent.width
        self.x = self.parent.x
        self.y = (self.previous.y + self.previous.height) if self.previous else self.parent.y

        for word in self.children:
            word.layout()

        if not self.children:
            self.height = 0
            return

        max_ascent = max(-word.font.getMetrics().fAscent for word in self.children)
        baseline = self.y + 1.25 * max_ascent
        for word in self.children:
            word.y = baseline + word.font.getMetrics().fAscent
        max_descent = max(word.font.getMetrics().fDescent for word in self.children)
        self.height = 1.25 * (max_ascent + max_descent)

    def paint(self, cmds):
        for child in self.children:
            child.paint(cmds)


class TextLayout:
    def __init__(self, node, word, parent, previous):
        self.node = node
        self.word = word
        self.parent = parent
        self.previous = previous
        self.children = []
        self.x = None
        self.y = None
        self.width = None
        self.height = None
        self.font = None

    def layout(self):
        self.font = _font_for(self.node)
        self.width = self.font.measureText(self.word)

        if self.previous:
            space = self.previous.font.measureText(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

        metrics = self.font.getMetrics()
        self.height = 1.25 * (metrics.fDescent - metrics.fAscent)

    def paint(self, cmds):
        color = self.node.style.get("color", "black")
        cmds.append(DrawText(self.x, self.y, self.word, self.font, color))


class InputLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
        self.x = None
        self.y = None
        self.width = INPUT_WIDTH_PX
        self.height = None
        self.font = None

    def layout(self):
        self.font = _font_for(self.node)

        if self.previous:
            space = self.previous.font.measureText(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

        metrics = self.font.getMetrics()
        self.height = 1.25 * (metrics.fDescent - metrics.fAscent)

    def _text(self):
        if self.node.tag == "input":
            return self.node.attributes.get("value", "")
        if self.node.tag == "button":
            if len(self.node.children) == 1 and isinstance(self.node.children[0], Text):
                return self.node.children[0].text
        return ""

    def self_rect(self):
        return Rect(self.x, self.y, self.x + self.width, self.y + self.height)

    def paint(self, cmds):
        bgcolor = self.node.style.get("background-color", "transparent")
        if bgcolor != "transparent":
            cmds.append(DrawRect(self.self_rect(), bgcolor))

        text = self._text()
        color = self.node.style.get("color", "black")
        cmds.append(DrawText(self.x, self.y, text, self.font, color))

        if self.node.is_focused:
            cx = self.x + self.font.measureText(text)
            from .paint import DrawLine
            cmds.append(DrawLine(cx, self.y, cx, self.y + self.height, "black", 1))
