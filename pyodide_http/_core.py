import json
from dataclasses import dataclass, field
from typing import Optional, Dict
from email.parser import Parser


@dataclass
class Request:
    method: str
    url: str
    body: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)

    def set_header(self, name: str, value: str):
        self.headers[name] = value

    def set_body(self, body: str):
        self.body = body

    def set_json(self, body: dict):
        self.set_header("Content-Type", "application/json")
        self.set_body(json.dumps(body))


@dataclass
class Response:
    status_code: int
    headers: Dict[str, str]
    body: bytes


def send(request: Request) -> Response:
    from js import XMLHttpRequest
    xhr = XMLHttpRequest.new()
    xhr.responseType = "arraybuffer"

    for name, value in request.headers.items():
        xhr.setRequestHeader(name, value)

    xhr.open(request.method, request.url, False)
    xhr.send(request.body)

    headers = dict(Parser().parsestr(xhr.getAllResponseHeaders()))

    return Response(
        status_code=xhr.status,
        headers=headers,
        body=xhr.response.to_py().tobytes()
    )

