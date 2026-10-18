"""
T-Share v3 Binary Protocol Specification
Optimized for 1 Gbps direct Ethernet cable transfer (Windows <-> Linux).
Raw TCP socket streaming, zero TLS overhead, 4 MB chunking with in-flight SHA-256 integrity.
"""

import struct
import socket
import json
from typing import Tuple, Optional, Any

# Protocol Constants
MAGIC = b'TS'
PROTOCOL_VERSION = 3

DEFAULT_TCP_PORT = 52001
DEFAULT_UDP_PORT = 52000
BLOCK_SIZE = 4 * 1024 * 1024  # 4 MB blocks for maximum disk & network alignment

# Packet Header: Magic (2B) + MsgType (1B) + SessionID (4B uint32) + PayloadLen (4B uint32) = 11 Bytes
HEADER_FORMAT = '!2sBII'
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

# Block Payload Header: FileID (4B uint32) + BlockIndex (4B uint32) + BlockLen (4B uint32) + SHA256 (32B) = 44 Bytes
BLOCK_HEADER_FORMAT = '!III32s'
BLOCK_HEADER_SIZE = struct.calcsize(BLOCK_HEADER_FORMAT)

# Message Types (uint8)
MSG_HELLO           = 0x01  # Sender -> Receiver: {version, hostname, session_id}
MSG_HELLO_ACK       = 0x02  # Receiver -> Sender: {accepted: bool, name: str}
MSG_MANIFEST        = 0x03  # Sender -> Receiver: {session_id, files: [...], total_bytes, total_files}
MSG_ACCEPT          = 0x04  # Receiver -> Sender: {accepted: bool, reason: str}
MSG_REJECT          = 0x05  # Receiver -> Sender: {reason: str}
MSG_RESUME_QUERY    = 0x06  # Sender -> Receiver: {file_id}
MSG_RESUME_BITMAP   = 0x07  # Receiver -> Sender: [4B file_id][4B total_blocks][bitmask bytes]
MSG_BLOCK           = 0x10  # Sender -> Receiver: BlockHeader (44B) + Data (<= 4MB)
MSG_BLOCK_ACK       = 0x11  # Receiver -> Sender: {file_id, block_index}
MSG_BLOCK_NACK      = 0x12  # Receiver -> Sender: {file_id, block_index, reason}
MSG_FILE_DONE       = 0x20  # Sender -> Receiver: {file_id, checksum}
MSG_SESSION_DONE    = 0x21  # Sender -> Receiver: {session_id}
MSG_CANCEL          = 0x30  # Bidirectional: {reason: str}
MSG_ERROR           = 0xFF  # Bidirectional: {error: str}


class ProtocolError(Exception):
    """Raised when a protocol framing or integrity error occurs."""
    pass


def tune_socket(sock: socket.socket) -> None:
    """Apply high-throughput low-latency socket optimizations."""
    try:
        # Disable Nagle's algorithm for immediate dispatch
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except Exception:
        pass
    try:
        # 4 MB socket buffers for 1 Gbps line-rate
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
    except Exception:
        pass


def send_block(
    sock: socket.socket,
    session_id: int,
    file_id: int,
    block_idx: int,
    block_data: bytes,
    block_hash: bytes
) -> None:
    """
    Sends a high-speed streaming block with zero intermediate payload concatenation.
    Combines 11-byte Packet Header and 44-byte Block Header into a single 55-byte header,
    then writes block_data directly from memory to socket.
    """
    data_len = len(block_data)
    hdr = struct.pack(
        '!2sBIIIII32s',
        MAGIC, MSG_BLOCK, session_id, BLOCK_HEADER_SIZE + data_len,
        file_id, block_idx, data_len, block_hash
    )
    sock.sendall(hdr)
    sock.sendall(block_data)


def recv_exact(sock: socket.socket, num_bytes: int) -> bytes:
    """Read exactly num_bytes from socket, raising ConnectionError if disconnected."""
    buf = bytearray(num_bytes)
    view = memoryview(buf)
    pos = 0
    while pos < num_bytes:
        n = sock.recv_into(view[pos:], num_bytes - pos)
        if n == 0:
            raise ConnectionError(f"Connection closed prematurely (received {pos}/{num_bytes} bytes)")
        pos += n
    return bytes(buf)


def send_packet(sock: socket.socket, msg_type: int, session_id: int, payload: bytes = b'') -> None:
    """Encapsulates and sends a binary framed packet."""
    header = struct.pack(HEADER_FORMAT, MAGIC, msg_type, session_id, len(payload))
    sock.sendall(header + payload)


def send_json(sock: socket.socket, msg_type: int, session_id: int, data: Any) -> None:
    """Serializes a Python object to JSON and sends as packet payload."""
    payload = json.dumps(data, ensure_ascii=False).encode('utf-8')
    send_packet(sock, msg_type, session_id, payload)


def recv_packet(sock: socket.socket) -> Tuple[int, int, bytes]:
    """
    Receives and decodes the next packet from socket.
    Returns: (msg_type, session_id, payload_bytes)
    """
    header_bytes = recv_exact(sock, HEADER_SIZE)
    magic, msg_type, session_id, payload_len = struct.unpack(HEADER_FORMAT, header_bytes)
    
    if magic != MAGIC:
        raise ProtocolError(f"Invalid packet magic: {magic!r}, expected {MAGIC!r}")
        
    payload = recv_exact(sock, payload_len) if payload_len > 0 else b''
    return msg_type, session_id, payload


def recv_json(sock: socket.socket) -> Tuple[int, int, Any]:
    """Receives a packet and parses its payload as JSON."""
    msg_type, session_id, payload = recv_packet(sock)
    if not payload:
        return msg_type, session_id, None
    try:
        data = json.loads(payload.decode('utf-8'))
        return msg_type, session_id, data
    except Exception as e:
        raise ProtocolError(f"Failed to decode JSON payload: {e}")
