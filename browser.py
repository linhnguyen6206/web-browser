import tkinter
import tkinter.font

# --- Constants & Globals ---
HEIGHT, WIDTH = 600, 800
HSTEP, VSTEP = 13, 18
SCROLL_STEP = 100

INHERITED_PROPERTIES = {
    "font-size": "16px",
    "font-style": "normal",
    "font-weight": "normal",
    "color": "black",
}

BLOCK_ELEMENTS = [
    "html", "body", "article", "section", "nav", "aside", "h1",
    "h2", "h3", "h4", "h5", "h6", "hgroup", "header", "footer",
    "address", "p", "hr", "pre", "blockquote", 
    "ol", "ul", "menu", "li", "dl", "dt", "dd", "figure", "figcaption",
    "main", "div", "table", "form", "fieldset", "legend", "details", "summary"
]

FONTS = {}
DEFAULT_STYLE_SHEET = [] # Add your default CSS rules here

def get_font(size, weight, style):
    key = (size, weight, style)
    if key not in FONTS:
        font = tkinter.font.Font(size=size, weight=weight, slant=style)
        label = tkinter.Label(font=font)
        FONTS[key] = (font, label)
    return FONTS[key][0]

def tree_to_list(tree, lst):
    lst.append(tree)
    for child in tree.children:
        tree_to_list(child, lst)
    return lst

# --- DOM Nodes ---
class Text:
    def __init__(self, text, parent=None):
        self.text = text
        self.children = []
        self.parent = parent
        self.style = {}

    def __repr__(self):
        return repr(self.text)

class Element:
    def __init__(self, tag, attributes, parent=None):
        self.tag = tag
        self.attributes = attributes
        self.children = []
        self.parent = parent
        self.style = {}

    def __repr__(self):
        return "<" + self.tag + ">"

# --- Network / Utilities ---
class URL:
    def __init__(self, url):
        # Implementation depends on earlier chapters (scheme, host, path parsing)
        self.url = url
        self.scheme = "http"
        self.host = ""
        self.port = 80
        self.path = "/"

    def resolve(self, url):
        if "://" in url: return URL(url)
        if not url.startswith("/"):
            dir, _ = self.path.rsplit("/", 1)
            url = dir + "/" + url
        if url.startswith("//"):
            return URL(self.scheme + ":" + url)
        else:
            return URL(self.scheme + "://" + self.host + ":" + str(self.port) + url)
            
    def request(self):
        # Placeholder for socket logic
        return "<html><body>Hello World</body></html>"
    
    def __str__(self):
        port_part = ":" + str(self.port)
        if self.scheme == "https" and self.port == 443:
            port_part = ""
        if self.scheme == "http" and self.port == 80:
            port_part = ""
        return self.scheme + "://" + self.host + port_part + self.path
# --- Parsers ---
class HTMLParser:
    HEAD_TAGS = [
        "base", "basefont", "bgsound", "noscript", "link",
        "meta", "title", "style", "script"
    ]
    SELF_CLOSING_TAGS = [
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    ]

    def __init__(self, body):
        self.body = body
        self.unfinished = []

    def parse(self):
        text = ""
        in_tag = False
        for c in self.body:
            if c == "<":
                in_tag = True
                if text: self.add_text(text)
                text = ""
            elif c == ">":
                in_tag = False
                self.add_tag(text)
                text = ""
            else:
                text += c
        if not in_tag and text:
            self.add_text(text)
        return self.finish()
    
    def add_text(self, text):
        if text.isspace(): return
        self.implicit_tags(None)
        parent = self.unfinished[-1]
        node = Text(text, parent)
        parent.children.append(node)

    def add_tag(self, tag):
        tag, attributes = self.get_attributes(tag)
        if tag.startswith("!"): return
        self.implicit_tags(tag)

        if tag.startswith("/"):
            if len(self.unfinished) == 1: return
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        elif tag in self.SELF_CLOSING_TAGS:
            parent = self.unfinished[-1]
            node = Element(tag, attributes, parent)
            parent.children.append(node)
        else:
            parent = self.unfinished[-1] if self.unfinished else None
            node = Element(tag, attributes, parent)
            self.unfinished.append(node)

    def get_attributes(self, text):
        parts = text.split()
        tag = parts[0].casefold()
        attributes = {}
        for attrpair in parts[1:]:
            if "=" in attrpair:
                key, value = attrpair.split("=", 1)
                attributes[key.casefold()] = value
                if len(value) > 2 and value[0] in ["'", "\""]:
                    value = value[1:-1]
            else:
                attributes[attrpair.casefold()] = ""
        return tag, attributes

    def implicit_tags(self, tag):
        while True:
            open_tags = [node.tag for node in self.unfinished]
            if open_tags == [] and tag != "html":
                self.add_tag("html")
            elif open_tags == ["html"] and tag not in ["head", "body", "/html"]:
                if tag in self.HEAD_TAGS:
                    self.add_tag("head")
                else:
                    self.add_tag("body")
            elif open_tags == ["html", "head"] and tag not in ["/head"] + self.HEAD_TAGS:
                self.add_tag("/head")
            else:
                break

    def finish(self):
        if not self.unfinished:
            self.implicit_tags(None)
        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        return self.unfinished.pop()

