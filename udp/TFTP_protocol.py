import struct
from dataclasses import dataclass

""" TFTP PROTOCOL """
DEFAULT_IP = '127.0.0.1'
DEFAULT_HOSTNAME = ''
DEFAULT_PORT = 69
DEFAULT_ROOT_DIR = 'C:\\'  # TODO -- os
DEFAULT_MODE = 'octet'  # TODO

BUF_SIZE = 65536
MAX_BLOCK_NUMBER = 65536
CHUNK_SIZE = 512

MAX_RETRIES = 10
REPEAT_TIMEOUT = 1

CLIENT_TIMEOUT = 5


class TFTP:
    @dataclass
    class Opcodes:
        """Class containing all the opcodes used in TFTP."""
        RRQ = b'\x00\x01'
        WRQ = b'\x00\x02'
        DATA = b'\x00\x03'
        ACK = b'\x00\x04'
        ERROR = b'\x00\x05'

    @dataclass
    class ErrorCodes:
        """Class containing all the opcodes used in TFTP."""
        NOT_DEFINED = 0
        FILE_NOT_FOUND = 1
        ACCESS_VIOLATION = 2
        ALLOCATION = 3
        ILLEGAL_OPERATION = 4
        UNKNOWN_TRANSFER_ID = 5
        FILE_ALREADY_EXISTS = 6
        NO_SUCH_USER = 7

    OPCODES = Opcodes

    ERROR_CODES = ErrorCodes

    ERROR_MSG = ['Not defined.',
                 'File not found.',
                 'Access violation.',
                 'Disk full or allocation exceeded.',
                 'Illegal TFTP operation.',
                 'Unknown transfer ID.',
                 'File already exists.',
                 'No such user.']

    MODES = {
        'unknown': 0,
        'netascii': 1,
        'octet': 2,
        'mail': 3}


""" PACKAGE BUILDERS """


def build_rrq_packet(filename: str, mode: str):
    packet = TFTP.OPCODES.RRQ + filename.encode() + b'\x00' + mode.encode() + b'\x00'
    return packet


def build_wrq_packet(filename: str, mode: str):
    packet = TFTP.OPCODES.WRQ + filename.encode() + b'\x00' + mode.encode() + b'\x00'
    return packet


def build_data_packet(block_number: int, data: bytes):
    packet = TFTP.OPCODES.DATA + struct.pack(b'!H', block_number) + data
    return packet


def build_ack_packet(block_number: int):
    packet = TFTP.OPCODES.ACK + struct.pack(b'!H', block_number)
    return packet


def build_error_packet(error_code: int):
    packet = TFTP.OPCODES.ERROR + struct.pack(b'!H', error_code) + TFTP.ERROR_MSG[error_code].encode() + b'\x00'
    return packet


""" PACKAGE UNPACKERS """


def unpack_request(data: bytes):
    packet = data[2:].split(b'\x00')  # without opcode
    filename_part = bytes.decode(packet[0])
    mode_part = bytes.decode(packet[1])
    return filename_part, mode_part


def unpack_error(data: bytes):
    err_code = struct.unpack('!H', data[2:4])[0]
    err_msg = data[4:-1]
    return err_code, err_msg
