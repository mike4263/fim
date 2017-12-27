#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" Tests for fim - fortune improved (2018) """

import re
import sys
import os
import unittest
from fim import Epigram, EpigramStore, SoloEpigramImporter, \
    FortuneFileImporter, Bucket
import logging

logger = logging.getLogger()
logger.level = logging.DEBUG
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)


FORTUNE_FILE = "test/fishes_fortune"
EXPECTED_FORTUNE = ["redfish", "bluefish", "onefish", "twofish"]


class EpigramTest(unittest.TestCase):

    def test_create_basic_epigram(self):
        content = "quick brown fox"
        bucket = "bucket"

        epigram = Epigram(content, bucket)

        self.assertEqual(epigram.content, content)
        self.assertEqual(epigram.bucket, bucket)
        self.assertIsNotNone(epigram.uuid)


class BucketTest(unittest.TestCase):
    def test_create_minimium_bucket(self):
        bucket_name = "test_case"
        bucket = Bucket(bucket_name)
        self.assertEqual(bucket.name, bucket_name)

    def test_create_complete_bucket(self):
        bucket_name = "test_case"
        bucket_id = 123
        item_weight = 2

        bucket = Bucket(bucket_name, id=bucket_id, item_weight=item_weight)
        self.assertEqual(bucket.name, bucket_name)
        self.assertEqual(bucket.item_weight, item_weight)
        self.assertEqual(bucket.id, None)

    def test_bucket_from_db(self):
        bucket_name = "test_case"
        bucket_id = 123
        item_weight = 2

        row = {'bucket_id': bucket_id, 'name': bucket_name,
               'item_weight': item_weight}

        # TODO: looking for a cleaner way to do this
        bucket = Bucket(**row)
        self.assertEqual(bucket.name, row['name'])
        self.assertEqual(bucket.item_weight, row['item_weight'])
        self.assertEqual(bucket.id, bucket_id)


redfish_epigram = Epigram('blah', 'test_data')


class EpigramStoreTest(unittest.TestCase):
    test_db_path = "/tmp/fim_test.db"

    def setUp(self):
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

        self.db = EpigramStore(self.test_db_path)

    def test_no_rows(self):
        result = self.db.get_epigram()
        self.assertEqual(result.content, EpigramStore.NO_RESULTS_FOUND.content)

    def test_add_and_get_epigram(self):
        self.db.add_epigram(redfish_epigram)
        result = self.db.get_epigram()
        self.assertEqual(result.content, redfish_epigram.content)


class FortuneImporterTest(unittest.TestCase):
    @unittest.skip("until db works")
    def test_load_file(self):
        fortunes = FortuneFileImporter(FORTUNE_FILE)
        i = 0
        for f in fortunes.process():
            self.assertEqual(f.content, fortunes[i])
            i += 1


class SoloImporterTest(unittest.TestCase):
    def test_single_epigram(self):
        (x, ) = SoloEpigramImporter(redfish_epigram).process()
        self.assertEqual(redfish_epigram.content, x.content)


if __name__ == '__main__':
    unittest.main()
