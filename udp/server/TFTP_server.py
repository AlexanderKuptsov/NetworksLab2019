import os
import socket
import time
from _thread import *
from typing import Union
from pathlib import Path
from udp.TFTP_protocol import *


class ClientHandler:
    def __init__(self, client_sock, server):
        self.client_sock = client_sock
        self.server = server
        self.server_sock = server.sock
        self.server_dir = server.root_dir
        self.client_info = f'{client_sock[0]}:{client_sock[1]}'
        self.block_number = 1

        self.file_put = None
        self.file_get = None
        self.data_size = 0
        self.current_packet = None
        self.end_flag = False

        self.is_stopped = False
        self.retries = -1

    """ ========== REQUEST HANDLING ========== """

    def rrq_handle(self, data):
        """ Read request """
        # ---------- packet formatting ----=-----
        filename_part, mode_part = unpack_request(data)
        print(f'[{self.client_info}] -- RRQ: file({filename_part}) mode({mode_part})')
        # ---------------------------------------

        file_path = os.path.join(self.server_dir, filename_part)  # TODO -- check
        if os.path.isfile(file_path):
            try:
                self.file_put = open(file_path, 'rb')  # TODO -- mode
            except FileNotFoundError:
                self.create_error(TFTP.ERROR_CODES.ACCESS_VIOLATION)
            data_chunk = self.file_put.read(CHUNK_SIZE)
            self.data_size = len(data_chunk)

            self.current_packet = build_data_packet(self.block_number, data_chunk)
            self.server_sock.sendto(self.current_packet, self.client_sock)
            if len(data_chunk) < CHUNK_SIZE:
                # The last packet will have between 0 and 511 data bytes.
                self.end_flag = True
            start_new_thread(self.th_sending_handler, ())
        else:
            self.create_error(TFTP.ERROR_CODES.FILE_NOT_FOUND)

    def wrq_handle(self, data):
        """ Write request """
        # ---------- packet formatting ----------
        filename_part, mode_part = unpack_request(data)
        print(f'[{self.client_info}] -- WRQ: file({filename_part}) mode({mode_part})')
        # ---------------------------------------

        file_path = os.path.join(self.server_dir, filename_part)
        if not os.path.isfile(file_path):
            try:
                self.file_get = open(file_path, 'wb')  # TODO -- mode
            except FileNotFoundError:
                self.create_error(TFTP.ERROR_CODES.ACCESS_VIOLATION)
            self.data_size = 0

            self.current_packet = build_ack_packet(self.data_size)
            self.server_sock.sendto(self.current_packet, self.client_sock)
            start_new_thread(self.th_sending_handler, ())
        else:
            self.create_error(TFTP.ERROR_CODES.FILE_ALREADY_EXISTS)

    def data_handle(self, data):
        """ DATA """
        # ---------- packet formatting ----------
        current_block_number = struct.unpack('!H', data[2:4])[0]
        received_data = data[4:]
        print(f'[{self.client_info}] -- DATA packet ({current_block_number} block)')
        # ---------------------------------------
        self.data_size += len(received_data)

        if current_block_number == self.block_number:
            try:
                self.file_get.write(received_data)
            except FileNotFoundError:
                self.create_error(TFTP.ERROR_CODES.ACCESS_VIOLATION)
            self.increment_block_number()

            self.current_packet = build_ack_packet(current_block_number)
            self.server_sock.sendto(self.current_packet, self.client_sock)

            if len(received_data) < CHUNK_SIZE:
                self.transfer_end()
            self.th_reset()
        else:
            print(f'[{self.client_info}] -- Wrong block. Resending {current_block_number} block.')

    def ack_handle(self, data):
        """ Acknowledgment """
        # ---------- packet formatting ----------
        current_block_number = struct.unpack('!H', data[2:4])[0]
        print(f'[{self.client_info}] -- ACK: block number({current_block_number})')
        # ---------------------------------------

        if self.end_flag:
            self.transfer_end()
        else:
            data_chunk = b''
            if current_block_number == self.block_number:
                try:
                    data_chunk = self.file_put.read(CHUNK_SIZE)
                except FileNotFoundError:
                    self.create_error(TFTP.ERROR_CODES.ACCESS_VIOLATION)

                data_chunk_size = len(data_chunk)
                self.data_size += data_chunk_size
                self.increment_block_number()

                self.current_packet = build_data_packet(self.block_number, data_chunk)
                self.server_sock.sendto(self.current_packet, self.client_sock)

                if data_chunk_size < CHUNK_SIZE:
                    self.end_flag = True
                self.th_reset()
            else:
                print(f'[{self.client_info}] -- Wrong block. Resending {current_block_number} block.')

    def error_handle(self, data):
        """ Error """
        # ---------- packet formatting ----------
        err_code = struct.unpack('!H', data[2:4])[0]
        err_msg = data[4:-1]
        print(f'[{self.client_info}] -- ERROR: code({err_code}) msg({err_msg})')
        # ---------------------------------------
        if err_code != TFTP.ERROR_CODES.UNKNOWN_TRANSFER_ID:
            self.close()
            os.remove(self.file_get.name)

    def unexpected_handle(self, data):
        """ unexpected opcode """
        self.create_error(TFTP.ERROR_CODES.ILLEGAL_OPERATION)

    def request_handle(self, data):
        self.th_reset()
        opcode = data[0:2]
        opcode_handlers = {TFTP.OPCODES.RRQ: self.rrq_handle,
                           TFTP.OPCODES.WRQ: self.wrq_handle,
                           TFTP.OPCODES.DATA: self.data_handle,
                           TFTP.OPCODES.ACK: self.ack_handle,
                           TFTP.OPCODES.ERROR: self.error_handle}
        opcode_handlers.get(opcode, self.unexpected_handle)(data)

    """ HELPERS """

    def resend(self):
        self.server_sock.sendto(self.current_packet, self.client_sock)

    def increment_block_number(self):
        self.block_number += 1
        if self.block_number == MAX_BLOCK_NUMBER:
            self.block_number = 0

    def create_error(self, error_code):
        error_package = build_error_packet(error_code)
        self.server_sock.sendto(error_package, self.client_sock)
        print(f'[{self.client_info}] -- {TFTP.ERROR_MSG[error_code]}')
        self.close()

    def transfer_end(self):
        print(f'[{self.client_info}] -- File transferring has finished ({self.data_size} bytes).')
        self.close()

    def close(self):
        self.th_stop()
        del self.server.clients[self.client_sock]

    def __del__(self):
        print(f'[{self.client_info}] -- Client handler deleted.')
        try:
            self.file_put.close()
        except AttributeError:
            pass
        try:
            self.file_get.close()
        except AttributeError:
            pass

    """ ========== THREADING ========== """

    def th_sending_handler(self):
        self.th_reset()
        while True:
            if self.is_stopped:
                break
            if self.retries < MAX_RETRIES:
                self.resend()
                print(f'[{self.client_info}] -- Resending {self.block_number} block.')
            elif self.retries >= MAX_RETRIES:
                print(f'[{self.client_info}] -- Session timeout.')
                self.close()
                break

            self.retries += 1
            time.sleep(REPEAT_TIMEOUT)

    def th_reset(self):
        self.retries = -1

    def th_stop(self):
        self.is_stopped = True


