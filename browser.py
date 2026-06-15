import tkinter.font
HEIGHT, WIDTH = 600, 800
HSTEP, VSTEP = 13, 18
SCROLL_STEP = 100

INHERITED_PROPERTIES = {
    "font-size": "16px",
    "font-style": "normal",
    "font-weight": "normal",
    "color": "black",
}
class Text:
    def __init__(self, text):
        self.text = text

class Tag:
    def __init__(self, tag):
        self.tag = tag

class Layout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
        
    def layout(self, tokens):
        self.cursor_x = HSTEP
        self.cursor_y = VSTEP
        self.weight = "normal"
        self.style = "roman"
        self.display_list = []

        for tok in tokens:
            if isinstance(tok, Text):
                self.word(tok.text)
            elif tok.tag == "i":
                self.style = "italic"
            elif tok.tag == "/i":
                self.style = "roman"
            elif tok.tag == "b":
                self.style = "bold"
            elif tok.tag == "/b":
                self.weight = "normal"
            elif tok.tag == "br":
                self.flush()
            elif tok.tag == "/p":
                self.flush()
                self.cursor_y += VSTEP

        return self.display_list

    def word(self, node, word):
        color = node.style["color"]
        weight = node.style["font-weight"]
        style = node.style["font-style"]
        self.line.append((self.cursor_x, word, font, color))
        if style == "normal": style = "roman"
        size = int(float(node.style["font-size"][:-2]) * .75)

        font = get_font(size, weight, style)
        w = font.measure(word)

        if self.cursor_x + w > self.width:
            self.flush()

        self.line.append(
            (self.cursor_x, word, font)
        )

        self.cursor_x += w + font.measure(" ")

    def flush(self):
        if not self.line:
            return

        metrics = [font.metrics() for x, word, font in self.line]

        max_ascent = max(
            metric["ascent"]
            for metric in metrics
        )

        baseline = self.cursor_y + 1.25 * max_ascent

        for rel_x, word, font in self.line:
            x = self.x + rel_x

            y = (
                self.y
                + baseline
                - font.metrics("ascent")
            )

            self.display_list.append((x, y, word, font, color))

        max_descent = max(
            metric["descent"]
            for metric in metrics
        )

        self.cursor_y = (
            baseline
            + 1.25 * max_descent
        )

        self.cursor_x = 0
        self.line = []

    def open_tag(self, tag):
        if tag == "i":
            self.style = "italic"
        elif tag == "b":
            self.weight = "bold"
        elif tag == "small":
            self.size -= 2
        elif tag == "big":
            self.size += 4

    def close_tag(self, tag):
        if tag == "i":
            self.style = "roman"
        elif tag == "b":
            self.weight = "normal"
        elif tag == "small":
            self.size += 2
        elif tag == "big":
            self.size -= 4
        elif tag == "p":
            self.flush()
            self.cursor_y += VSTEP
    
    def recurse(self, node):
        if isinstance(node, Text):
            for word in node.text.split():
                self.word(node, word)
        else:
            if node.tag == "br":
                self.flush()
            for child in node.children:
                self.recurse(child)

    def tree_to_list(tree, list):
        list.append(tree)
        for child in tree.children:
            tree_to_list(child, list)
        return list

class Browser:
    def draw(self):
        for x, y, c in self.display_list:
            self.canvas.create_text(x, y - self.scroll, text=c)   

    def scrolldown(self, e):
        self.canvas.delete("all")
        self.scroll += SCROLL_STEP
        self.draw()
    
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT,
            bg = "white"
        )
        self.canvas.pack()
        self.window.bind("<Down>", self.scrolldown)
        self.scroll = 0
    
    def load(self, url):
        self.document = Layout(self.nodes)
        self.document.layout()
        self.display_list = self.document.display_list
        rules = DEFAULT_STYLE_SHEET.copy()
        style(self.nodes, sorted(rules, key=cascade_priority))
        links = [node.attributes["href"] 
                 for node in tree_to_list(self.nodes, [])
                 if isinstance(node, Element)
                 and node.tag == "link"
                 and node.attributes.get("rel") == "stylesheet"
                 and "href" in node.attributes]
        self.draw()
        for link in links:
            style_url = url.resolve(link)
            try:
                body = style_url.request()
            except:
                continue
            rules.extend(CSSParser(body).parse())

    def lex(self, body):
        tokens = []
        in_tag = False
        tag_text = ""
        text_buffer = ""

        for c in body:
            if c == "<":
                in_tag = True
                if text_buffer:
                    tokens.append(Text(text_buffer))
                    text_buffer = ""
                tag_text = ""
            elif c == ">":
                in_tag = False
                tokens.append(Tag(tag_text))
            elif in_tag:
                tag_text += c
            else:
                text_buffer += c

            if text_buffer:
                tokens.append(Text(text_buffer))
            
        return tokens
        
class Text:
    def __init__(self, text, parent):
        self.text = text
        self.children = []
        self.parent = parent


    def __init__(self, body):
        self.body = body
        self.unfinished = []

class Element:
    def __init__(self, tag, attributes, parent):
        self.tag = tag
        self.attributes = attributes
        self.children = []
        self.parent = parent

