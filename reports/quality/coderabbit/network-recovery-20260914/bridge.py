"""Task-local CONNECT relay: WSL loopback -> Windows stdio -> CodeRabbit TCP.

No TLS termination, no payload logging, no system network configuration changes.
"""
import os
import socket
import socketserver
import subprocess
import sys
import threading

ALLOWED = {
    'app.coderabbit.ai',
    'ide.coderabbit.ai',
    'cli.coderabbit.ai',
    'www.coderabbit.ai',
    'coderabbit.ai',
    'us.i.posthog.com',
}


def windows_tcp(host):
    if host not in ALLOWED:
        raise SystemExit(2)
    import msvcrt
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    with socket.create_connection((host, 443), timeout=15) as remote:
        remote.settimeout(None)
        sys.stdout.buffer.write(b'READY\n')
        sys.stdout.buffer.flush()
        def send():
            try:
                while data := os.read(sys.stdin.fileno(), 65536):
                    remote.sendall(data)
            except OSError:
                pass
            finally:
                try:
                    remote.shutdown(socket.SHUT_WR)
                except OSError:
                    pass
        threading.Thread(target=send, daemon=True).start()
        try:
            while data := remote.recv(65536):
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()
        except (OSError, BrokenPipeError):
            pass


class Proxy(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = False


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        self.connection.settimeout(20)
        first = self.rfile.readline(4096).decode('ascii', errors='replace').split()
        print("Proxy method:", first[0] if first else "empty", flush=True)
        if len(first) != 3 or first[0] != 'CONNECT':
            self.wfile.write(b'HTTP/1.1 405 Method Not Allowed\r\n\r\n')
            return
        host, _, port = first[1].rpartition(':')
        print("Proxy host:", host, "port:", port, flush=True)
        if host not in ALLOWED or port != '443':
            self.wfile.write(b'HTTP/1.1 403 Forbidden\r\n\r\n')
            return
        for _ in range(100):
            if self.rfile.readline(8192) in (b'\r\n', b'\n', b''):
                break
        helper = subprocess.Popen([
            '/mnt/e/github/BioactivityDataAcquisition/.venv-win/Scripts/python.exe',
            '-B', '-u',
            r'E:\github\BioactivityDataAcquisition\reports\quality\coderabbit\network-recovery-20260914\bridge.py',
            '--tcp', host,
        ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            if helper.stdout.readline() != b'READY\n':
                self.wfile.write(b'HTTP/1.1 502 Bad Gateway\r\n\r\n')
                return
            self.wfile.write(b'HTTP/1.1 200 Connection Established\r\n\r\n')
            self.wfile.flush()
            self.connection.settimeout(None)
            def upload():
                try:
                    while data := self.rfile.read1(65536):
                        helper.stdin.write(data)
                        helper.stdin.flush()
                except (OSError, ValueError):
                    pass
                finally:
                    try:
                        helper.stdin.close()
                    except OSError:
                        pass
            threading.Thread(target=upload, daemon=True).start()
            while data := helper.stdout.read1(65536):
                self.wfile.write(data)
                self.wfile.flush()
        except (OSError, ValueError):
            pass
        finally:
            if helper.poll() is None:
                helper.terminate()
            helper.wait(timeout=10)


def main():
    if sys.argv[1] == '--tcp':
        windows_tcp(sys.argv[2])
        return 0
    with Proxy(('127.0.0.1', 0), Handler) as server:
        url = f'http://127.0.0.1:{server.server_address[1]}'
        env = dict(os.environ, HTTP_PROXY=url, HTTPS_PROXY=url, http_proxy=url, https_proxy=url,
                   NO_PROXY='localhost,127.0.0.1', no_proxy='localhost,127.0.0.1')
        print('Temporary CodeRabbit-only proxy:', url, flush=True)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            return subprocess.call(sys.argv[1:], env=env)
        finally:
            server.shutdown()


if __name__ == '__main__':
    raise SystemExit(main())
