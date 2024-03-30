# from pyhanlp import *

import traceback
import json
import urllib
from http.server import HTTPServer, BaseHTTPRequestHandler


class HttpHandler(BaseHTTPRequestHandler):
    def _response(self, path, args):
        code=200
        rtv={'c':0,'m':'','v':''}
            
        try:
            rtv=json.dumps(rtv,ensure_ascii=False)
        except Exception as e:
            rtv={'c':2,'m':'服务器返回数据错误：'+str(e)+"\n"+traceback.format_exc(),'v':''}
            rtv=json.dumps(rtv,ensure_ascii=False)
        
        self.send_response(code)
        self.send_header('Content-type', 'text/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(rtv.encode())
    
    def do_GET(self):
        path,args=urllib.parse.splitquery(self.path)
        self._response(path, args)

    def do_POST(self):
        args = self.rfile.read(int(self.headers['content-length'])).decode("utf-8")
        self._response(self.path, args)


httpd = HTTPServer(('0.0.0.0', 9527), HttpHandler)
httpd.serve_forever()
