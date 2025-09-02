import socket
import logging
import signal
from .communication import ProtocolMessage
from .utils import Bet, store_bets

MSG_END = "END"
REQUEST_HANDLERS = {
    "LOAD_BATCHES": lambda server, agency: server._load_batches_request(agency),
}

class Server:
    def __init__(self, port, listen_backlog):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        self._client_socket = None
        self.running = False

    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """

        self.running = True
        signal.signal(signal.SIGTERM, lambda _signum, _frame: self.stop())

        while self.running:
            self.__accept_new_connection()
            self.__handle_client_connection()

    def __handle_client_connection(self):
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        if self._client_socket is None:
            return
        
        try:
            msg = ProtocolMessage.new_from_sock(self._client_socket)
            if type(msg) is not str:
                raise ValueError("Invalid message type received for request")
            request, agency = msg.split(',')
            
            REQUEST_HANDLERS[request](self, agency)
            
        except Exception as e:
            if not self.running:
                return
            logging.error(f"action: receive_message | result: fail | error: {e}")
        finally:
            self._client_socket.close()

    def __accept_new_connection(self):
        """
        Accept new connections

        Function blocks until a connection to a client is made.
        Then connection created is printed and returned
        """

        # Connection arrived
        logging.info('action: accept_connections | result: in_progress')
        try: 
            c, addr = self._server_socket.accept()
            logging.info(f'action: accept_connections | result: success | ip: {addr[0]}')
            self._client_socket = c
        except OSError as e:
            if self.running:
                logging.error(f"action: accept_connections | result: fail | error: {e}")

    def stop(self):
        """
        Stop the server

        Function that stops the server and closes the server socket
        """
        self.running = False
        self._server_socket.close()
        logging.info("action: server_socket_closed | result: success")
        if self._client_socket is not None:
            self._client_socket.close()
            logging.info("action: client_socket_closed | result: success")
            
    def _load_batches_request(self, agency: str):
        total_bets = 0
        try:
            while True:
                msg = ProtocolMessage.new_from_sock(self._client_socket)
                if type(msg) is not list:
                    if msg == MSG_END:
                        break
                    else:
                        raise ValueError("Invalid message type received for bets batch")
                
                bets = [Bet.from_string(agency, bet_str) for bet_str in msg.value]
                total_bets += len(bets)
                store_bets(bets)
            
        except Exception:
            logging.error(f"action: apuesta_recibida | result: fail | cantidad: {total_bets}")
            return
        finally:
            logging.info(f"action: apuesta_recibida | result: success | cantidad: {total_bets}")