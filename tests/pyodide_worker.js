importScripts("https://cdn.jsdelivr.net/pyodide/v0.25.1/full/pyodide.js");

onmessage = async function (e) {
  try {
    const data = e.data;
    for (let key of Object.keys(data)) {
      if (key !== "python") {
        // Keys other than python must be arguments for the python script.
        // Set them on self, so that `from js import key` works.
        self[key] = data[key];
      }
    }

    if (!loadPyodide.inProgress && !this.self.pyodide) {
        console.log("Init pyodide");
        self.pyodide = await loadPyodide();
    }
    await self.pyodide.loadPackagesFromImports(data.python);
    let results = await self.pyodide.runPythonAsync(data.python);
    results=results.toJs({dict_converter:Object.fromEntries});
    self.postMessage({ results });
  } catch (e) {
    // if you prefer messages with the error
    self.postMessage({ error: e.message + "\n" + e.stack });
    // if you prefer onerror events
    // setTimeout(() => { throw err; });
  }
};
