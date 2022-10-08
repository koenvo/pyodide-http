from io import BytesIO, IOBase

from requests.adapters import BaseAdapter
from requests.utils import get_encoding_from_headers, CaseInsensitiveDict

from ._core import Request, send
from ._core import _StreamingError, _StreamingTimeout

_IS_PATCHED = False


class PyodideHTTPAdapter(BaseAdapter):
    """The Base Transport Adapter"""

    def __init__(self):
        super().__init__()

    def send(self, request, **kwargs):
        """Sends PreparedRequest object. Returns Response object.
        :param request: The :class:`PreparedRequest <PreparedRequest>` being sent.
        :param stream: (optional) Whether to stream the request content.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a :ref:`(connect timeout,
            read timeout) <timeouts>` tuple.
        :type timeout: float or tuple
        :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a string, in which case it must be a path
            to a CA bundle to use
        :param cert: (optional) Any user-provided SSL certificate to be trusted.
        :param proxies: (optional) The proxies dictionary to apply to the request.
        """
        stream = kwargs.get("stream", False)
        pyodide_request = Request(request.method, request.url)
        pyodide_request.timeout = kwargs.get("timeout", 0)
        if not pyodide_request.timeout:
            pyodide_request.timeout = 0
        pyodide_request.params = None  # this is done in preparing request now
        pyodide_request.headers = dict(request.headers)
        if request.body:
            pyodide_request.set_body(request.body)
        try:
            resp = send(pyodide_request, stream)
        except _StreamingTimeout:
            from requests import ConnectTimeout

            raise ConnectTimeout(request=pyodide_request)
        except _StreamingError:
            from requests import ConnectionError

            raise ConnectionError(request=pyodide_request)
        import requests

        response = requests.Response()
        # Fallback to None if there's no status_code, for whatever reason.
        response.status_code = getattr(resp, "status_code", None)
        # Make headers case-insensitive.
        response.headers = CaseInsensitiveDict(resp.headers)
        # Set encoding.
        response.encoding = get_encoding_from_headers(response.headers)
        if isinstance(resp.body, IOBase):
            # streaming response
            response.raw = resp.body
        else:
            # non-streaming response, make it look like a stream
            response.raw = BytesIO(resp.body)

        def new_read(self, amt=None, decode_content=False, cache_content=False):
            return self.old_read(amt)

        # make the response stream look like a urllib3 stream
        response.raw.old_read = response.raw.read
        response.raw.read = new_read.__get__(response.raw, type(response.raw))

        response.reason = ""
        response.url = request.url
        return response

    def close(self):
        """Cleans up adapter specific items."""
        pass


def patch():
    global _IS_PATCHED
    """
        Patch the requests Session. Will add a new adapter for the http and https protocols.

        Keep in mind the browser is stricter with things like CORS and this can cause some
        requests to fail that work with the regular Adapter.
    """
    if _IS_PATCHED:
        return

    import requests

    requests.sessions.Session._old_init = requests.sessions.Session.__init__

    def new_init(self):
        self._old_init()
        self.mount("https://", PyodideHTTPAdapter())
        self.mount("http://", PyodideHTTPAdapter())

    requests.sessions.Session._old_init = requests.sessions.Session.__init__
    requests.sessions.Session.__init__ = new_init

    _IS_PATCHED = True
