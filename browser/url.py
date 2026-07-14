import socket
import ssl


class URL:
    def __init__(self, url: str):
        self.url = url

        if "://" not in url:
            # Not a fully-qualified URL; treat as a bare path on http.
            self.scheme = "http"
            rest = url
        else:
            self.scheme, rest = url.split("://", 1)

        assert self.scheme in ("http", "https"), "Unknown scheme {!r}".format(self.scheme)
        self.port = 443 if self.scheme == "https" else 80

        if "/" not in rest:
            rest += "/"
        host, self.path = rest.split("/", 1)
        self.path = "/" + self.path

        if ":" in host:
            host, port = host.split(":", 1)
            self.port = int(port)
        self.host = host

    def resolve(self, url: str) -> "URL":
        if "://" in url:
            return URL(url)
        if not url.startswith("/"):
            directory, _ = self.path.rsplit("/", 1)
            url = directory + "/" + url
        if url.startswith("//"):
            return URL(self.scheme + ":" + url)
        return URL("{}://{}:{}{}".format(self.scheme, self.host, self.port, url))

    def request(self, payload: str = None) -> str:
        method = "POST" if payload else "GET"

        s = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
        s.connect((self.host, self.port))
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)

        request = "{} {} HTTP/1.0\r\n".format(method, self.path)
        request += "Host: {}\r\n".format(self.host)
        if payload:
            request += "Content-Length: {}\r\n".format(len(payload.encode("utf8")))
        request += "\r\n"
        if payload:
            request += payload

        s.send(request.encode("utf8"))
        response = s.makefile("b")

        statusline = response.readline().decode("utf8")
        _version, status, explanation = statusline.split(" ", 2)

        headers = {}
        while True:
            line = response.readline().decode("utf8")
            if line == "\r\n":
                break
            header, value = line.split(":", 1)
            headers[header.casefold()] = value.strip()

        body = response.read().decode("utf8")
        s.close()
        return body

    def __str__(self):
        port_part = ":" + str(self.port)
        if self.scheme == "https" and self.port == 443:
            port_part = ""
        if self.scheme == "http" and self.port == 80:
            port_part = ""
        return self.scheme + "://" + self.host + port_part + self.path
