from pathlib import Path
import glob

from pytest_pyodide import run_in_pyodide, spawn_web_server
from pytest import fixture

@fixture(scope="module")
def dist_dir(request):
    # return pyodide dist dir relative to top level of webserver
    p=Path(request.config.getoption('--dist-dir')).resolve()
    p=p.relative_to(Path(__file__).parent.parent)
    return p

@fixture(scope="module")
def web_server_base():
    server_folder=Path(__file__).parent.parent
    with spawn_web_server(server_folder) as server:
        server_hostname, server_port, _ = server
        base_url=f"http://{server_hostname}:{server_port}/"
        yield base_url

def _install_package(selenium,base_url):
    wheel_folder=Path(__file__).parent.parent / "dist"

    selenium.run_js(
        f"""
        await pyodide.loadPackage("micropip");
        """
    )
    selenium.run_async(f'import micropip\nawait micropip.install("requests")')

    for wheel in wheel_folder.glob("*.whl"):
        url = base_url +"dist/" + str(wheel.name)
        selenium.run_async(f'await micropip.install("{url}")')

        selenium.run(
            """
            import pyodide_http
            pyodide_http.patch_all()
            import requests
            """
        )


def test_install_package(selenium_standalone,web_server_base):
    _install_package(selenium_standalone,web_server_base)


def test_requests_get(selenium_standalone,dist_dir,web_server_base):
    _install_package(selenium_standalone,web_server_base)

    @run_in_pyodide
    def test_fn(selenium_standalone,base_url):
        import requests
        print("get:",base_url)
        resp=requests.get(f"{base_url}/yt-4.0.4-cp310-cp310-emscripten_3_1_14_wasm32.whl")
        data=resp.content
        return len(data)

    assert test_fn(selenium_standalone,f"{web_server_base}{dist_dir}/")==11373926

def test_requests_404(selenium_standalone,dist_dir,web_server_base):
    _install_package(selenium_standalone,web_server_base)

    @run_in_pyodide
    def test_fn(selenium_standalone,base_url):
        import requests
        print("get:",base_url)
        resp=requests.get(f"{base_url}/surely_this_file_does_not_exist.hopefully.")
        response=resp.status_code
        return response

    assert test_fn(selenium_standalone,f"{web_server_base}{dist_dir}/")==404
