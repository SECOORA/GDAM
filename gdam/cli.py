#!/usr/bin/env python

# GDAM - Glider Database Alternative with Mongo
#
# Monitors a glider directory for changes.
# When a change occurs, it performs the following
# in order:
#     1) Looks for a flight/science pair.
#     2) Processes and merges the file pair with dbd2asc.
#     3) Inserts new data to MongoDB.
#     4) Publishes details about processed dataset to
#        a ZMQ queue.
#
# The format of these ZMQ mulit-part messages is as follows:
#
# ZMQ Message Format:
# * Glider Name
# * Mission
# * Segment
# * New Data Start Timestamp
# * New Data End Timestamp
# * List of New Data Files
#
# By: Michael Lindemuth <mlindemu@usf.edu>
# University of South Florida
# College of Marine Science
# Ocean Technology Group

import os
import sys
import argparse

from pyinotify import (
    WatchManager,
    Notifier,
    NotifierError,
    IN_CLOSE_WRITE,
    IN_MOVED_TO
)

from gdam.processor import GliderFileProcessor

import logging
logging.captureWarnings(True)
logger = logging.getLogger(__name__)


def main():
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())
    logging.getLogger('py.warnings').setLevel(logging.ERROR)

    parser = argparse.ArgumentParser(
        description="Monitor a directory for new glider data. "
                    "Processes and uploads new data to a Mongo Database. "
                    "Announce changes via ZMQ."
    )
    parser.add_argument(
        "-d",
        "--data_path",
        help="Path to Glider data directory",
        default=os.environ.get('GDB_DATA_DIR')
    )
    parser.add_argument(
        "--zmq_url",
        help='Port to publish ZMQ messages on. '
             'Default is "tcp://127.0.0.1:44444".',
        default=os.environ.get('ZMQ_URL', 'tcp://127.0.0.1:44444')
    )
    parser.add_argument(
        "--mongo_url",
        help='Mongo Database URL.  Can include authentication parameters. '
             'Default is "mongodb://localhost:27017".',
        default=os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    )
    parser.add_argument(
        "--daemonize",
        help="To daemonize or not to daemonize",
        type=bool,
        default=False
    )

    args = parser.parse_args()

    if not args.data_path:
        logger.error("Please provide a --data_path agrument or set the "
                     "GDB_DATA_DIR environmental variable")
        sys.exit(parser.print_usage())

    monitor_path = args.data_path
    if monitor_path[-1] == '/':
        monitor_path = monitor_path[:-1]

    wm = WatchManager()
    mask = IN_MOVED_TO | IN_CLOSE_WRITE
    wm.add_watch(
        args.data_path,
        mask,
        rec=True,
        auto_add=True
    )

    processor = GliderFileProcessor(
        zmq_url=args.zmq_url,
        mongo_url=args.mongo_url
    )
    notifier = Notifier(wm, processor)

    try:
        logger.info("Watching {}\nInserting into {}\nPublishing to {}".format(
            args.data_path,
            args.mongo_url,
            args.zmq_url)
        )
        notifier.loop(daemonize=args.daemonize)
    except NotifierError:
        logger.exception('Unable to start notifier loop')
        return 1

    logger.info("GDAM Exited Successfully")
    return 0

if __name__ == '__main__':
    sys.exit(main())
