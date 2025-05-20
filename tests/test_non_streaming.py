from pathlib import Path
import os.path
import glob

from pytest_pyodide import run_in_pyodide, spawn_web_server
from pytest import fixture, fail


@fixture(scope="module")
def dist_dir(request):
    # return pyodide dist dir relative to top level of webserver
    p = Path(request.config.getoption("--dist-dir")).resolve()
    p = p.relative_to(Path(__file__).parent.parent)
    return p


@fixture(scope="module")
def web_server_base():
    server_folder = Path(__file__).parent.parent
    with spawn_web_server(server_folder) as server:
        server_hostname, server_port, _ = server
        base_url = f"http://{server_hostname}:{server_port}/"
        yield base_url


def _install_package(selenium, base_url):
    wheel_folder = Path(__file__).parent.parent / "dist"

    selenium.run_js(
        f"""
        await pyodide.loadPackage("micropip");
        """
    )
    selenium.run_async(f'import micropip\nawait micropip.install("requests")')

    for wheel in wheel_folder.glob("*.whl"):
        url = base_url + "dist/" + str(wheel.name)
        selenium.run_async(f'await micropip.install("{url}")')

        selenium.run(
            """
            import pyodide_http
            pyodide_http.patch_all()
            import requests
            """
        )
        break
    else:
        fail(f"no pre-built *.whl found in {os.path.relpath(wheel_folder)}")


def test_install_package(selenium_standalone, web_server_base):
    _install_package(selenium_standalone, web_server_base)


def test_requests_get(selenium_standalone, dist_dir, web_server_base):
    _install_package(selenium_standalone, web_server_base)

    @run_in_pyodide
    def test_fn(selenium_standalone, base_url):
        import requests

        import pyodide_http._requests
        assert pyodide_http._requests._IS_PATCHED

        import pyodide_http as ph

        print("get:", base_url)
        url = f"{base_url}/yt-4.1.4-cp311-cp311-emscripten_3_1_46_wasm32.whl"

        # The test web server sets "Access-Control-Allow-Origin: *" which disallows sending credentials.
        # Credentials are explicitly disabled, although that's the default, to exercise the option code.
        with ph.option_context(with_credentials=False):
            resp = requests.get(url)

        data = resp.content
        assert resp.request.url == url

        return len(data)

    assert test_fn(selenium_standalone, f"{web_server_base}{dist_dir}/") == 78336150


def test_urllib_get(selenium_standalone, dist_dir, web_server_base):
    _install_package(selenium_standalone, web_server_base)

    @run_in_pyodide
    def test_fn(selenium_standalone, base_url):
        import urllib.request

        import pyodide_http._urllib
        assert pyodide_http._urllib._IS_PATCHED

        import pyodide_http as ph

        # The test web server sets "Access-Control-Allow-Origin: *" which disallows sending credentials.
        # Credentials are explicitly disabled, although that's the default, to exercise the option code.
        ph.set_with_credentials_option(False)

        print("get:", base_url)
        url = f"{base_url}/yt-4.1.4-cp311-cp311-emscripten_3_1_46_wasm32.whl"
        with urllib.request.urlopen(url) as resp:
            data = resp.read()
            assert resp.url == url

            return len(data)

    assert test_fn(selenium_standalone, f"{web_server_base}{dist_dir}/") == 78336150


def test_requests_404(selenium_standalone, dist_dir, web_server_base):
    _install_package(selenium_standalone, web_server_base)

    @run_in_pyodide
    def test_fn(selenium_standalone, base_url):
        import requests

        import pyodide_http._requests
        assert pyodide_http._requests._IS_PATCHED

        print("get:", base_url)
        resp = requests.get(f"{base_url}/surely_this_file_does_not_exist.hopefully.")
        response = resp.status_code
        return response

    assert test_fn(selenium_standalone, f"{web_server_base}{dist_dir}/") == 404
