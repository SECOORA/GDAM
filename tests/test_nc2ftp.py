#!/usr/bin/env python
import os
import unittest

from gdam.ftp import profile_compliance

import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


class TestNc2Ftp(unittest.TestCase):

    def test_passing_testing_compliance(self):
        ncpath = os.path.join(os.path.dirname(__file__), 'resources', 'should_pass.nc')
        assert profile_compliance(ncpath) is True

    def test_failing_testing_compliance(self):
        ncpath = os.path.join(os.path.dirname(__file__), 'resources', 'should_fail.nc')
        assert profile_compliance(ncpath) is False
