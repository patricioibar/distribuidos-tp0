from socket import MSG_WAITALL, socket

def string_message(data: bytes) -> str:
    return data.decode('utf-8')

TYPE_TO_CONSTRUCTOR = {
    b'\x01': string_message,
}
HEADER_SIZE = 5 # 1 byte for type + 4 bytes for length

class ProtocolMessage:
    @staticmethod
    def new_from_sock(sock: socket):
        header = sock.recv(HEADER_SIZE)
        if len(header) < HEADER_SIZE:
            raise ConnectionError("Connection closed by the other side")
        
        type = header[0:1]
        length = int.from_bytes(header[1:5], byteorder='big')
        
        body = bytearray()
        while len(body) < length:
            packet = sock.recv(length - len(body))
            if not packet:
                raise EOFError("Socket closed before receiving full message")
            body.extend(packet)
            
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