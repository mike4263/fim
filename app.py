#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler
import os
from pathlib import Path
from fim import Epigram, EpigramStore, SoloEpigramImporter, \
    FortuneFileImporter, Bucket, Impression


CONTAINER_PATH = "/var/fim/fim.db"
HOME_DIR = str(Path.home())+"/.fim/fim.db"

def get_db():
    if os.path.exists(CONTAINER_PATH):
        # this is a container with a mounted fim dir
        db = EpigramStore(CONTAINER_PATH)
    elif os.path.exists(HOME_DIR):
        db = EpigramStore(HOME_DIR)
    else:
        # This means we are running inside of the container
        db = EpigramStore("/app/fim.db", force_random=True)
    return db

globalDB = get_db()

class S(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def _html(self, message):
        """This just generates an HTML document that includes `message`
        in the body. Override, or re-write this do do more interesting stuff.
        """
        content =  globalDB.get_epigram().content
        #content = f"<html><body><h1>{message}</h1></body></html>"
        return content.encode("utf8")  # NOTE: must return a bytes object!

    def do_GET(self):
        self._set_headers()
        self.wfile.write(self._html("hi!"))

    def do_HEAD(self):
        self._set_headers()

    def do_POST(self):
        self._set_headers()
        self.wfile.write(self._html("POST!"))


def run(server_class=HTTPServer, handler_class=S, addr="localhost", port=8000):
    server_address = (addr, port)
    httpd = server_class(server_address, handler_class)

    print(f"Starting httpd server on {addr}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    run(addr="0.0.0.0", port=8080)


"""
The HTTP Code was writen by Brad under the MIT license
Copyright 2021 Brad Montgomery
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and 
associated documentation files (the "Software"), to deal in the Software without restriction, 
including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, 
and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, 
subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial 
portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT 
LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. 
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, 
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.    
"""
