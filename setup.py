from distutils.core import setup

import setuptools


def setup_package():
    from pyodide_http import __version__

    setup(
        name="pyodide_http",
        version=__version__,
        author="Koen Vossen",
        author_email="info@koenvossen.nl",
        url="https://github.com/koenvo/pyodide-http",
        packages=setuptools.find_packages(exclude=["tests"]),
        license="MIT",
        description="Patch requests, urllib and urllib3 to make them work in Pyodide",
        long_description="Patch requests, urllib and urllib3 to make them work in Pyodide",
        long_description_content_type="text/markdown",
        classifiers=[],
        install_requires=[],
        ext_modules=[],
    )


if __name__ == "__main__":
    setup_package()
