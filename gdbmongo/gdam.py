#!/usr/bin/python

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

import argparse
import sys
import os
import signal
import logging
logger = logging.getLogger("GDAM")

from pyinotify import (
    WatchManager,
    Notifier,
    NotifierError,
    IN_CLOSE_WRITE,
    IN_MOVED_TO
)

from gdbmongo.processor import GliderFileProcessor


def main():
    parser = argparse.ArgumentParser(
        description="Monitor a directory for new glider data.  "
                    "Processes and uploads new data to a Mongo Database. "
                    "Announce changes via ZMQ."
    )
    parser.add_argument(
        "glider_directory_path",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--zmq_port",
        help="Port to publish ZMQ messages on.  8008 by default.",
        type=int,
        default=8008
    )
    parser.add_argument(
        "--daemonize",
        help="To daemonize or not to daemonize",
        type=bool,
        default=False
    )
    parser.add_argument(
        "--pid_file",
        help="Where to look for and put the PID file",
        default="./gdam.pid"
    )
    parser.add_argument(
        "--log_file",
        help="Full path of file to log to",
        default="./gdam.log"
    )
    parser.add_argument(
        "--mongo_url",
        help="Mongo Database URL.  Can include authentication parameters",
        default="mongodb://localhost"
    )

    args = parser.parse_args()

    # Check environment variable if not mongo URL specified
    if args.mongo_url == "mongodb://localhost":
        args.mongo_url = os.environ.get('GDAM_MONGO_URL', args.mongo_url)

    # Setup logger
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(name)s "
                                  "- %(levelname)s - %(message)s")
    if args.daemonize:
        log_handler = logging.FileHandler(args.log_file)
    else:
        log_handler = logging.StreamHandler(sys.stdout)
    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)

    monitor_path = args.glider_directory_path
    if monitor_path[-1] == '/':
        monitor_path = monitor_path[:-1]

    wm = WatchManager()
    mask = IN_MOVED_TO | IN_CLOSE_WRITE
    wdd = wm.add_watch(args.glider_directory_path, mask,
                       rec=True, auto_add=True)

    processor = GliderFileProcessor(args.zmq_port, args.mongo_url)
    notifier = Notifier(wm, processor)

    def handler(signum, frame):
        wm.rm_watch(wdd.values())
        processor.stop()
        notifier.stop()

    signal.signal(signal.SIGTERM, handler)

    try:
        logger.info("Starting")
        notifier.loop(daemonize=args.daemonize, pid_file=args.pid_file)
    except NotifierError, err:
        logger.error('Unable to start notifier loop: %s' % err)
        return 1

    logger.info(
        "Glider Database Alternative with Mongo Service Exited Successfully"
    )
    return 0

if __name__ == '__main__':
    sys.exit(main())
