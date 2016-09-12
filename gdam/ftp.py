#!/usr/bin/env python

import os
import sys
import argparse
from ftplib import FTP

import netCDF4 as nc4
from pyinotify import (
    WatchManager,
    Notifier,
    NotifierError,
    IN_CLOSE_WRITE,
    IN_MOVED_TO
)

from pyinotify import ProcessEvent

import logging
logger = logging.getLogger(__name__)


class GliderNc2FtpProcessor(ProcessEvent):

    def my_init(self, ftp_url, ftp_user, ftp_pass):
        self.ftp_url = ftp_url
        self.ftp_user = ftp_user
        self.ftp_pass = ftp_pass

    def process_IN_CLOSE(self, event):
        if self.valid_extension(event.name):
            self.upload_file(event)

    def process_IN_MOVED_TO(self, event):
        if self.valid_extension(event.name):
            self.upload_file(event)

    def valid_extension(self, name):
        _, ext = os.path.splitext(name)
        if ext in ['.nc', 'nc4']:
            return True

        logger.error('Unrecognized file extension for event: {}'.format(ext))
        return False

    def upload_file(self, event):
        try:
            ftp = FTP(self.ftp_url)
            ftp.login(self.ftp_user, self.ftp_pass)

            with nc4.Dataset(event.pathname) as ncd:
                # Change into the correct deployment directory
                ftp.cwd(ncd.id)

            with open(event.pathname, 'rb') as fp:
                # Upload NetCDF file
                ftp.storbinary(
                    'STOR {}'.format(os.path.basename(event.pathname)),
                    fp
                )

            ftp.quit()

        except BaseException:
            logger.exception('Could not upload NetCDF file')


def main():
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())

    parser = argparse.ArgumentParser(
        description="Monitor a directory for new netCDF glider data and "
                    "upload the netCDF files to an FTP site."

    )
    parser.add_argument(
        "--ftp_url",
        help="Path to the glider data netCDF output directory",
        default=os.environ.get('NC2FTPURL')
    )
    parser.add_argument(
        "--ftp_user",
        help="FTP username, defaults to 'anonymous'",
        default=os.environ.get('NC2FTPUSER', 'anonymous')
    )
    parser.add_argument(
        "--ftp_pass",
        help="FTP password, defaults to an empty string",
        default=os.environ.get('NC2FTPPASS', '')
    )
    parser.add_argument(
        "-i",
        "--input",
        help="Path to the glider data netCDF output directory",
        default=os.environ.get('GDAM2NC_OUTPUT')
    )
    parser.add_argument(
        "--daemonize",
        help="To daemonize or not to daemonize",
        type=bool,
        default=False
    )

    args = parser.parse_args()

    if not args.input:
        logger.error("Please provide an --input agrument or set the "
                     "GDAM2NC_OUTPUT environmental variable")
        sys.exit(parser.print_usage())

    if not args.ftp_url:
        logger.error("Please provide an --ftp_url agrument or set the "
                     "NC2FTPURL environmental variable")
        sys.exit(parser.print_usage())

    wm = WatchManager()
    mask = IN_MOVED_TO | IN_CLOSE_WRITE
    wm.add_watch(
        args.input,
        mask,
        rec=True,
        auto_add=True
    )

    processor = GliderNc2FtpProcessor(
        ftp_url=args.ftp_url,
        ftp_user=args.ftp_user,
        ftp_pass=args.ftp_pass,
    )
    notifier = Notifier(wm, processor)

    try:
        logger.info("Watching {}\nUploading to {}".format(
            args.input,
            args.ftp_url)
        )
        notifier.loop(daemonize=args.daemonize)
    except NotifierError:
        logger.exception('Unable to start notifier loop')
        return 1

    logger.info("NC2FTP Exited Successfully")
    return 0

if __name__ == '__main__':
    sys.exit(main())
