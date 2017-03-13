from argparse import ArgumentParser

from pokerserver.client import CliClient


def main():
    parser = ArgumentParser('Interactive script to test the server manually')
    parser.add_argument('-p', '--port', type=int, help='Server port number', default=5555)
    parser.add_argument('-s', '--host', help='Server address', default='localhost')
    parser.add_argument('-c', '--player-count', type=int, help='Number of players', default=2)
    parser.add_argument('--log-requests', action='store_true', help='Log REST requests')
    arguments = parser.parse_args()
    client = CliClient(**vars(arguments))
    client.run()


if __name__ == "__main__":
    main()
