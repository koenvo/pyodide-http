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

## How does this work?

This package applies patches to common http libraries. How the patch works depends on the package.

All requests are replaced with calls using `XMLHttpRequest`. 

## Supported packages

Currently the following packages can be patched:
- [requests](https://requests.readthedocs.io/en/latest/)
- [urllib](https://docs.python.org/3/library/urllib.request.html)