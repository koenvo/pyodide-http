# Pyodide-HTTP

Provides patches for widely used http libraries to make them work in Pyodide environments like JupyterLite.

## Usage

```python
# 1. Install this package
import micropip
await micropip.install('pyodide-http')

# 2. Patch requests
import pyodide_http
pyodide_http.patch_requests()
# pyodide_http.patch_urllib()  # Patch urllib
# pyodide_http.patch_all()  # Patch all libraries

# 3. Use requests
import requests
response = requests.get('https://raw.githubusercontent.com/statsbomb/open-data/master/data/lineups/15946.json')
```


import micropip
await micropip.install('pyodide-http==0.0.6')


await micropip.install('mplsoccer')
await micropip.install('requests')


from pyodide_http import patch_all
patch_all(auto_fix=True)

from mplsoccer import Radar, FontManager, grid

URL1 = ('https://raw.githubusercontent.com/googlefonts/SourceSerifProGFVersion/'
        '/main/fonts/SourceSerifPro-Regular.ttf')
serif_regular = FontManager(URL1)
## How does this work?

This package applies patches to common http libraries. How the patch works depends on the package.

All non-streaming requests are replaced with calls using `XMLHttpRequest`. 

Streaming requests (i.e. calls with `stream=True` in requests) are replaced by calls to `fetch` in a separate web-worker if (and only if) you are in a state that can support web-threading correctly, which is that cross-origin isolation is enabled, and you are running pyodide in a web-worker. Otherwise it isn't possible until WebAssembly stack-switching becomes available, and it falls back to an implementation that fetches everything then returns a stream wrapper to a memory buffer.

## Enabling Cross-Origin isolation

The implementation of streaming requests makes use of Atomics.wait and SharedArrayBuffer to do the fetch in a separate web worker. For complicated web-security reasons, SharedArrayBuffers cannot be passed to a web-worker unless you have cross-origin isolation enabled. You enable this by serving the page using the following two headers:

    Cross-Origin-Opener-Policy: same-origin
    Cross-Origin-Embedder-Policy: require-corp

Be aware that this will have effects on what you are able to embed on the page - check out https://web.dev/cross-origin-isolation-guide/ for more details.

## Supported packages

Currently the following packages can be patched:
- [requests](https://requests.readthedocs.io/en/latest/)
- [urllib](https://docs.python.org/3/library/urllib.request.html)