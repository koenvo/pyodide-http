
SUCCESS_HEADER=-1
SUCCESS_EOF=-2
ERROR_TIMEOUT=-3
ERROR_EXCEPTION=-4

_STREAMING_WORKER_CODE="""
let SUCCESS_HEADER=-1
let SUCCESS_EOF=-2
let ERROR_TIMEOUT=-3
let ERROR_EXCEPTION=-4

self.addEventListener("message", async function (event) {
    const encoder = new TextEncoder();
    const intBuffer = new Int32Array(event.data.buffer);
    const byteBuffer=new Uint8Array(event.data.buffer,8)
    try {
        const response = await fetch(event.data.url, event.data.fetchParams);
        // return the headers first via textencoder
        var headers = [];
        for (const pair of response.headers.entries()) {
            headers.push([pair[0], pair[0]]);
        }
        headerObj = { headers: headers, status: response.status };
        const headerText = JSON.stringify(headerObj);
        let headerBytes=encoder.encode(headerText);
        let written = headerBytes.length;
        byteBuffer.set(headerBytes);
        intBuffer[1] = written;
        // magic number for header ready
        Atomics.store(intBuffer, 0, SUCCESS_HEADER);
        Atomics.notify(intBuffer,0);
        Atomics.wait(intBuffer, 0, intBuffer[0], 500);// wait until it resets to zero which means read
        const reader = response.body.getReader();
        while (true) {
            let { value, done } = await reader.read();
            if (value) {
                // pass a chunk back to the sharedarraybuffer - wait half a second or else assume it
                // didn't get consumed for some reason and abort
                let curOffset = 0;
                while (curOffset < value.length) {

                    let curLen = value.length - curOffset;
                    if (curLen > byteBuffer.length) {
                        curLen = byteBuffer.length;
                    }
                    byteBuffer.set(value.subarray(curOffset, curOffset+curLen), 0)
                    Atomics.store(intBuffer, 0, curLen);// store current length in bytes
                    Atomics.notify(intBuffer,0);
                    Atomics.wait(intBuffer, 0, intBuffer[0]);// wait until it resets to zero 
                    if(intBuffer[0]!=0)
                    {
                        throw "Error - intBuffer not read";
                    }
                    // which means it is read by the other end
                    curOffset += curLen;
                }
            }
            if (done) {
                Atomics.store(intBuffer, 0, SUCCESS_EOF);
                Atomics.notify(intBuffer,0);
                // finished reading successfully
                // return from event handler 
                return;
            }
        }
    }
    catch (error) {
            console.log("Request exception:",error);
            let errorBytes=encoder.encode(errorBytes);
            let written = errorBytes.length;
            byteBuffer.set(errorBytes);
            intBuffer[1] = written;
            Atomics.store(intBuffer, 0, ERROR_EXCEPTION);
            Atomics.notify(intBuffer,0);
        }
    }

);

"""

from urllib.request import Request
from pyodide.ffi import to_js
import js,json,io

def _obj_from_dict(d:dict):
    return to_js(d,dict_converter = js.Object.fromEntries)

class _ReadStream(io.RawIOBase):
    def __init__(self,int_buffer,byte_buffer):
        self.int_buffer=int_buffer
        self.byte_buffer=byte_buffer
        self.read_pos=0
        self.read_len=0

    def readable(self):
        return True

    def writeable(self):
        return False
    
    def seekable(self):
        return False

    def readall(self,byte_obj):
        pass 

    def readinto(self,byte_obj):
        if not self.int_buffer:
            return 0
        if self.read_len==0:
            # wait for the worker to send something
            js.Atomics.store(self.int_buffer,0,0) 
            js.Atomics.notify(self.int_buffer,0)
            js.Atomics.wait(self.int_buffer,0,0,5000) 
            data_len=self.int_buffer[0]
            if data_len>0:
                self.read_len=data_len
                self.read_pos=0
            else:
                # EOF, free the buffers and return zero
                self.read_len=0
                self.read_pos=0
                self.int_buffer=None
                self.byte_buffer=None
                return 0
        # copy from int32array to python bytes
        ret_length=min(self.read_len,len(byte_obj))
        self.byte_buffer.subarray(self.read_pos,self.read_pos+ret_length).assign_to(byte_obj[0:ret_length])
        self.read_len-=ret_length
        self.read_pos+=ret_length
        return ret_length

class _Streaming_Fetcher:
    def __init__(self):
        # make web-worker and data buffer on startup
        dataBlob=js.Blob.new([_STREAMING_WORKER_CODE],_obj_from_dict({"type":'application/javascript'}))
        dataURL=js.URL.createObjectURL(dataBlob)
        self._worker=js.Worker.new(dataURL)

    def send(self,request):
        from ._core import Response
        headers=_obj_from_dict(request.headers)
        body=request.body
        fetch_data=_obj_from_dict({"headers":headers,"body":body,"method":request.method})
        # start the request off in the worker

        shared_buffer=js.SharedArrayBuffer.new(1048576)
        int_buffer=js.Int32Array.new(shared_buffer)
        byte_buffer=js.Uint8Array.new(shared_buffer,8)

        js.Atomics.store(int_buffer,0,0)
        js.Atomics.notify(int_buffer,0);
        absolute_url=js.URL.new(request.url,js.location).href
        self._worker.postMessage(_obj_from_dict({"buffer":shared_buffer,"url":absolute_url,"fetchParams":fetch_data}))
        # wait for the worker to send something
        js.Atomics.wait(int_buffer,0,0,10000) 
        if int_buffer[0]==0:
            from requests import ConnectTimeout
            raise ConnectTimeout(request=request,response=None)
        if int_buffer[0]==SUCCESS_HEADER:
            # got response
            # header length is in second int of intBuffer
            string_len=int_buffer[1]
            # decode the rest to a JSON string 
            decoder=js.TextDecoder.new()
            # this does a copy (the slice) because decode can't work on shared array
            # for some silly reason
            json_str=decoder.decode(byte_buffer.slice(0,string_len))
            # get it as an object
            response_obj=json.loads(json_str)
            return Response(
                status_code=response_obj["status"],
                headers=response_obj["headers"],
                body=io.BufferedReader(_ReadStream(int_buffer,byte_buffer),buffer_size=1048576)
            )
        if int_buffer[0]==ERROR_EXCEPTION:
            string_len=int_buffer[1]
            # decode the error string
            decoder=js.TextDecoder.new()
            json_str=decoder.decode(byte_buffer.slice(0,string_len))
            from requests import ConnectionError
            raise ConnectionError(request=request,response=None)


from js import crossOriginIsolated
if crossOriginIsolated:
    _fetcher=_Streaming_Fetcher()
else:
    _fetcher=None

def send_streaming_request(request: Request):
    global _fetcher
    if _fetcher:
        return _fetcher.send(request)
    else:
        from js import console
        console.warning("requests can't stream data because site is not cross origin isolated")
        return False
