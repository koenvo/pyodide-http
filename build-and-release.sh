#!/bin/bash

CURRENT_VERSION=`python -c "import pyodide_http; print(pyodide_http.__version__)"`

python setup.py sdist
python setup.py bdist_wheel

twine upload dist/pyodide_http-$CURRENT_VERSION*