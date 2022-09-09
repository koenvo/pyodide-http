import json
from dataclasses import dataclass, field
from typing import Optional, Dict
from email.parser import Parser


@dataclass
class Request:
    method: str
    url: str
    body: Optional[bytes] = None
    headers: Dict[str, str] = field(default_factory=dict)

    def set_header(self, name: str, value: str):
        self.headers[name] = value

    def set_body(self, body: bytes):
        self.body = body

    def set_json(self, body: dict):
        self.set_header("Content-Type", "application/json; charset=utf-8")
        self.set_body(json.dumps(body).encode('utf-8'))


@dataclass
class Response:
    status_code: int
    headers: Dict[str, str]
    body: bytes


def send(request: Request) -> Response:
    from js import XMLHttpRequest
    try:
        from js import importScripts
        _IN_WORKER = True
    except ImportError:
        _IN_WORKER = False

    xhr = XMLHttpRequest.new()
    for name, value in request.headers.items():
        xhr.setRequestHeader(name, value)

    if _IN_WORKER:
        xhr.responseType = "arraybuffer"
    else:
        xhr.overrideMimeType('text/plain; charset=ISO-8859-15')

    xhr.open(request.method, request.url, False)
    xhr.send(request.body)

    headers = dict(Parser().parsestr(xhr.getAllResponseHeaders()))

    if _IN_WORKER:
        body = xhr.response.to_py().tobytes()
    else:
        body = xhr.response.encode('ISO-8859-15')

    return Response(
        status_code=xhr.status,
        headers=headers,
        body=body
    )

