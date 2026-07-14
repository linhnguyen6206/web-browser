from .dom import Text, tree_to_list
from .css import DEFAULT_STYLE_SHEET, apply_style, cascade_priority
from .js import JSContext
from .layout import VSTEP, DocumentLayout
from .url import URL


class Tab:
    def __init__(self, tab_height):
        self.tab_height = tab_height
        self.scroll = 0
        self.display_list = []
        self.url = None
        self.history = []
        self.focus = None
        self.nodes = None
        self.document = None
        self.js = None

    # -- loading & rendering -------------------------------------------------

    def load(self, url_str, payload=None):
        self.url = URL(url_str) if isinstance(url_str, str) else url_str
        self.history.append(self.url)

        body = self.url.request(payload)
        self.nodes = HTMLParserSafe(body)

        self.js = JSContext(self)
        scripts = [
            node.attributes["src"]
            for node in tree_to_list(self.nodes, [])
            if getattr(node, "tag", None) == "script" and "src" in node.attributes
        ]
        for script in scripts:
            script_url = self.url.resolve(script)
            try:
                body = script_url.request()
            except Exception:
                continue
            self.js.run(script, body)

        self.render()

    def render(self):
        if not self.nodes:
            return

        rules = list(DEFAULT_STYLE_SHEET)
        apply_style(self.nodes, sorted(rules, key=cascade_priority))

        self.document = DocumentLayout(self.nodes)
        self.document.layout()

        self.display_list = []
        self.document.paint(self.display_list)

    # -- rendering to a real canvas ------------------------------------------

    def draw(self, canvas):
        for cmd in self.display_list:
            if cmd.rect.top() > self.scroll + self.tab_height:
                continue
            if cmd.rect.bottom() < self.scroll:
                continue
            cmd.execute(self.scroll, canvas)

    # -- input handling -------------------------------------------------------

    def scrolldown(self):
        if not self.document:
            return
        max_y = max(self.document.height + 2 * VSTEP - self.tab_height, 0)
        self.scroll = min(self.scroll + 100, max_y)

    def hit_test(self, x, y):
        """Return the deepest DOM node whose layout box contains (x, y)."""
        if not self.document:
            return None
        candidates = []
        for obj in tree_to_list(self.document, []):
            if obj.x is None or obj.y is None or not obj.width or not obj.height:
                continue
            if obj.x <= x < obj.x + obj.width and obj.y <= y < obj.y + obj.height:
                candidates.append(obj)
        for obj in reversed(candidates):
            if hasattr(obj.node, "tag"):
                return obj.node
        return None

    def click(self, x, y):
        y += self.scroll

        if self.focus:
            self.focus.is_focused = False
            self.focus = None

        elt = self.hit_test(x, y)

        while elt:
            tag = getattr(elt, "tag", None)
            if tag == "button":
                if self.js.dispatch_event("click", elt):
                    return
                form = self._enclosing_form(elt)
                if form is not None:
                    self.submit_form(form)
                return
            elif tag == "input":
                if self.js.dispatch_event("click", elt):
                    return
                self.focus = elt
                elt.is_focused = True
                self.render()
                return
            elif tag == "a" and "href" in elt.attributes:
                if self.js.dispatch_event("click", elt):
                    return
                self.load(self.url.resolve(elt.attributes["href"]))
                return
            elt = getattr(elt, "parent", None)

        self.render()

    def keypress(self, char):
        if self.focus and getattr(self.focus, "tag", None) == "input":
            if self.js.dispatch_event("keydown", self.focus):
                return
            self.focus.attributes["value"] = self.focus.attributes.get("value", "") + char
            self.render()

    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.load(back)

    def _enclosing_form(self, elt):
        node = elt
        while node:
            if getattr(node, "tag", None) == "form":
                return node
            node = node.parent
        return None

    def submit_form(self, elt):
        if self.js.dispatch_event("submit", elt):
            return

        body_parts = []
        for input_elt in self.get_inputs(elt):
            name = input_elt.attributes.get("name")
            if not name:
                continue
            value = input_elt.attributes.get("value", "")
            body_parts.append("{}={}".format(_quote(name), _quote(value)))
        body = "&".join(body_parts)

        action = elt.attributes.get("action", "")
        submit_url = self.url.resolve(action)
        self.load(submit_url, payload=body)

    def get_inputs(self, elt):
        inputs = []
        for child in elt.children:
            if getattr(child, "tag", None) == "input":
                inputs.append(child)
            inputs.extend(self.get_inputs(child))
        return inputs


def _quote(s):
    import urllib.parse

    return urllib.parse.quote(s)


def HTMLParserSafe(body):
    from .dom import HTMLParser

    return HTMLParser(body).parse()
