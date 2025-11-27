#!/usr/bin/env python3
"""
OpenWebUI-ZeroErr 代理服务器
负责将前端请求代理到相应的后端服务
"""

import http.server
import socketserver
import urllib.request
import urllib.parse
import urllib.error
import json
import signal
import sys
import time
import os
import ssl

# 配置
FRONTEND_PORT = 5173  # SvelteKit前端服务端口
BACKEND_PORT = 6000   # Python后端服务端口（本地）
PORT = 5557          # 代理服务器端口

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.handle_request()
    def do_POST(self):
        self.handle_request()
    def do_PUT(self):
        self.handle_request()
    def do_DELETE(self):
        self.handle_request()
    def do_HEAD(self):
        self.handle_request()
    def do_OPTIONS(self):
        self.handle_request()
    def do_PATCH(self):
        self.handle_request()

    def handle_request(self):
        """处理HTTP请求"""
        path = self.path
        method = self.command
        
        # 根据路径决定代理目标
        if path.startswith('/api/v1/'):
            # 知识库等API请求 - 转发到本地Python后端
            target_url = f"http://127.0.0.1:{BACKEND_PORT}{path}"
            service_name = f"Python后端服务({BACKEND_PORT}端口)"
        elif path.startswith('/api/') or path.startswith('/ollama/') or path.startswith('/openai/'):
            # 其他API请求 - 转发到本地Python后端
            target_url = f"http://127.0.0.1:{BACKEND_PORT}{path}"
            service_name = f"Python后端服务({BACKEND_PORT}端口)"
        elif path.startswith('/ws/'):
            # WebSocket请求 - 转发到本地Python后端
            target_url = f"http://127.0.0.1:{BACKEND_PORT}{path}"
            service_name = f"Python后端WebSocket({BACKEND_PORT}端口)"
        else:
            # 前端静态资源请求 - 转发到SvelteKit
            target_url = f"http://127.0.0.1:{FRONTEND_PORT}{path}"
            service_name = f"SvelteKit前端服务({FRONTEND_PORT}端口)"
        
        try:
            # 创建请求
            req = urllib.request.Request(target_url, method=method)
            
            # 复制请求头
            for header, value in self.headers.items():
                if header.lower() not in ['host', 'connection']:
                    req.add_header(header, value)
            
            # 复制请求体（如果有）
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                req.data = self.rfile.read(content_length)
            
            # 发送请求
            with urllib.request.urlopen(req, timeout=30) as response:
                # 设置响应状态
                self.send_response(response.status)
                
                # 复制响应头
                for header, value in response.headers.items():
                    if header.lower() not in ['connection', 'transfer-encoding']:
                        self.send_header(header, value)

                # 添加CORS头
                self._add_cors_headers()
                self.end_headers()
                
                # 复制响应体（分块读取，避免大文件问题）
                try:
                    chunk_size = 8192  # 8KB chunks
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        self.wfile.flush()  # 确保数据及时发送
                except (BrokenPipeError, ConnectionResetError):
                    # 客户端断开连接，这是正常的，不需要报错
                    pass
                
        except urllib.error.HTTPError as e:
            # HTTP错误处理
            self._handle_error(e.status, f"{service_name} HTTP错误: {e.reason}", service_name)
        except urllib.error.URLError as e:
            # 网络错误处理
            self._handle_error(503, f"{service_name} 连接失败: {str(e)}", service_name)
        except (BrokenPipeError, ConnectionResetError):
            # 客户端断开连接，这是正常的，不需要报错
            pass
        except Exception as e:
            # 其他错误处理
            self._handle_error(500, f"{service_name} 内部错误: {str(e)}", service_name)

    def _add_cors_headers(self):
        """添加CORS头"""
        origin = self.headers.get('Origin', '*')
        self.send_header('Access-Control-Allow-Origin', origin if origin else '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS, PATCH')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, Accept, Origin')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.send_header('Vary', 'Origin')

    def _handle_error(self, status_code, error_msg, service_name):
        """处理错误响应"""
        try:
            print(f"代理错误 [{status_code}]: {error_msg}")
            self.send_response(status_code)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self._add_cors_headers()
            self.end_headers()
            
            error_response = {
                "error": error_msg,
                "service": service_name,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            self.wfile.write(json.dumps(error_response, ensure_ascii=False).encode('utf-8'))
        except (BrokenPipeError, ConnectionResetError):
            # 客户端断开连接，无法发送错误响应
            pass

    def log_message(self, format, *args):
        """自定义日志格式"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {self.address_string()} - {format % args}")

def check_service(host, port, service_name):
    """检查服务是否可用"""
    try:
        url = f"http://{host}:{port}"
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'ProxyServer/1.0')
        
        with urllib.request.urlopen(req, timeout=5) as response:
            return True
            
    except Exception as e:
        print(f"警告: {service_name} 不可用 - {str(e)}")
        return False

def signal_handler(sig, frame):
    """信号处理器"""
    print('\n正在停止代理服务器...')
    sys.exit(0)

def main():
    """主函数"""
    # 设置信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 检查服务状态
    print("正在检查服务状态...")
    frontend_ok = check_service("127.0.0.1", FRONTEND_PORT, f"SvelteKit前端服务({FRONTEND_PORT}端口)")
    backend_ok = check_service("127.0.0.1", BACKEND_PORT, f"Python后端服务({BACKEND_PORT}端口)")
    
    # 显示服务状态
    print(f"\n服务状态:")
    print(f"  SvelteKit前端: http://127.0.0.1:{FRONTEND_PORT} {'✓' if frontend_ok else '✗'}")
    print(f"  Python后端:   http://127.0.0.1:{BACKEND_PORT} {'✓' if backend_ok else '✗'}")
    
    if not frontend_ok and not backend_ok:
        print("错误: 没有可用的服务，无法启动代理服务器")
        sys.exit(1)
    
    # 允许端口重用
    socketserver.TCPServer.allow_reuse_address = True
    
    try:
        with socketserver.TCPServer(("", PORT), ProxyHandler) as httpd:
            print(f"\n🚀 代理服务器启动成功!")
            print(f"   代理地址: http://127.0.0.1:{PORT}")
            print(f"   按 Ctrl+C 停止服务器")
            print("=" * 50)
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print('\n正在停止代理服务器...')
    except Exception as e:
        print(f"服务器错误: {e}")
    finally:
        print("代理服务器已停止")

if __name__ == "__main__":
    main()