#!/usr/bin/env python

# Subscribes to the Glider Database Alternative with Mongo ZMQ Socket.
# When a new set is published, it outputs a new NetCDF to a given
# output directory.
#
# By: Michael Lindemuth
# University of South Florida
# College of Marine Science
# Ocean Technology Group

import os
import sys
import argparse
import subprocess

import zmq

import logging
logger = logging.getLogger(__name__)


MODE_MAPPING = {
    "rt": [".sbd", ".tbd", ".mbd", ".nbd"],
    "delayed": [".dbd", ".ebd"]
}


def handle_message(message, config_path, output_path):
    mode = 'rt'

    filename, extension = os.path.splitext(message['flight_file'])
    if extension in MODE_MAPPING['delayed']:
        mode = 'delayed'
    else:
        mode = 'rt'

    flight_path = os.path.join(
        message['path'],
        message['flight_file']
    )
    science_path = os.path.join(
        message['path'],
        message['science_file']
    )

    glider_name = message['glider']
    deployment_name = message['deployment']

    config_folder_options = [
        os.path.join(config_path, '{}__{}'.format(glider_name, deployment_name)),
        os.path.join(config_path, '{}_{}'.format(glider_name, deployment_name)),
        os.path.join(config_path, '{}-{}'.format(glider_name, deployment_name)),
        os.path.join(config_path, glider_name),
    ]
    config_folder = None
    for cp in config_folder_options:
        if os.path.isdir(cp):
            config_folder = cp
            break
    if config_folder is None:
        raise ValueError("No config folder found for Glider {} and Deployment {}".format(
            glider_name,
            deployment_name
        ))

    cmds = [
        "create_glider_netcdf.py",
        config_folder,
        output_path,
        "--mode",
        mode,
        "-f",
        flight_path,
        "-s",
        science_path
    ]
    logger.info('Running: {}'.format(' '.join(cmds)))
    try:
        cp = subprocess.run(
            cmds,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(e.stdout)
    else:
        logger.info(cp.stdout)


def main():
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())

    parser = argparse.ArgumentParser(
        description="Subscribes to the Glider Database Alternative with Mongo "
                    "Socket. When a new set is published, it outputs a new "
                    "NetCDF to a given output directory."
    )
    parser.add_argument(
        "--zmq_url",
        help='Port to listen for ZMQ GDAM messages. '
             'Default is "tcp://127.0.0.1:44444".',
        default=os.environ.get('ZMQ_URL', 'tcp://127.0.0.1:44444')
    )
    parser.add_argument(
        "--configs",
        help="Folder to look for NetCDF global and glider "
             "JSON configuration files.  Default is './config'.",
        default=os.environ.get('GDAM2NC_CONFIG', './config')
    )
    parser.add_argument(
        "--output",
        help="Where to place the newly generated netCDF files.",
        default=os.environ.get('GDAM2NC_OUTPUT')
    )
    parser.add_argument(
        '--time',
        help="Set time parameter to use for profile recognition",
        default="timestamp"
    )
    parser.add_argument(
        '--depth',
        help="Set depth parameter to use for profile recognition",
        default="m_depth-m"
    )
    parser.add_argument(
        '--gps',
        help="Set prefix for gps parameters to use for location estimation",
        default="m_gps_"
    )

    args = parser.parse_args()

    if not args.output:
        logger.error("Please provide an --output argument or set the "
                     "GDAM2NC_OUTPUT environmental variable")
        sys.exit(parser.print_usage())

    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect(args.zmq_url)
    socket.setsockopt(zmq.SUBSCRIBE, b'')

    logger.info("Loading configuration from {}\nListening to {}\nSaving to {}".format(
        args.configs,
        args.zmq_url,
        args.output)
    )

    while True:
        try:
            message = socket.recv_json()
            handle_message(message, args.configs, args.output)
        except KeyboardInterrupt:
            break
        except BaseException:
            logger.exception('Subscriber exited')
            break

    logger.info('Stopped')

if __name__ == '__main__':
    sys.exit(main())
