from socket import MSG_WAITALL, socket

def string_message(data: bytes) -> str:
    return data.decode('utf-8')

def string_list_message(data: bytes) -> list[str]:
    result = []
    offset = 0
    while offset < len(data):
        if offset + 4 > len(data):
            raise ValueError("Invalid data: incomplete string size")
        size = int.from_bytes(data[offset:offset+4], byteorder='big')
        offset += 4
        if offset + size > len(data):
            raise ValueError("Invalid data: incomplete string content")
        result.append(data[offset:offset+size].decode('utf-8'))
        offset += size
    return result

TYPE_TO_CONSTRUCTOR = {
    b'\x01': string_message,
    b'\x02': string_list_message,
}
HEADER_SIZE = 5 # 1 byte for type + 4 bytes for length
TYPE_STRING = b'\x01'
TYPE_STRING_LIST = b'\x02'

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
        length = len(body).to_bytes(4, byteorder='big')
        message = TYPE_STRING + length + body
        sock.sendall(message)
        
    @staticmethod
    def send_string_list_to_sock(sock: socket, strings: list[str]):
        body = bytearray()
        for s in strings:
            bytes = s.encode('utf-8')
            size = len(bytes).to_bytes(4, byteorder='big')
            body.extend(size)
            body.extend(bytes)
        length = len(body).to_bytes(4, byteorder='big')
        message = TYPE_STRING_LIST + length + body
        sock.sendall(message)