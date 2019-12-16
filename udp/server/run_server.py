import os
from TFTP_server import TFTP_Server

SERVER_PORT = 5001
ROOT_DIR = 'Z:\\Projects\\_Amazing\\TFTP_Client\\'
MODE = 'octet'

if __name__ == '__main__':
    print('Running TFTP server')
    tftp_server = TFTP_Server(host='',
                              port=SERVER_PORT,
                              root_dir=os.path.abspath(ROOT_DIR),
                              mode=MODE)
    tftp_server.launch()
