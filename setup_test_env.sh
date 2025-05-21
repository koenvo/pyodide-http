#!/bin/bash
set -e



# install chrome
wget -nc https://dl-ssl.google.com/linux/linux_signing_key.pub
cat linux_signing_key.pub | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/linux_signing_key.gpg  >/dev/null
sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/chrome.list'
sudo apt update
sudo apt install google-chrome-stable


# pyodide build and test
pip install pytest
pip install pyodide-build pytest-pyodide
# install chromedriver stuff for selenium to control chrome
pip install selenium webdriver-manager
pip install chromedriver-binary-auto
# make sure chromedriver is on path
export PATH=$PATH:`chromedriver-path`

# run the tests
cd tests
# get pyodide to tests/pyodide
wget https://github.com/pyodide/pyodide/releases/download/0.25.1/pyodide-0.25.1.tar.bz2
tar xjf pyodide-0.25.1.tar.bz2
cp "$(python3 -c 'import os.path; import pytest_pyodide; print(os.path.dirname(pytest_pyodide.__file__))')/_templates/test.html" pyodide/
cp "$(python3 -c 'import os.path; import pytest_pyodide; print(os.path.dirname(pytest_pyodide.__file__))')/_templates/webworker_dev.js" pyodide/
pytest . --dist-dir ./pyodide --rt chrome -v
