function Node(handle) {
    this.handle = handle;
}

Node.prototype.getAttribute = function(attr) {
    return call_python("getAttribute", this.handle, attr);
};

Node.prototype.dispatchEvent = function(type) {
    var handlers = LISTENERS[this.handle] && LISTENERS[this.handle][type];
    if (!handlers) return true;
    var do_default = true;
    for (var i = 0; i < handlers.length; i++) {
        if (handlers[i]() === false) do_default = false;
    }
    return do_default;
};

Object.defineProperty(Node.prototype, "innerHTML", {
    set: function(s) {
        call_python("innerHTML_set", this.handle, s.toString());
    },
});

var LISTENERS = {};

function querySelectorAll(selector_text) {
    var handles = call_python("querySelectorAll", selector_text);
    return handles.map(function(h) { return new Node(h); });
}

function addEventListener(node, type, fn) {
    LISTENERS[node.handle] = LISTENERS[node.handle] || {};
    LISTENERS[node.handle][type] = LISTENERS[node.handle][type] || [];
    LISTENERS[node.handle][type].push(fn);
}
