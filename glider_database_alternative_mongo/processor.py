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

from pyinotify import(
    ProcessEvent
)

import logging
logger = logging.getLogger("GDAM")

import zmq
from datetime import datetime

from glider_binary_data_reader import (
    GliderBDReader,
    MergedGliderBDReader
)

import pymongo


class GliderPairInserter(object):
    """Inserts data from a pair of glider files into GDAM
    """

    def __init__(self, glider, pair, mongo_url, dbname='GDAM'):
        self.glider = glider
        self.pair = pair
        self.start = datetime.utcnow()
        self.end = datetime.utcfromtimestamp(0)
        self.mongo_url = mongo_url

        self.processed = datetime.utcnow()
        self.mongo_client = pymongo.MongoClient(self.mongo_url)
        self.db = self.mongo_client[dbname]

        self.collection_name = "%s.%s%s" % (
            glider,
            pair[0],
            pair[1]
        )
        self.collection = self.db[self.collection_name]

    remove_time_fields = (
        'm_present_time-timestamp',
        'sci_m_present_time-timestamp'
    )

    gps_fields = ("m_gps_lon-lon", "m_lon-lon", "c_wpt_lon-lon")

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

    def insert_filenames(self, glider, flight_file, science_file):
        file_collection_name = "%s.processed_files" % glider
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
        except Exception, e:
            logger.info('Error inserting %s.  Exception: %s' % (data, e))

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
    def __init__(self, port, mongo_url):
        ProcessEvent.__init__(self)
        self.glider_data = {}

        self.port = port
        self.mongo_url = mongo_url

    def process_segment_pair(self, glider, path, file_base, pair):
        segment_id = int(file_base[file_base.rfind('-')+1:file_base.find('.')])
        logger.info(
            "Processing glider %s segment %d data in %s named %s pair %s"
            % (glider, segment_id, path, file_base, pair)
        )

        flight_file = file_base + pair[0]
        science_file = file_base + pair[1]

        inserter = GliderPairInserter(glider, pair, self.mongo_url)
        try:
            inserter.insert_filenames(glider, flight_file, science_file)
        except LookupError, e:  # Duplicate detected
            logger.error(e)
            return

        # Read the file
        flight_reader = GliderBDReader(
            path,
            pair[0],
            [flight_file]
        )
        science_reader = GliderBDReader(
            path,
            pair[1],
            [science_file]
        )
        merged_reader = MergedGliderBDReader(
            flight_reader, science_reader
        )
        for data in merged_reader:
            inserter.insert_data(data)

        inserter.update_file_timespan()

        self.publish_segment_processed(
            glider, segment_id, flight_file, science_file,
            merged_reader, inserter
        )

    def publish_segment_processed(self, glider, segment_id, flight_file, science_file, merged_reader, inserter):  # NOQA
        # Create ZMQ context and socket for publishing files
        context = zmq.Context()
        socket = context.socket(zmq.PUB)
        socket.bind("tcp://*:%d" % self.port)

        logger.info(
            "Publishing glider %s segment %d data in %s & %s"
            % (glider, segment_id, flight_file, science_file)
        )

        socket.send_json({
            'processed': inserter.processed.isoformat(),
            'start': inserter.start.isoformat(),
            'end': inserter.end.isoformat(),
            'flight_file': flight_file,
            'science_file': science_file,
            'glider': glider,
            'segment': segment_id,
            'headers': merged_reader.headers
        })

        self.glider_data[glider]['files'].remove(flight_file)
        self.glider_data[glider]['files'].remove(science_file)

    def check_for_pair(self, event):
        if len(event.name) > 0 and event.name[0] is not '.':
            # Add full path to glider data queue
            glider_name = event.path[event.path.rfind('/')+1:]
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
                            glider_name, event.path, event.name[:-3], pair
                        )
                    except Exception, e:
                        logger.error("Error processing pair %s: %s"
                                     % (event.name[:-3], e))

    def valid_extension(self, name):
        extension = name[name.rfind('.')+1:]
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
