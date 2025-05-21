try:
    from js import XMLHttpRequest

    _SHOULD_PATCH = True
except ImportError:
    _SHOULD_PATCH = False

from contextlib import ContextDecorator
from dataclasses import dataclass


__version__ = "0.2.3"


@dataclass
class Options:
    with_credentials: bool = False


_options = Options()


def set_with_credentials_option(value: bool):
    global _options
    _options.with_credentials = value


class option_context(ContextDecorator):
    def __init__(self, with_credentials=False):
        self._with_credentials = with_credentials
        self._default_options = None

    def __enter__(self):
        global _options
        self._default_options = _options

        _options = Options()
        _options.with_credentials = self._with_credentials

    def __exit__(self, *_):
        if self._default_options is not None:
            global _options
            _options = self._default_options


def patch_requests(continue_on_import_error: bool = False):
    if not _SHOULD_PATCH:
        return
    try:
        from ._requests import patch
    except ImportError:
        if continue_on_import_error:
            return
        raise
    else:
        patch()


def patch_urllib(continue_on_import_error: bool = False):
    if not _SHOULD_PATCH:
        return

    try:
        from ._urllib import patch
    except ImportError:
        if continue_on_import_error:
            return
        raise
    else:
        patch()


def should_patch():
    return _SHOULD_PATCH


def patch_all():
    patch_requests(continue_on_import_error=True)
    patch_urllib(continue_on_import_error=True)