# Styling
class TagSelector:
    def __init__(self, tag):
        self.tag = tag
        self.priority = 1

    def matches(self, node):
        return isinstance(node, Element) and self.tag == node.tag

class DescendantSelector:
    def __init__(self, ancestor, descendant):
        self.ancestor = ancestor
        self.descendant = descendant
        self.priority = ancestor.priority + descendant.priority

    def matches(self, node):
        if not self.descendant.matches(node): return False
        while node.parent:
            if self.ancestor.matches(node.parent): return True
            node = node.parent
        return False

def cascade_priority(rule):
    selector, body = rule
    return selector.priority

def apply_style(node, rules):
    node.style = {}
    for selector, body in rules:
        if not selector.matches(node): continue
        for prop, val in body.items():
            node.style[prop] = val

    # Inherit properties
    for prop, default in INHERITED_PROPERTIES.items():
        if prop not in node.style:
            if node.parent and prop in node.parent.style:
                node.style[prop] = node.parent.style[prop]
            else:
                node.style[prop] = default

    # Handle percentage font sizes
    if node.style.get("font-size", "").endswith("%"):
        if node.parent:
            parent_font_size = node.parent.style.get("font-size", INHERITED_PROPERTIES["font-size"])
        else:
            parent_font_size = INHERITED_PROPERTIES["font-size"]
        
        node_pct = float(node.style["font-size"][:-1]) / 100
        parent_px = float(parent_font_size[:-2])
        node.style["font-size"] = str(node_pct * parent_px) + "px"

    for child in node.children:
        apply_style(child, rules)

class CSSParser:
    def __init__(self, s):
        self.s = s
        self.i = 0

    def whitespace(self):
        while self.i < len(self.s) and self.s[self.i].isspace():
            self.i += 1

    def word(self):
        start = self.i
        while self.i < len(self.s):
            if self.s[self.i].isalnum() or self.s[self.i] in "#-.%":
                self.i += 1
            else:
                break
        if not (self.i > start):
            raise Exception("Parsing error")
        return self.s[start:self.i]

    def literal(self, literal):
        if not (self.i < len(self.s) and self.s[self.i] == literal):
            raise Exception("Parsing error")
        self.i += 1

    def pair(self):
        prop = self.word()
        self.whitespace()
        self.literal(":")
        self.whitespace()
        val = self.word()
        return prop.casefold(), val
    
    def body(self):
        pairs = {}
        while self.i < len(self.s) and self.s[self.i] != "}":
            try: 
                prop, val = self.pair()
                pairs[prop] = val
                self.whitespace()
                self.literal(";")
                self.whitespace()
            except Exception:
                why = self.ignore_until([";"])
                if why == ";":
                    self.literal(";")
                    self.whitespace()
                else:
                    break
        return pairs
    
    def ignore_until(self, chars):
        while self.i < len(self.s):
            if self.s[self.i] in chars:
                return self.s[self.i]
            else:
                self.i += 1
        return None

    def selector(self):
        out = TagSelector(self.word().casefold())
        self.whitespace()
        while self.i < len(self.s) and self.s[self.i] != "{":
            tag = self.word()
            descendant = TagSelector(tag.casefold())
            out = DescendantSelector(out, descendant)
            self.whitespace()
        return out
    
    def parse(self):
        rules = []
        while self.i < len(self.s):
            try: 
                self.whitespace()
                selector = self.selector()
                self.literal("{")
                self.whitespace()
                body = self.body()
                self.literal("}")
                rules.append((selector, body))
            except Exception:
                why = self.ignore_until(["}"])
                if why == "}":
                    self.literal("}")
                    self.whitespace()
                else:
                    break
        return rules


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
        self.children.append(child)
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

    def layout_mode(self):
        if isinstance(self.node, Text): return "inline"
        elif any(isinstance(child, Element) and child.tag in BLOCK_ELEMENTS for child in self.node.children): return "block"
        elif self.node.children: return "inline"
        else: return "block"

    def layout(self):
        self.x = self.parent.x
        self.width = self.parent.width
        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y

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
        self.height = sum([child.height for child in self.children])

    def paint(self, cmds):
        bgcolor = self.node.style.get("background-color", "transparent")
        if bgcolor != "transparent":
            cmds.append(DrawRect(self.x, self.y, self.x + self.width, self.y + self.height, bgcolor))
        for child in self.children:
            child.paint(cmds)
        if bgcolor != "transparent":
            rect = DrawRect(self.self_rect(), bgcolor)
            cmds.append(rect)
        return cmds

    def new_line(self):
        self.cursor_x = 0
        last_line = self.children[-1] if self.children else None
        new_line = LineLayout(self.node, self, last_line)
        self.children.append(new_line)

    def self_rect(self):
        return Rect(self.x, self.y,
                    self.x + self.width, self.y + self.height)
    
    
class LineLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
    
    def layout(self):
        self.width = self.parent.width
        self.x = self.parent.x

        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        if style == "normal": style = "roman"
        size = int(float(self.node.style["font-size"][:-2]) * .75)
        self.font = get_font(size, weight, style)
        for word in self.children:
            word.layout()
        max_ascent = max([word.font.metrics("ascent") 
                          for word in self.children])
        baseline = self.y + 1.25 * max_ascent
        for word in self.children:
            word.y = baseline - word.font.metrics("ascent")
        max_descent = max([word.font.metrics("descent")
                           for word in self.children])
        self.height = 1.25 * (max_ascent + max_descent)

    def paint(self):
        return []

class TextLayout:
    def __init__(self, node, word, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []

        self.x = None
        self.y = None
        self.width = None
        self.height = None
        self.font = None

    def layout(self):
        weight = self.node.style.get("font-weight", "normal")
        style = self.node.style.get("font-style", "normal")
        if style == "normal": style = "roman"
        size = int(float(self.node.style.get("font-size", "16px")[:-2]) * .75)
        self.font = get_font(size, weight, style)
        self.width = self.font.measure(self.word)

        if self.previous:
            space = self.previous.font.measure(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

        self.height = self.font.metrics("linespace")

    def paint(self, cmds):
        color = self.node.style.get("color", "black")
        cmds.append(DrawText(self.x, self.y, self.word, self.font, color))
        
class InlineLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
        self.display_list = []
        self.x = self.parent.x
        self.y = self.parent.y
        self.width = self.parent.width
        self.height = 0

    def layout(self):
        self.cursor_x = 0
        self.cursor_y = 0
        self.line = []
        self.recurse(self.node)
        self.flush()
        self.height = self.cursor_y

    def recurse(self, node):
        if isinstance(node, Text):
            for word in node.text.split():
                self.word(node, word)
        else:
            if node.tag == "br":
                self.flush()
            for child in node.children:
                self.recurse(child)

    def word(self, node, word):
        color = node.style.get("color", "black")
        weight = node.style.get("font-weight", "normal")
        style = node.style.get("font-style", "normal")
        if style == "normal": style = "roman"
        size = int(float(node.style.get("font-size", "16px")[:-2]) * .75)

        font = get_font(size, weight, style)
        w = font.measure(word)

        if self.cursor_x + w > self.width:
            self.flush()

        self.line.append((self.cursor_x, word, font, color))
        self.cursor_x += w + font.measure(" ")

    def flush(self):
        if not self.line: return

        metrics = [font.metrics() for x, word, font, color in self.line]
        max_ascent = max(metric["ascent"] for metric in metrics)
        baseline = self.cursor_y + 1.25 * max_ascent

        for rel_x, word, font, color in self.line:
            x = self.x + rel_x
            y = self.y + baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, font, color))

        max_descent = max(metric["descent"] for metric in metrics)
        self.cursor_y = baseline + 1.25 * max_descent
        self.cursor_x = 0
        self.line = []

    def paint(self, cmds):
        for x, y, word, font, color in self.display_list:
            cmds.append(DrawText(x, y, word, font, color))

