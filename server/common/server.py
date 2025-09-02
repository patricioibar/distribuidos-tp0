import socket
import logging
import signal
import threading
from .communication import ProtocolMessage
from .utils import Bet, has_won, load_bets, store_bets

MSG_END = "END"
MSG_LOTERY_IN_PROGRESS = "LOTERY_IN_PROGRESS"
REQUEST_HANDLERS = {
    "LOAD_BATCHES": lambda server, agency, sock: server._load_batches_request(agency, sock),
    "ALL_BETS_SENT": lambda server, agency, sock: server._agency_done_submitting(agency),
    "RESULTS_REQUEST": lambda server, agency, sock: server._send_results_to(agency, sock),
}

class Server:
    def __init__(self, port, listen_backlog, total_agencies):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        self.running = False
        
        self._total_agencies = total_agencies
        self._agencies_done_submitting = set()
        self._lottery_completed = False
        
        self._current_client_sockets = set()
        self._store_bets_lock = threading.Lock()
        self._done_writting_data_for_agency = {}


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

    def __handle_client_connection(self, sock: socket):
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        
        This function is intended to run in a separate thread
        for each client connection
        """
        
        try:
            while True:
                msg = ProtocolMessage.new_from_sock(sock)
                if type(msg) is not str:
                    raise ValueError("Invalid message type received for request")
                if msg == MSG_END:
                    return
                
                request, agency = msg.split(',')
                
                if REQUEST_HANDLERS.get(request) is None:
                    raise ValueError(f"Unknown request type: {request}")
                
                REQUEST_HANDLERS[request](self, agency, sock)
            
        except Exception as e:
            if not self.running:
                return
            logging.error(f"action: receive_message | result: fail | error: {e}")
        finally:
            self._current_client_sockets.remove(sock)
            sock.close()
                

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
            self._current_client_sockets.add(c)
            threading.Thread(target=self.__handle_client_connection, args=(c,)).start()
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
        self.__close_client_sockets()

    def __close_client_sockets(self):
        for sock in self._current_client_sockets:
            try:
                sock.close()
            except Exception as e:
                logging.error(f"action: client_socket_close | result: fail | error: {e}")
        self._current_client_sockets.clear()
        logging.info("action: client_sockets_closed | result: success")

    def _load_batches_request(self, agency: str, sock: socket):
        """
        Handle LOAD_BATCHES request from client
        
        Function that handles the LOAD_BATCHES request from a client.
        It will keep receiving batches of bets until an END message is
        received. If any error occurs during the process, it will log
        the error and return.
        """
        total_bets = 0
        self._done_writting_data_for_agency[agency] = threading.Event()
        try:
            while True:
                msg = ProtocolMessage.new_from_sock(sock)
                if type(msg) is not list:
                    if msg == MSG_END:
                        return
                    else:
                        raise ValueError("Invalid message type received for bets batch")
                
                bets = [Bet.from_string(agency, bet_str) for bet_str in msg]
                total_bets += len(bets)
                
                with self._store_bets_lock:
                    store_bets(bets)
                
                logging.info(f"action: apuesta_recibida | result: success | cantidad: {len(bets)}")
            
        except Exception as e:
            logging.error(f"action: apuesta_recibida | result: fail | cantidad: {total_bets}")
            logging.error(f"{e}")
        
        finally:
            self._done_writting_data_for_agency[agency].set()
            
    def _agency_done_submitting(self, agency: str):
        """
        Handle ALL_BETS_SENT from client
        
        Function that handles the ALL_BETS_SENT from a client.
        It will add the agency to the set of agencies that have
        finished submitting bets. If all agencies have finished,
        it will mark the lottery as completed.
        """
        if self._lottery_completed:
            return
        
        agency_num = int(agency)
        if agency_num < 1 or agency_num > self._total_agencies:
            logging.error(f"action: agency_done_submitting | result: fail | agencia: {agency}")
            return
        
        self._done_writting_data_for_agency[agency].wait()
        self._agencies_done_submitting.add(agency_num)
        logging.info(f"action: agency_done_submitting | result: success | agencia: {agency}")

        if len(self._agencies_done_submitting) == self._total_agencies:
            self._lottery_completed = True
            logging.info("action: sorteo | result: success")

    def _send_results_to(self, agency: str, sock: socket):
        """
        Handle RESULTS_REQUEST from client
        
        Function that handles the RESULTS_REQUEST from a client.
        It will wait until the lottery has been completed, and then
        send the result to the client. 
        
        The result is a StringList message with the DNI of the
        winning bets from that company.
        If there are no winning bets, an empty list is sent.
        """
        agency_num = int(agency)
        if agency_num < 1 or agency_num > self._total_agencies:
            logging.error(f"action: enviar_resultados | result: fail | agencia: {agency}")
            return
        
        try:
            if not self._lottery_completed:
                ProtocolMessage.send_string_to_sock(
                    sock,
                    MSG_LOTERY_IN_PROGRESS
                    )
                return

            winning_bets = []
            for bet in load_bets():
                if bet.agency == agency_num and has_won(bet):
                    winning_bets.append(bet.document)

            ProtocolMessage.send_string_list_to_sock(sock, winning_bets)
            logging.info(f"action: enviar_resultados | result: success | agencia: {agency}")
            
        except Exception as e:
            logging.error(f"action: enviar_resultados | result: fail | agencia: {agency} | error: {e}")