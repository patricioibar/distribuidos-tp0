import socket
import logging
import signal

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
            # TODO: Modify the receive to avoid short-reads
            msg = self._client_socket.recv(1024).rstrip().decode('utf-8')
            addr = self._client_socket.getpeername()
            logging.info(f'action: receive_message | result: success | ip: {addr[0]} | msg: {msg}')
            # TODO: Modify the send to avoid short-writes
            self._client_socket.send("{}\n".format(msg).encode('utf-8'))
        except OSError as e:
            if not self.running:
                return
            logging.error(f"action: receive_message | result: fail | error: {e}")
        finally:
            self.__close_client_socket()

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
        self.__close_client_socket()

    def __close_client_socket(self):
        if self._client_socket is None:
            return
        self._client_socket.close()
        self._client_socket = None
        logging.info("action: client_socket_closed | result: success")