# --- Rendering ---
class DrawText:
    def __init__(self, x1, y1, text, font, color):
        self.x1 = x1
        self.y1 = y1
        self.text = text
        self.font = font
        self.color = color

    def execute(self, scroll, canvas):
        canvas.create_text(self.x1, self.y1 - scroll, text=self.text, fill=self.color, font=self.font, anchor="nw")

class DrawRect:
    def __init__(self, x1, y1, x2, y2, color):
        self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2
        self.color = color
        
    def execute(self, scroll, canvas):
        canvas.create_rectangle(self.x1, self.y1 - scroll, self.x2, self.y2 - scroll, fill=self.color, outline="")

class Tab:
    def __init__(self, tab_height):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(self.window, width=WIDTH, height=HEIGHT, bg="white")
        self.canvas.pack()
        self.window.bind("<Down>", self.scrolldown)
        self.scroll = 0
        self.display_list = []
        self.window.bind("<Button-1>", self.click)
        self.url = None
        self.tab_height = tab_height
        self.history = []

    def click(self, e):
        x, y = e.x, e.y
        y += self.scroll
        objs = [obj for obj in tree_to_list(self.document, [])
                if obj.x <= x < obj.x + obj.width
                and obj.y <= y < obj.y + obj.height]
        if not objs: return
        elt = objs[-1].node
        while elt:
            if isinstance(elt, Text):
                pass
            elif elt.tag == "a" and "href" in elt.attributes:
                url = self.url.resolve(elt.attributes["href"])
                return self.load(url)
            elt = elt.parent
    
    def scrolldown(self, e):
        max_y = max(self.document.height + 2*VSTEP - self.tab_height, 0)
        self.scroll = min(self.scroll + SCROLL_STEP, max_y)

    def draw(self):
        self.canvas.delete("all")
        for cmd in self.display_list:
            if cmd.rect.top > self.scroll + self.tab_height:
                continue
            if cmd.rect.bottom < self.scroll: continue
            cmd.execute(self.scroll, self.canvas)
            
    def load(self, url_str):
        self.history.append(url)
        url = URL(url_str)
        body = url.request() # Note: You'll need to implement the socket request logic in URL
        self.nodes = HTMLParser(body).parse()
        
        # Apply CSS styling
        rules = DEFAULT_STYLE_SHEET.copy()
        apply_style(self.nodes, sorted(rules, key=cascade_priority))
        
        # Layout
        self.document = DocumentLayout(self.nodes)
        self.document.layout()
        
        # Paint
        self.display_list = []
        self.document.paint(self.display_list)
        self.draw()
    
    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.load(back)

class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.tabs, self.active_tab
        )
        self.canvas.pack()
        self.window.bind("<Down>", self.handle_down)
        self.window.bind("<Button-1>", self.handle_click)

    def handle_down(self, e):
        self.active_tab.scrolldown()
        self.draw()

    def handle_click(self, e):
        if e.y < self.chrome.bottom:
            self.chrome.click(e.x, e.y)
        else:
            tab_y = e.y - self.chrome.bottom
            self.active_tab.click(e.x, e.y)
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        self.active_tab.draw(self.canvas)
        for cmd in self.chrome.paint():
            cmd.execute(0, self.canvas)

    def new_tab(self, url):
        new_tab = Tab(HEIGHT - self.chrome.bottom)
        new_tab.load(url)
        self.active_tab = self.new_tab
        self.tabs.append(new_tab)
        self.draw()
    
