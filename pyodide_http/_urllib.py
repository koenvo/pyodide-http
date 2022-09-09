from io import BytesIO

import urllib.request
from http.client import HTTPResponse


from ._core import Request, send

_IS_PATCHED = False


class FakeSock:
    def __init__(self, data):
        self.data = data

    def makefile(self, mode):
        return BytesIO(self.data)


def urlopen(url):
    method = 'GET'
    data = None
    headers = {}
    if isinstance(url, urllib.request.Request):
        method = url.get_method()
        data = url.data
        headers = dict(url.header_items())
        url = url.full_url

    request = Request(method, url, headers=headers, body=data)
    resp = send(request)

    # Build a fake http response
    response_data = (
        b'HTTP/1.1 ' + str(resp.status_code).encode('ascii') + b"\n" +
        "\n".join(
            f"{key}: {value}" for key, value in resp.headers.items()
        ).encode('ascii') + b"\n\n" +
        resp.body
    )

    response = HTTPResponse(FakeSock(response_data))
    response.begin()
    return response


def patch():
    global _IS_PATCHED

    if _IS_PATCHED:
        return

    urllib.request.urlopen = urlopen

    _IS_PATCHED = True
