import os
from TFTP_client import TFTP_Client

SERVER_IP = '127.0.0.1'
SERVER_PORT = 5001
ROOT_DIR = 'Z:\\'
MODE = 'octet'


def print_separator():
    print('=' * 80)


def help_cmd():
    print('Available commands: GET/PUT\n'
          '\tGET command format: GET SERVER_FILENAME LOCAL_FILENAME\n'
          '\tPUT command format: PUT LOCAL_FILENAME SERVER_FILENAME')


def get_cmd():
    ans = str(input('Your command: ')).split(' ')
    cmd = ans[0].lower()
    if len(ans) != 3 or cmd not in ['get', 'put']:
        print('Invalid command')
        return get_cmd()
    else:
        return cmd, ans[1], ans[2]


if __name__ == '__main__':
    print('Running TFTP client')
    help_cmd()
    tftp_client = TFTP_Client(server_ip=SERVER_IP,
                              server_port=SERVER_PORT,
                              root_dir=os.path.abspath(ROOT_DIR),
                              mode=MODE)
    while True:
        print_separator()
        args = get_cmd()
        tftp_client.run_command(*args)

# GET Z:\\Projects\\_Amazing\\TFTP_Client\\img.jpg Z:\\img.jpg
# PUT Z:\\img2.jpg Z:\\Projects\\_Amazing\\TFTP_Client\\img2.jpg