class HTMLParser:
    HEAD_TAGS = [
        "base", "basefont", "bgsound", "noscript", "link",
        "meta", "title", "style", "script"
    ]
    def __init__(self, body):
        self.body = body
        self.unifinished = []

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

    def finish(self):
        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        
        return self.unfinished.pop()
    
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
            node = Element(tag, parent)
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

    
    
    def finish(self):
        if not self.unfinished:
            self.implicit_tags(None)
        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        
        return self.unfinished.pop()
    
    def print_tree(self, node, indent = 0):
        print(" " * indent + str(node.value))
        for child in node.children:
            self.print_tree(child, indent + 2)
    
    def implicit_tags(self, tag):
        while True:
            open_tags = [node.tag for node in self.unfinished]
            if open_tags == [] and tag != "html":
                self.add_tag("html")
            elif open_tags == ["html"] \
                and tag not in ["head", "body", "/html"]:
                if tag in self.HEAD_TAGS:
                    self.add_tag("head")
                else:
                    self.add_tag("body")
            elif open_tags == ["html", "head"] and \
                tag not in ["/head"] + self.HEAD_TAGS:
                self.add_tag("/head")
            else:
                break
    def tree_to_list(tree, list):
        list.append(tree)
        for child in tree.children:
            tree_to_list(child, list)
        return list
    
class Text:
    def __repr_(self):
        return repr(self.text)
    
class Element:
    def __repr__(self):
        return "<" + self.tag + ">"
    
    def __init__(self, tag, attributes, parent):
        self.tag = tag
        self.attributes = attributes
    
FONTS = {}
def get_font(size, weight, style):
    key = (size, weight, style)
    if key not in FONTS:
        font = tkinter.font.Font(size=size, weight=weight, slant=style)
        label = tkinter.Label(font=font)
        FONTS[key] = (font, label)

    return FONTS[key][0]

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

    def paint(self):
        return []
    

BLOCK_ELEMENTS = [
            "html", "body", "article", "section", "nav", "aside", "h1",
            "h2", "h3", "h4", "h5", "h6", "hgroup", "header", "footer",
            "address", "p", "hr", "pre", "blockquote", 
            "ol", "ul", "menu", "li", "dl", "dt", "dd", "figure", "figcaption",
            "main", "div", "table", "form", "fieldset", "legend", "details", "summary"
        ]

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
        if isinstance(self.node, Text):
            return "inline"

        elif any(
            isinstance(child, Element)
            and child.tag in BLOCK_ELEMENTS
            for child in self.node.children
        ):
            return "block"

        elif self.node.children:
            return "inline"

        else:
            return "block"

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
                next = BlockLayout(child, self, previous)

                self.children.append(next)
                previous = next

        else:
            self.cursor_x = 0
            self.cursor_y = 0

            self.weight = "normal"
            self.style = "roman"
            self.size = 16

            self.display_list = []
            self.line = []

            self.recurse(self.node)
            self.flush()

        for child in self.children:
            child.layout()

        self.height = sum(
            child.height for child in self.children
        )

        if mode == "inline":
            self.height = self.cursor_y

    def paint(self, cmds):
        x, y = self.x, self.y
        width, height = self.width, self.height

        bgcolor = self.node.style.get("background-color",
                                      "transparent")
        if bgcolor != "transparent":
            x2, y2 = x + width, y + height
            cmds.append(DrawRect(x, y, x2, y2, bgcolor))

        border = self.node.style.get("border", None)
        if border:
            cmds.append(DrawBorder(x, y, x + width, y + height, border))

        if hasattr(self, "text") and self.text:
            cmds.append(DrawText(x, y, self.text))

        for child in self.children:
            child.paint(cmds)
        if self.layout_mode() == "inline":
            for x, y, word, font, color in self.display_list:
                cmds.append(DrawText(x, y, word, font, color))

class DrawText:
    def __init__(self, x1, y1, text, font, color):
        self.x1 = x1
        self.y1 = y1
        self.text = text
        self.font = font
        self.color = color

    def execute(self, scroll, canvas):
        canvas.create_text(
            self.x1,
            self.y1 - scroll,
            text=self.text,
            fill=self.color,
            font=self.font
        )

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
    
    def style(node, rules):
        node.style = {}
        for selector, body in rules:
            if not selector.matches(node): continue
            if node.style["font-size"].endswith("%"):
                
                if node.parent:
                    parent_font_size = node.parent.style["font-size"]
                else:
                    parent_font_size = INHERITED_PROPERTIES["font-size"]
                node_pct = float(node.style["font-size"][:-1]) / 100
                parent_px = float(parent_font_size[:-2])
                node.style["font-size"] = str(node_pct * parent_px) + "px"
        for child in node.children:
            style(child)

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
        if not self.descenda.matches(node): return False
        while node.parent:
            if self.ancestor.matches(node.parent): return True
            node = node.parent
        return False
    
    def cascade_priority(rule):
        selector, body = rule
        return selector.priority

class URL:
    def resolve(self, url):
        if "://" in url: return URL(url)
        if not url.startswith("/"):
            dir, _ = self.path.rsplit("/", 1)
            url = dir + "/" + url
        if url.startswith("//"):
            return URL(self.scheme + ":" + url)
        else:
            return URL(self.scheme + "://" + self.host + \
                       ":" + str(self.port) + url)
        