class Chrome:
    def __init__(self, browser):
        self.browser = browser
        self.chrome = Chrome(self)
        self.font = get_font(20, "normal", "roman")
        self.font_height = self.font.metrics("linespace")
        self.padding = 5
        self.tabbar_top = 0
        self.tabbar_bottom = self.font_height + 2*self.padding
        plus_width = self.font.measure("+") + 2*self.padding
        self.newtab_rect = Rect(
            self.padding, self.padding,
            self.padding + plus_width,
            self.padding + self.font_height)
        self.bottom = self.tabbar_bottom
        
        self.urlbar_top = self.tabbar_bottom
        self.urlbar_bottom = self.urlbar_top + \
        self.font_height + 2*self.padding
        self.bottom = self.urlbar_bottom

        back_width = self.font.measure("<") + 2*self.padding
        self.back_rect = Rect(
            self.padding,
            self.urlbar_top + self.padding,
            self.padding + back_width,
            self.urlbar_bottom - self.padding)
        
        self.address_rect = Rect(
            self.back_rect.right + self.padding,
            self.urlbar_top + self.padding,
            WIDTH - self.padding,
            self.urlbar_bottom - self.padding)
    
    def tab_rect(self, i):
        tabs_start = self.newtab_rect.right + self.padding
        tab_width = self.font.measure("Tab X") + 2*self.padding
        return Rect(
            tabs_start + tab_width * i, self.tabbar_top,
            tabs_start + tab_width * (i + 1), self.tabbar_bottom)
    
    def paint(self):
        cmds = []
        cmds.append(DrawOutline(self.newtab_rect, "black", 1))
        cmds.append(DrawText(
            self.newtab_rect.left + self.padding, 
            self.newtab_rect.top,
            "+", self.font, "black"))
        for i, tab in enumerate(self.browser.tabs):
            bounds = self.tab_rect(i)
            cmds.append(DrawLine(
                bounds.left, 0, bounds.left, bounds.bottom, 
                "black", 1))
            cmds.append(DrawLine(
                bounds.right, 0, bounds.right, bounds.bottom,
                "black", 1))
            cmds.append(DrawText(
                bounds.left + self.padding, bounds.top + self.padding, 
                "Tab {}".format(i), self.font, "black"))
            
            if tab == self.browser.active_tab:
                cmds.append(DrawLine(
                    0, bounds.bottom, bounds.left, bounds.bottom,
                    "black", 1))
                cmds.append(DrawLine(
                    bounds.right, bounds.bottom, WIDTH, bounds.bottom,
                    "black", 1))
            cmds.append(DrawRect(
                Rect(0, 0, WIDTH, self.bottom), "white"))
            cmds.append(DrawLine(0, self.bottom, WIDTH,
                                 self.bottom, "black", 1))
            
            cmds.append(DrawOutline(self.back_rect, "black", 1))
            cmds.append(DrawText(
                self.back_rect.left + self.padding,
                self.back_rect.top,
                "<", self.font, "black"))
        return cmds

    def click(self, x, y, tabs):
        if self.newtab_rect.contains_point(x, y):
            self.browser.new_tab(URL("https://www.google.com/"))
        else:
            for i, tab in enumerate(self.browser,tabs):
                if self.tab_rect(i).contains_point(x, y):
                    self.browser.active_tab = tab
                    break
                elif self.back_rect.contains_point(x, y):
                    self.browser.active_tab.go_back()

class DrawLine:
    def __init__(self, x1, y1, x2, y2, color, thickness):
        self.rect = Rect(x1, y1, x2, y2)
        self.color = color
        self.thickness = thickness
    
    def execute(self, scroll, canvas):
        canvas.create_line(
            self.rect.left, self.rect.top - scroll,
            self.rect.right, self.rect.bottom - scroll,
            fill=self.color, width=self.thickness)


class DrawOutline:
    def __init__(self, rect, color, thickness):
        self.rect = rect
        self.color = color
        self.thickness = thickness
    
    def execute(self, scroll, canvas):
        canvas.create_rectangle(
            self.rect.left, self.rect.top - scroll,
            self.rect.right, self.rect.bottom - scroll,
            width=self.thickness,
            outline=self.color)
    
class Rect:
    def __init__(self, left, top, right, bottom):
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom
    
    def contains_point(self, x, y):
        return x >= self.left and x < self.right \
        and y >= self.top and y < self.bottom

if __name__ == "__main__":
    import sys
    Browser().new_tab(URL(sys.argv[1]))
    tkinter.mainloop()
    
    