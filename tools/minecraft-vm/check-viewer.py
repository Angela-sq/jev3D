#!/usr/bin/env python3
"""Guest-side RFB authentication test through the same WebSocket as noVNC.

Reads the local VNC password without displaying it. Requires websocket-client
and pycryptodome in the guest test venv. Does not issue any input events.
"""
from pathlib import Path
import struct
import websocket
from Crypto.Cipher import DES

ws = websocket.create_connection('ws://127.0.0.1:6080/websockify', timeout=10,
                                 subprotocols=['binary'])
pending = bytearray()
def read(n):
    while len(pending) < n:
        chunk = ws.recv()
        if not isinstance(chunk, bytes) or not chunk:
            raise RuntimeError('Unexpected RFB stream termination')
        pending.extend(chunk)
    result = bytes(pending[:n]); del pending[:n]
    return result
def send(data):
    ws.send_binary(data)

assert read(12).startswith(b'RFB 003.'), 'Unexpected protocol'
send(b'RFB 003.008\n')
types = read(read(1)[0])
assert 2 in types, 'VNC password authentication unavailable'
send(b'\x02')
password = (Path.home()/'.vnc/password.txt').read_bytes().strip()[:8].ljust(8,b'\0')
key = bytes(int(f'{v:08b}'[::-1], 2) for v in password)
send(DES.new(key, DES.MODE_ECB).encrypt(read(16)))
assert read(4) == b'\0\0\0\0', 'VNC authentication failed'
send(b'\x01')  # shared read-only test connection
header = read(24)
width, height = struct.unpack('>HH', header[:4])
name_length = struct.unpack('>I', header[20:24])[0]
read(name_length)
assert (width,height) == (1280,720), (width,height)
ws.close()
print('PASS: WebSocket -> password-authenticated VNC -> 1280x720 desktop')