# noinspection PyPep8Naming
class TFTP_Server:
    def __init__(self,
                 host: str = DEFAULT_HOSTNAME,
                 port: int = DEFAULT_PORT,
                 root_dir: Union[str, Path] = DEFAULT_ROOT_DIR,
                 mode: str = DEFAULT_MODE):  # TODO
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.host = host
        self.addr = (host, port)
        self.root_dir = Path(root_dir)
        self.mode = mode
        self.clients = {}

        self.sock.bind(self.addr)

    def launch(self):
        server_info = f'{self.addr[0]}:{self.addr[1]}'
        print(f'[SERVER] ({server_info}) launched.')
        while True:
            data, client_sock = self.sock.recvfrom(BUF_SIZE)
            if client_sock not in self.clients:
                # new client
                self.clients[client_sock] = ClientHandler(client_sock, self)
                client_info = f'{client_sock[0]}:{client_sock[1]}'
                print(f'[SERVER] new client ({client_info}).')
            # handling client's request
            self.clients[client_sock].request_handle(data)

    def close_clients_handlers(self):
        print('[SERVER] Closing clients handlers..')
        self.clients.clear()

    def close(self):
        self.sock.close()
        self.close_clients_handlers()

    def __exit__(self, exc_type, exc_val, exc_tb):
        print('[SERVER] Stopping..')
        self.close()
        print('[SERVER] Stopped.')
