import os
from udp.server.TFTP_server import TFTP_Server

SERVER_PORT = 5002
ROOT_DIR = 'C:\\Projects\\tftp\\'
MODE = 'octet'

if __name__ == '__main__':
    print('Running TFTP server')
    tftp_server = TFTP_Server(host='',
                              port=SERVER_PORT,
                              root_dir=os.path.abspath(ROOT_DIR),
                              mode=MODE)
    tftp_server.launch()
