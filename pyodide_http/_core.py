import json
from dataclasses import dataclass, field
from typing import Optional, Dict
from email.parser import Parser

# need to import streaming here so that the web-worker is setup
from ._streaming import send_streaming_request


class _RequestError(Exception):
    def __init__(self, message=None, *, request=None, response=None):
        self.request = request
        self.response = response
        self.message = message
        super().__init__(self.message)


class _StreamingError(_RequestError):
    pass


class _StreamingTimeout(_StreamingError):
    pass


@dataclass
class Request:
    method: str
    url: str
    params: Optional[Dict[str, str]] = None
    body: Optional[bytes] = None
    headers: Dict[str, str] = field(default_factory=dict)
    timeout: int = 0

    def set_header(self, name: str, value: str):
        self.headers[name] = value

    def set_body(self, body: bytes):
        self.body = body

    def set_json(self, body: dict):
        self.set_header("Content-Type", "application/json; charset=utf-8")
        self.set_body(json.dumps(body).encode("utf-8"))


@dataclass
class Response:
    status_code: int
    headers: Dict[str, str]
    body: bytes


_SHOWN_WARNING = False


def show_streaming_warning():
    global _SHOWN_WARNING
    if not _SHOWN_WARNING:
        _SHOWN_WARNING = True
        from js import console

        console.warn(
            "requests can't stream data in the main thread, using non-streaming fallback"
        )


def send(request: Request, stream: bool = False) -> Response:
    if request.params:
        from js import URLSearchParams

        params = URLSearchParams.new()
        for k, v in request.params.items():
            params.append(k, v)
        request.url += "?" + params.toString()

    from js import XMLHttpRequest

    try:
        from js import importScripts

        _IN_WORKER = True
    except ImportError:
        _IN_WORKER = False
    # support for streaming workers (in worker )
    if stream:
        if not _IN_WORKER:
            stream = False
            show_streaming_warning()
        else:
            result = send_streaming_request(request)
            if result == False:
                stream = False
            else:
                return result

    xhr = XMLHttpRequest.new()
    # set timeout only if pyodide is in a worker, because
    # there is a warning not to set timeout on synchronous main thread
    # XMLHttpRequest https://developer.mozilla.org/en-US/docs/Web/API/XMLHttpRequest/timeout
    if _IN_WORKER and request.timeout != 0:
        xhr.timeout = int(request.timeout * 1000)

    if _IN_WORKER:
        xhr.responseType = "arraybuffer"
    else:
        xhr.overrideMimeType("text/plain; charset=ISO-8859-15")

    xhr.open(request.method, request.url, False)
    for name, value in request.headers.items():
        xhr.setRequestHeader(name, value)

    xhr.send(request.body)

    headers = dict(Parser().parsestr(xhr.getAllResponseHeaders()))

    if _IN_WORKER:
        body = xhr.response.to_py().tobytes()
    else:
        body = xhr.response.encode("ISO-8859-15")

    return Response(status_code=xhr.status, headers=headers, body=body)
