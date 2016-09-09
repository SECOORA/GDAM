#!/usr/bin/env python

# Announces data from flight and science files as merged
# JSON documents to ZeroMQ
#
# ZMQ JSON Messages:
# * set_start: Announces the start time and glider
#   - Use start time and glider to differentiate sets if necessary
# * set_data: Announces a row of data
# * set_end: Announces the end of a glider data set
#
# By: Michael Lindemuth
# University of South Florida
# College of Marine Science
# Ocean Technology Group

import os
from datetime import datetime

import zmq
import pymongo
from pyinotify import ProcessEvent

from gutils.gbdr import GliderBDReader, MergedGliderBDReader

import logging
logger = logging.getLogger(__name__)


class GliderPairInserter(object):
    """ Inserts data from a pair of glider files into GDAM """

    remove_time_fields = (
        'm_present_time-timestamp',
        'sci_m_present_time-timestamp'
    )

    gps_fields = ("m_gps_lon-lon", "m_lon-lon", "c_wpt_lon-lon")

    def __init__(self, glider, deployment, pair, mongo_url, dbname=None):
        self.pair = pair
        self.start = datetime.utcnow()
        self.end = datetime.utcfromtimestamp(0)
        self.processed = datetime.utcnow()

        dbname = dbname or 'GDAM'
        self.mongo_client = pymongo.MongoClient(mongo_url)
        self.db = self.mongo_client[dbname]

        deployment = deployment or 'unknown'
        self.collection_name = "{}.{}.{}{}".format(
            glider,
            deployment,
            pair[0],
            pair[1]
        )
        self.collection = self.db[self.collection_name]

    def __find_GPS(self, data):
        for field in self.gps_fields:
            if field in data:
                gps_prefix = field[0:field.find('lon')]
                lat_field = "%slat-lat" % gps_prefix

                lon = data[field]
                lat = data[lat_field]
                del data[field]
                del data[lat_field]

                field_name = "%slonlat-lonlat" % gps_prefix
                data[field_name] = {
                    "type": "Point",
                    "coordinates": [lon, lat]
                }

        return data

    def insert_filenames(self, glider, deployment, flight_file, science_file):
        deployment = deployment or 'unknown'
        file_collection_name = "%s.%s.processed_files" % (
            glider,
            deployment
        )
        self.file_collection = self.db[file_collection_name]

        duplicate_set = self.file_collection.find({
            'flight_file': flight_file,
            'science_file': science_file
        }).count() > 0

        if not duplicate_set:
            self.file_set_id = self.file_collection.insert({
                'flight_file': flight_file,
                'science_file': science_file,
                'date_processed': self.processed
            })
        else:
            raise LookupError('File set %s & %s have already been processed.' %
                              (flight_file, science_file))

    def insert_data(self, data):
        # Setup the timestamp field for Mongo
        for field in self.remove_time_fields:
            if field in data:
                del data[field]
        data['timestamp'] = datetime.utcfromtimestamp(data['timestamp'])

        if data['timestamp'] < self.start:
            self.start = data['timestamp']
        elif data['timestamp'] > self.end:
            self.end = data['timestamp']

        # If available, setup the lat lon field for Mongo
        data = self.__find_GPS(data)

        # Add the file_set_id to the document
        data['file_set_id'] = self.file_set_id

        try:
            self.collection.insert(data)
        except BaseException:
            logger.exception('Error inserting {}'.format(data))

    def update_file_timespan(self):
        self.file_collection.update(
            {'_id': self.file_set_id},
            {
                '$set': {
                    'start_timestamp': self.start,
                    'end_timestamp': self.end
                }
            }
        )


FLIGHT_SCIENCE_PAIRS = [('dbd', 'ebd'), ('sbd', 'tbd'), ('mbd', 'nbd')]


