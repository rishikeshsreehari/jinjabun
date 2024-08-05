import os
import sys
import time
import subprocess
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from http.server import SimpleHTTPRequestHandler
import socketserver
from build import main as build_site
import websocket_server
import logging
import socket

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

ORIGINAL_DIR = os.path.abspath(os.getcwd())
PUBLIC_DIR = os.path.join(ORIGINAL_DIR, 'public')

print("Current working directory:", ORIGINAL_DIR)

# WebSocket server for live reload
WS_PORT = 9000
ws_server = websocket_server.WebsocketServer(host='127.0.0.1', port=WS_PORT)

def new_client(client, server):
    logging.info(f"New client connected and was given id {client['id']}")

def client_left(client, server):
    logging.info(f"Client {client['id']} disconnected")

ws_server.set_fn_new_client(new_client)
ws_server.set_fn_client_left(client_left)

class BuildHandler(FileSystemEventHandler):
    def __init__(self):
        self.last_triggered = 0
        self.cooldown = 1  # 1 second cooldown

    def on_any_event(self, event):
        if event.is_directory:
            return

        current_time = time.time()
        if current_time - self.last_triggered < self.cooldown:
            return

        self.last_triggered = current_time

        if event.src_path.endswith(('.html', '.css', '.js', '.md', '.yml', '.yaml')):
            logging.info(f"Detected change in {event.src_path}. Rebuilding...")
            os.chdir(ORIGINAL_DIR)
            build_site()
            inject_live_reload_script()
            ws_server.send_message_to_all("reload")
            logging.info("Build complete. Page reload triggered.")

def watch_files(stop_event):
    event_handler = BuildHandler()
    observer = Observer()
    directories_to_watch = ['src', 'data', 'assets']
    for directory in directories_to_watch:
        full_path = os.path.join(ORIGINAL_DIR, directory)
        if os.path.exists(full_path):
            observer.schedule(event_handler, full_path, recursive=True)
            logging.info(f"Watching directory: {full_path}")
    observer.schedule(event_handler, ORIGINAL_DIR, recursive=False)
    observer.start()
    try:
        while not stop_event.is_set():
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()

class PublicDirectoryHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def do_GET(self):
        path = self.path.rstrip('/')
        file_path = os.path.join(PUBLIC_DIR, path[1:])
        if os.path.isfile(file_path):
            return super().do_GET()
        html_path = os.path.join(PUBLIC_DIR, path[1:] + '.html')
        if os.path.isfile(html_path):
            self.path = path + '.html'
            return super().do_GET()
        index_path = os.path.join(PUBLIC_DIR, 'index.html')
        if os.path.isfile(index_path):
            self.path = '/index.html'
            return super().do_GET()
        self.send_error(404, "File not found")

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

def find_available_port(start_port, max_port=65535):
    for port in range(start_port, max_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('', port))
                return port
            except OSError:
                continue
    raise OSError("No available ports")

def serve(stop_event):
    os.chdir(PUBLIC_DIR)
    handler = PublicDirectoryHandler
    port = find_available_port(8000)
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"Serving at \033[94mhttp://localhost:{port}\033[0m from {PUBLIC_DIR}")
        httpd.timeout = 1
        while not stop_event.is_set():
            httpd.handle_request()

def inject_live_reload_script():
    script = f"""
    <script>
        (function() {{
            var socket = new WebSocket("ws://localhost:{WS_PORT}");
            socket.onmessage = function(event) {{
                if (event.data === "reload") {{
                    console.log("Reloading page...");
                    location.reload();
                }}
            }};
            socket.onclose = function(event) {{
                console.log("WebSocket closed. Reconnecting...");
                setTimeout(function() {{ window.location.reload(); }}, 2000);
            }};
            socket.onerror = function(error) {{
                console.log("WebSocket error: " + error);
            }};
        }})();
    </script>
    """
    for root, dirs, files in os.walk(PUBLIC_DIR):
        for file in files:
            if file.endswith('.html'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r+', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if '</body>' in content and script not in content:
                            new_content = content.replace('</body>', f'{script}</body>')
                            f.seek(0)
                            f.write(new_content)
                            f.truncate()
                            logging.info(f"Injected live reload script into {file_path}")
                except UnicodeDecodeError as e:
                    logging.error(f"Error decoding file {file_path}: {e}")
                except Exception as e:
                    logging.error(f"Error processing file {file_path}: {e}")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'serve':
        os.chdir(ORIGINAL_DIR)
        build_site()
        inject_live_reload_script()
        
        stop_event = threading.Event()
        
        server_thread = threading.Thread(target=serve, args=(stop_event,))
        server_thread.daemon = True
        server_thread.start()
        
        ws_thread = threading.Thread(target=ws_server.run_forever)
        ws_thread.daemon = True
        ws_thread.start()
        
        watch_thread = threading.Thread(target=watch_files, args=(stop_event,))
        watch_thread.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("Stopping server...")
            stop_event.set()
            watch_thread.join()
            ws_server.shutdown()
            logging.info("Server stopped.")
    elif len(sys.argv) > 1 and sys.argv[1] == 'watch':
        os.chdir(ORIGINAL_DIR)
        build_site()
        stop_event = threading.Event()
        watch_files(stop_event)
    else:
        print("Usage: python dev.py [serve|watch]")
        sys.exit(1)

if __name__ == "__main__":
    main()
    