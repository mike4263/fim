#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" Tests for fim - fortune improved (2018) """

import re
import sys
import os
import random
import string
import unittest
from fim import Epigram, EpigramStore, SoloEpigramImporter, \
    FortuneFileImporter, Bucket, Impression
import logging
#from pudb import set_trace

logger = logging.getLogger()
logger.level = logging.DEBUG
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)


FORTUNE_FILE_DIR = "test_data"
FORTUNE_FILE = f"{FORTUNE_FILE_DIR}/fishes_fortune.txt"
EXPECTED_FORTUNE = ["redfish", "bluefish", "onefish", "twofish"]


class EpigramTest(unittest.TestCase):

    def test_create_basic_epigram(self):
        content = "quick brown fox"
        epigram = Epigram(content=content)
        self.assertEqual(epigram.content, content)

    def test_create_epigram_with_bucket(self):
        content = "quick brown fox"
        bucket_name = "test_data"
        bucket = Bucket(bucket_id=400, name=bucket_name)
        epigram = Epigram(content=content, bucket_id=400)
        self.assertEqual(epigram.content, content)


class BucketTest(unittest.TestCase):
    def test_create_minimium_bucket(self):
        bucket_name = "test_case"
        bucket = Bucket(name=bucket_name)
        self.assertEqual(bucket.name, bucket_name)

    def test_create_complete_bucket(self):
        bucket_name = "test_case"
        bucket_id = 123
        item_weight = 2

        bucket = Bucket(name=bucket_name, bucket_id=bucket_id,
                        item_weight=item_weight)
        self.assertEqual(bucket.name, bucket_name)
        self.assertEqual(bucket.item_weight, item_weight)
        self.assertEqual(bucket.bucket_id, 123)


class EpigramStoreTest(unittest.TestCase):
    test_db_path = "/tmp/fim_test.db"

    def setUp(self):
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

        self.db = EpigramStore(self.test_db_path)

    @unittest.skip("until db works")
    def test_no_rows(self):
        result = self.db.get_epigram()
        self.assertEqual(result.content, EpigramStore.NO_RESULTS_FOUND.content)

    def test_add_and_get_epigram(self):
        epi = get_random_epigram()
        self.db.add_epigram(epi)
        result = self.db.get_epigram()
        self.assertEqual(result.content, epi.content)

    @unittest.skip("move to integration suite")
    def test_add_entire_directory(self):
        self.db.add_epigrams_via_importer(
            FortuneFileImporter('content/legacy_fortune/'))

    def test_impression_count_test(self):
        self.db.add_epigrams_via_importer(
            FortuneFileImporter('test_data/'))

        for x in range(32):
            self.db.get_epigram()

        self.assertEqual(self.db.get_impression_count(), 32)

    def test_get_buckets(self):
        self.db.add_epigrams_via_importer(FortuneFileImporter('test_data/'))

        (fishes, meta) = self.db.get_buckets()

        self.assertEqual(fishes.name, "fishes_fortune")
        self.assertEqual(meta.name, "meta_fortune")

    def test_get_bucket(self):
        self.db.add_epigrams_via_importer(FortuneFileImporter('test_data/'))

        fishes = self.db.get_bucket("fishes_fortune")
        self.assertEqual(fishes.name, "fishes_fortune")

    def test_impression_count_categories(self):
        self.db.add_epigrams_via_importer(FortuneFileImporter('test_data/'))

        for x in range(100):
            self.db.get_epigram(bucket_name="meta_fortune")

        for x in range(4):
            self.db.get_epigram(bucket_name="fishes_fortune")

        self.assertEqual(self.db.get_impression_count(), 104)
        self.assertEqual(self.db.get_impression_count(
            bucket_name="meta_fortune"), 100)
        self.assertEqual(self.db.get_impression_count(
            bucket_name="fishes_fortune"), 4)


sample_fortune_file = """redfish
%
bluefish
%
onefish
twofish
%
something else
%"""


class FortuneFileTest(unittest.TestCase):

    def test_load_file_no_bucket(self):
        fortunes = FortuneFileImporter(FORTUNE_FILE)
        i = 0
        for f in fortunes.process():
            self.assertEqual(f.content, EXPECTED_FORTUNE[i])
            logger.debug(f" e is {f}")
            self.assertEqual(f.bucket.name, "fishes_fortune")
            i += 1

    def test_load_file_with_bucket(self):
        bucket_name = "test_data"
        bucket = Bucket(bucket_id=400, name=bucket_name)
        fortunes = FortuneFileImporter(FORTUNE_FILE, bucket=bucket)
        i = 0
        for f in fortunes.process():
            self.assertEqual(f.content, EXPECTED_FORTUNE[i])
            self.assertEqual(f.bucket.name, bucket_name)
            i += 1

    def test_load_directory(self):
        fortunes = FortuneFileImporter(FORTUNE_FILE_DIR)

        i = 0
        for f in fortunes.process():
            i += 1

        # I actually have no idea how many fortunes there are buts its more
        # then 10
        self.assertTrue(i > 10)

    def test_nonexistent_file(self):
        self.assertRaises(AttributeError,
                          lambda: FortuneFileImporter(
                              uri='/some/fake/path/to/a/file'))

    def test_default_bucket(self):
        """ The bucket will be defined for each file, so this is None"""
        fortunes = FortuneFileImporter(FORTUNE_FILE)
        self.assertEqual(fortunes._bucket,  None)

    def test_defined_bucket(self):
        bucket_name = "test_data"
        bucket = Bucket(bucket_id=400, name=bucket_name)
        fortunes = FortuneFileImporter(FORTUNE_FILE, bucket=bucket)
        self.assertEqual(fortunes._bucket.name, bucket.name)

    def test_multiline_re(self):
        fishes = ['redfish', 'bluefish', 'onefish\ntwofish', 'something else']
        i = 0
        for (parsed_message) in \
                FortuneFileImporter.process_fortune_file(sample_fortune_file):
            print("--", parsed_message,  "\n")
            self.assertEqual(fishes[i], parsed_message)
            i += 1

        self.assertEqual(i, 4)


class SoloImporterTest(unittest.TestCase):
    def test_single_epigram(self):
        epi = get_random_epigram()
        (x, ) = SoloEpigramImporter(epi).process()
        self.assertEqual(epi.content, x.content)


class ImpressionTest(unittest.TestCase):
    def test_impresssion_creation(self):
        epi = get_random_epigram()
        impression = Impression(epigram=epi)
        logger.debug(impression)
        self.assertEqual(impression.bucket.bucket_id,
                         epi.bucket.bucket_id)
        self.assertEqual(impression.epigram.epigram_uuid,
                         epi.epigram_uuid)


def get_random_epigram(bucket=None):

    if bucket is None:
        bucket = get_random_bucket()

    return Epigram(content=_random_string(), bucket=bucket,
                   bucket_id=bucket.bucket_id)


def get_random_bucket():
    return Bucket(name=_random_string())


def _random_string():
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(32))


def _random_id():
    return ''.join(random.choice(string.digits) for x in range(5))


if __name__ == '__main__':
    unittest.main()
