"""RTSP service checks kept separate from TCP discovery."""

import socket


def check(ip, port=554, timeout=1.0):
    try:
        with socket.create_connection((ip, port), timeout=timeout) as sock:
            sock.sendall(f"OPTIONS rtsp://{ip}:{port}/ RTSP/1.0\\r\\nCSeq: 1\\r\\n\\r\\n".encode())
            return sock.recv(256).startswith(b"RTSP/")
    except OSError:
        return False

