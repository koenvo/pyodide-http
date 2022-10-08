try:
    from js import XMLHttpRequest

    _SHOULD_PATCH = True
except ImportError:
    _SHOULD_PATCH = False

__version__ = "0.1.0"


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
