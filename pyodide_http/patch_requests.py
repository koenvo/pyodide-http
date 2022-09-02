from io import BytesIO

import requests
from requests.utils import get_encoding_from_headers, CaseInsensitiveDict

from ._core import Request, send

_IS_PATCHED = False


class Session:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    @staticmethod
    def request(method, url, **kwargs):
        request = Request(method, url)
        request.headers = kwargs.get('headers', {})
        if 'json' in kwargs:
            request.set_json(kwargs['json'])
        resp = send(request)

        response = requests.Response()
        # Fallback to None if there's no status_code, for whatever reason.
        response.status_code = getattr(resp, "status_code", None)
        # Make headers case-insensitive.
        response.headers = CaseInsensitiveDict(resp.headers)
        # Set encoding.
        response.encoding = get_encoding_from_headers(response.headers)
        response.raw = BytesIO(resp.body)
        response.reason = ''
        response.url = url
        return response


def patch():
    global _IS_PATCHED
    """
        Patch the requests Session. Will add a new adapter for the http and https protocols.

        Keep in mind the browser is stricter with things like CORS and this can cause some
        requests to fail that work with the regular Adapter.
    """
    if _IS_PATCHED:
        return

    class Sessions:
        Session = Session

    requests.api.sessions = Sessions()

    _IS_PATCHED = True
