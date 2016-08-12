from argparse import ArgumentParser
from pokerserver.client import SimpleClient


def main():
    parser = ArgumentParser(
        description='Simple client for our Python workshop at TNG Technology Consulting.'
    )
    parser.add_argument('-p', '--port', type=int, help='Server port number', default=5555)
    parser.add_argument('-s', '--host', help='Server address', default='localhost')
    parser.add_argument('-u', '--uuid', help='UUID of the player', default=None)
    parser.add_argument(help='Player name', dest='name')
    args = parser.parse_args()

    client = SimpleClient(args.host, args.port, args.name, args.uuid)
    client.play()


if __name__ == "__main__":
    main()
