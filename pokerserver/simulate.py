import argparse
import random
import threading

from pokerserver.client.simple import SimpleClient

NUMBER_OF_PLAYERS = 2


def get_random_name():
    return 'Player{}'.format(random.randint(1, 99))


def main():
    parser = argparse.ArgumentParser(description='Start several clients in parallel.')
    parser.add_argument('-n', '--number', type=int, help='Number of clients', default=2)
    args = parser.parse_args()

    for _ in range(args.number):
        client = SimpleClient('localhost', 5555, get_random_name(), None)
        client_thread = threading.Thread(target=client.play)
        client_thread.start()


if __name__ == "__main__":
    main()
