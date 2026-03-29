"""
航路/空域编辑器 自动保存服务
运行: python save_server.py
端口: 8765
保存目录: routes/data/
"""

import json
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

SAVE_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(SAVE_DIR, exist_ok=True)

# 允许跨域的来源（本地开发用）
ALLOW_ORIGIN = '*'


class SaveHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        ts = datetime.now().strftime('%H:%M:%S')
        print(f'[{ts}] {fmt % args}')

    def send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', ALLOW_ORIGIN)
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        """处理预检请求"""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path

        # 读取请求体
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)

        try:
            data = json.loads(body)
        except Exception as e:
            self._respond(400, {'ok': False, 'error': f'JSON解析失败: {e}'})
            return

        if path == '/save/routes':
            self._save_file(data, 'routes_autosave.geojson', '航路')
        elif path == '/save/airspaces':
            self._save_file(data, 'airspaces_autosave.geojson', '空域')
        else:
            self._respond(404, {'ok': False, 'error': '未知路径'})

    def _save_file(self, data, filename, label):
        filepath = os.path.join(SAVE_DIR, filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            count = len(data.get('features', []))
            self.log_message(f'已保存{label} → {filename}  ({count} 条)')
            self._respond(200, {'ok': True, 'file': filepath, 'count': count})
        except Exception as e:
            self.log_message(f'保存{label}失败: {e}')
            self._respond(500, {'ok': False, 'error': str(e)})

    def _respond(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(body)


if __name__ == '__main__':
    port = 8765
    server = HTTPServer(('127.0.0.1', port), SaveHandler)
    print(f'=== 航路自动保存服务已启动 ===')
    print(f'监听: http://127.0.0.1:{port}')
    print(f'保存目录: {SAVE_DIR}')
    print(f'接口:')
    print(f'  POST /save/routes    → data/routes_autosave.geojson')
    print(f'  POST /save/airspaces → data/airspaces_autosave.geojson')
    print(f'按 Ctrl+C 停止')
    print()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n服务已停止')
