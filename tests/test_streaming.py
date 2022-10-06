import contextlib
import http.server
import multiprocessing
import queue
import tempfile
import shutil
import sys
import os
import socketserver

from pathlib import Path
import glob

from pytest_pyodide import run_in_pyodide
from pytest import fixture

@contextlib.contextmanager
def spawn_web_server_custom(server_folder,custom_headers):
    tmp_dir = tempfile.mkdtemp()
    log_path = Path(tmp_dir) / "http-server.log"
    q = multiprocessing.Queue()
    p = multiprocessing.Process(target=_run_web_server, args=(q, log_path, server_folder,custom_headers))

    try:
        p.start()
        port = q.get(timeout=20)
        hostname = "127.0.0.1"

        print(
            f"Spawning webserver at http://{hostname}:{port} "
            f"(see logs in {log_path})"
        )
        yield hostname, port, log_path
    finally:
        q.put("TERMINATE")
        p.join()
        shutil.rmtree(tmp_dir)

def _run_web_server(q, log_filepath, dist_dir,custom_headers):
    """Start the HTTP web server
    Parameters
    ----------
    q : Queue
      communication queue
    log_path : pathlib.Path
      path to the file where to store the logs
    """

    os.chdir(dist_dir)

    log_fh = log_filepath.open("w", buffering=1)
    sys.stdout = log_fh
    sys.stderr = log_fh

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format_, *args):
            print(
                "[%s] source: %s:%s - %s"
                % (self.log_date_time_string(), *self.client_address, format_ % args)
            )

        def end_headers(self):
            # Enable Cross-Origin Resource Sharing (CORS)
            for k,v in custom_headers.items():
                self.send_header(k,v)
            self.send_header("Access-Control-Allow-Origin", "*")
            super().end_headers()

    with socketserver.TCPServer(("", 0), Handler) as httpd:
        host, port = httpd.server_address
        print(f"Starting webserver at http://{host}:{port}")
        httpd.server_name = "test-server"  # type: ignore[attr-defined]
        httpd.server_port = port  # type: ignore[attr-defined]
        q.put(port)

        def service_actions():
            try:
                if q.get(False) == "TERMINATE":
                    print("Stopping server...")
                    sys.exit(0)
            except queue.Empty:
                pass

        httpd.service_actions = service_actions  # type: ignore[assignment]
        httpd.serve_forever()


@fixture(scope="module")
def dist_dir(request):
    # return pyodide dist dir relative to top level of webserver
    p=Path(request.config.getoption('--dist-dir')).resolve()
    p=p.relative_to(Path(__file__).parent.parent)
    return p

@fixture(scope="module")
def web_server_non_isolated():
    server_folder=Path(__file__).parent.parent
    with spawn_web_server_custom(server_folder,{}) as server:
        server_hostname, server_port, _ = server
        base_url=f"http://{server_hostname}:{server_port}/"
        yield base_url

@fixture(scope="module")
def web_server_isolated():
    server_folder=Path(__file__).parent.parent
    with spawn_web_server_custom(server_folder,{"Cross-Origin-Opener-Policy":"same-origin","Cross-Origin-Embedder-Policy":"require-corp"}) as server:
        server_hostname, server_port, _ = server
        base_url=f"http://{server_hostname}:{server_port}/"
        yield base_url

@fixture(scope="module")
def big_file_path(dist_dir):
    test_size=0
    test_filename=None
    for f in (Path(__file__).parent.parent / dist_dir).iterdir():
        if f.is_file():
            sz=f.stat().st_size
            if sz>test_size:
                test_size=sz
                test_filename=f.name
    return dist_dir / test_filename,test_size



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

def get_install_package_code(base_url):
    wheel_folder=Path(__file__).parent.parent / "dist"

    code="""
import micropip
await micropip.install("requests")
"""

    for wheel in wheel_folder.glob("*.whl"):
        url = base_url +"dist/" + str(wheel.name)
        code+=f'await micropip.install("{url}")\n'

    code+="""
import pyodide_http
pyodide_http.patch_all()
import requests
"""
    return code



def test_requests_stream_isolated_worker(selenium_standalone,web_server_isolated,big_file_path):
    test_filename,test_size=big_file_path
    fetch_url=f"{web_server_isolated}{test_filename}"
    resp=selenium_standalone.run_webworker(
        get_install_package_code(web_server_isolated)+
        f"""
import requests
print("get:",'{fetch_url}')
resp=requests.get('{fetch_url}',stream=True)
data_len=0
data_count=0
while True:
    this_len=len(resp.raw.read())
    data_len+=this_len
    data_count+=1
    if this_len==0:
        break
assert data_count>1
data_len
        """)

    assert resp==big_file_path[1] 

def test_requests_stream_non_isolated_worker(selenium_standalone,web_server_non_isolated,big_file_path):
    test_filename,test_size=big_file_path
    fetch_url=f"{web_server_non_isolated}{test_filename}"
    resp=selenium_standalone.run_webworker(
        get_install_package_code(web_server_non_isolated)+
        f"""
import requests
print("get:",'{fetch_url}')
resp=requests.get('{fetch_url}',stream=True)
data_len=0
data_count=0
while True:
    this_len=len(resp.raw.read())
    data_len+=this_len
    data_count+=1
    if this_len==0:
        break
assert data_count>1
data_len
        """)

    assert resp==big_file_path[1] 



def test_requests_404_isolated(selenium_standalone,dist_dir,web_server_isolated):
    _install_package(selenium_standalone,web_server_isolated)

    @run_in_pyodide
    def test_fn(selenium_standalone,base_url):
        import requests
        print("get:",base_url)
        resp=requests.get(f"{base_url}/surely_this_file_does_not_exist.hopefully.")
        response=resp.status_code
        return response

    assert test_fn(selenium_standalone,f"{web_server_isolated}{dist_dir}/")==404

def test_install_package_isolated(selenium_standalone,web_server_isolated):
    _install_package(selenium_standalone,web_server_isolated)


def test_requests_stream_isolated_main_thread(selenium_standalone,dist_dir,web_server_isolated,big_file_path):
    _install_package(selenium_standalone,web_server_isolated)
    test_filename,test_size=big_file_path
    @run_in_pyodide
    def test_fn(selenium_standalone,fetch_url):
        import requests
        print("get:",fetch_url)
        resp=requests.get(fetch_url,stream=True)
        data=resp.content
        return len(data)

    assert test_fn(selenium_standalone,f"{web_server_isolated}{test_filename}")==test_size