class GliderFileProcessor(ProcessEvent):

    def my_init(self, zmq_url, mongo_url):
        self.zmq_url = zmq_url
        self.mongo_url = mongo_url

        self.glider_data = {}

        # Create ZMQ context and socket for publishing files
        context = zmq.Context()
        self.socket = context.socket(zmq.PUB)
        self.socket.bind(self.zmq_url)

    def process_segment_pair(self, glider, deployment, path, file_base, pair):
        segment_id = int(file_base[file_base.rfind('-') + 1:file_base.find('.')])

        flight_file = file_base + pair[0]
        science_file = file_base + pair[1]

        dupe = False
        inserter = GliderPairInserter(glider, deployment, pair, self.mongo_url)
        try:
            inserter.insert_filenames(glider, deployment, flight_file, science_file)
        except LookupError:
            logger.warning('Duplicate detected')
            dupe = True

        # Read the file
        flight_reader = GliderBDReader([os.path.join(path, flight_file)])
        science_reader = GliderBDReader([os.path.join(path, science_file)])
        merged_reader = MergedGliderBDReader(flight_reader, science_reader)

        if dupe is False:
            for data in merged_reader:
                inserter.insert_data(data)
            inserter.update_file_timespan()
        else:
            inserter = None

        self.publish_segment_processed(
            glider, deployment, segment_id,
            path, flight_file, science_file,
            merged_reader, inserter
        )

    def publish_segment_processed(self, glider, deployment, segment_id, path, flight_file, science_file, merged_reader, inserter):  # NOQA

        logger.info(
            'Publishing glider {0} segment {1:d} data in {2} & {3}'.format(
                glider,
                segment_id,
                flight_file,
                science_file
            )
        )

        message = {
            'processed': inserter.processed.isoformat() if inserter else None,
            'start': inserter.start.isoformat() if inserter else None,
            'end': inserter.end.isoformat() if inserter else None,
            'path': path,
            'flight_file': flight_file,
            'science_file': science_file,
            'glider': glider,
            'deployment': deployment,
            'segment': segment_id,
            'headers': merged_reader.headers
        }
        self.socket.send_json(message)

        self.glider_data[glider]['files'].remove(flight_file)
        self.glider_data[glider]['files'].remove(science_file)

    def check_for_pair(self, event):
        if len(event.name) > 0 and event.name[0] is not '.':
            # Add full path to glider data queue
            folder_name = os.path.basename(event.path)
            if '__' in folder_name:
                glider_name, glider_deployment = (folder_name.split('__', maxsplit=1))
            else:
                glider_name = folder_name
                glider_deployment = ''

            glider_name = os.path.basename(event.path)
            if glider_name not in self.glider_data:
                self.glider_data[glider_name] = {}
                self.glider_data[glider_name]['path'] = event.path
                self.glider_data[glider_name]['files'] = []

            self.glider_data[glider_name]['files'].append(event.name)

            fileType = event.name[-3:]

            # Check for matching pair
            for pair in FLIGHT_SCIENCE_PAIRS:
                checkFile = None
                if fileType == pair[0]:
                    checkFile = event.name[:-3] + pair[1]
                elif fileType == pair[1]:
                    checkFile = event.name[:-3] + pair[0]

                if checkFile in self.glider_data[glider_name]['files']:
                    try:
                        self.process_segment_pair(
                            glider_name, glider_deployment, event.path, event.name[:-3], pair
                        )
                    except BaseException:
                        logger.exception(
                            'Error processing pair {}'.format(event.name[:-3])
                        )

    def valid_extension(self, name):
        extension = name[name.rfind('.') + 1:]
        for pair in FLIGHT_SCIENCE_PAIRS:
            if extension == pair[0] or extension == pair[1]:
                return True

        logger.error("Unrecognized file extension for event: %s" % extension)
        return False

    def process_IN_CLOSE(self, event):
        if self.valid_extension(event.name):
            self.check_for_pair(event)

    def process_IN_MOVED_TO(self, event):
        if self.valid_extension(event.name):
            self.check_for_pair(event)
