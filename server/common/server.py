from queue import Queue
import socket
import logging
import signal
from .communication import ProtocolMessage
from .utils import Bet, has_won, load_bets, store_bets
import threading

MSG_END = "END"
REQUEST_HANDLERS = {
    "LOAD_BATCHES": lambda server, agency: server._load_batches_request(agency),
    "ALL_BETS_SENT": lambda server, agency: server._client_done_submitting.put(agency),
    "RESULTS_REQUEST": lambda server, agency: server._handle_request_in_thread(Server._send_results_to, agency),
}

class Server:
    def __init__(self, port, listen_backlog, total_agencies):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        self._current_client_socket = None
        self.running = False
        
        self._total_agencies = total_agencies
        self._client_done_submitting = Queue()
        self._lottery_completed = [Queue()] * total_agencies
        self._wait_thread = threading.Thread(target=self._wait_for_all_agencies)
        self._wait_thread.daemon = True
        self._wait_thread.start()

    def _wait_for_all_agencies(self):
        """
        Wait for all agencies to finish submitting their bets.
        Once all agencies have finished submitting, notify
        that the lottery has been completed.
        """
        received = set()
        while len(received) < self._total_agencies:
            agency_num = self._client_done_submitting.get()
            if agency_num is None:
                # Server is stopping
                return
            received.add(agency_num)
        
        for q in self._lottery_completed:
            q.put(True)
        
        logging.info("action: sorteo | result: success")


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
        if self._current_client_socket is None:
            return
        
        try:
            msg = ProtocolMessage.new_from_sock(self._current_client_socket)
            if type(msg) is not str:
                raise ValueError("Invalid message type received for request")
            request, agency = msg.split(',')
            
            REQUEST_HANDLERS[request](self, agency)
            
        except Exception as e:
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
            self._current_client_socket = c
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
        
        self._client_done_submitting.put(None)
        for q in self._lottery_completed:
            q.put(False)

    def __close_client_socket(self):
        if self._current_client_socket is None:
            return
        self._current_client_socket.close()
        self._current_client_socket = None
        logging.info("action: client_socket_closed | result: success")
            
    def _load_batches_request(self, agency: str):
        """
        Handle LOAD_BATCHES request from client
        
        Function that handles the LOAD_BATCHES request from a client.
        It will keep receiving batches of bets until an END message is
        received. If any error occurs during the process, it will log
        the error and return.
        """
        total_bets = 0
        try:
            while True:
                msg = ProtocolMessage.new_from_sock(self._current_client_socket)
                if type(msg) is not list:
                    if msg == MSG_END:
                        return
                    else:
                        raise ValueError("Invalid message type received for bets batch")
                
                bets = [Bet.from_string(agency, bet_str) for bet_str in msg]
                total_bets += len(bets)
                store_bets(bets)
                logging.info(f"action: apuesta_recibida | result: success | cantidad: {len(bets)}")
            
        except Exception as e:
            logging.error(f"action: apuesta_recibida | result: fail | cantidad: {total_bets}")
            logging.error(f"{e}")
            return
        
    def _handle_request_in_thread(self, handler, agency):
        thread = threading.Thread(target=handler, args=(self, agency), daemon=True)
        thread.start()
        
    def _send_results_to(self, agency: str):
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
            client_socket = self._current_client_socket
            self._current_client_socket = None
            if client_socket is None:
                # Server is stopping
                return
            
            completed = self._lottery_completed[agency_num-1].get()
            if not completed:
                # Server is stopping
                return

            winning_bets = []
            for bet in load_bets():
                if bet.agency == agency_num and has_won(bet):
                    winning_bets.append(bet.document)

            if not winning_bets:
                ProtocolMessage.send_string_list_to_sock(client_socket, [])
            else:
                ProtocolMessage.send_string_list_to_sock(client_socket, winning_bets)
            
            logging.info(f"action: enviar_resultados | result: success | agencia: {agency}")
            
        except Exception as e:
            logging.error(f"action: enviar_resultados | result: fail | agencia: {agency} | error: {e}")

        finally:
            if client_socket:
                client_socket.close()