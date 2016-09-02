#!/usr/bin/env python

import os
import sys
import argparse

import zmq

import logging
from gdbmongo import logger
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


def main():
    parser = argparse.ArgumentParser(
        description="Monitor a ZeroMQ stream for information about new glider "
                    "data being added to Mongo."
    )
    parser.add_argument(
        "--zmq_url",
        help='Port to publish ZMQ messages on. '
             'Default is "tcp://127.0.0.1:8008".',
        default=os.environ.get('ZMQ_URL', 'tcp://127.0.0.1:8008')
    )

    args = parser.parse_args()

    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect(args.zmq_url)
    logger.info("Listening...")
    socket.setsockopt(zmq.SUBSCRIBE, b'')

    while True:
        try:
            logger.info('***********\n{}\n'.format(socket.recv_json()))
        except KeyboardInterrupt:
            break


if __name__ == '__main__':
    sys.exit(main())
