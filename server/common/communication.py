from socket import MSG_WAITALL, socket

def string_message(data: bytes) -> str:
    return data.decode('utf-8')

TYPE_TO_CONSTRUCTOR = {
    b'\x01': string_message,
}
HEADER_SIZE = 5 # 1 byte for type + 4 bytes for length

def _recv_exact(sock: socket, nbytes: int) -> bytes:
    data = bytearray()
    
    while len(data) < nbytes:
        packet = sock.recv(nbytes - len(data), MSG_WAITALL)
        if not packet:
            raise EOFError("Socket closed before receiving expected bytes")
        data += packet
    return data

class ProtocolMessage:
    @staticmethod
    def new_from_sock(sock: socket):
        header = _recv_exact(sock, HEADER_SIZE)

        type = header[0:1]
        length = int.from_bytes(header[1:5], byteorder='big')

        body = _recv_exact(sock, length)

        constructor = TYPE_TO_CONSTRUCTOR.get(type)
        if not constructor:
            raise ValueError(f"Unknown message type: {type}")
        return constructor(body)
        
    @staticmethod
    def send_string_to_sock(sock: socket, string: str):
        body = string.encode('utf-8')
        type = b'\x01'
        length = len(body).to_bytes(4, byteorder='big')
        message = type + length + body
        sock.sendall(message)