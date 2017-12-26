#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" Tests for fim - fortune improved (2018) """

import unittest
from tempfile import mkstemp
from fim import Epigram, EpigramStore, SoloEpigramImporter, FortuneFileImporter


FORTUNE_FILE = "test/fishes_fortune"
EXPECTED_FORTUNE = ["redfish", "bluefish", "onefish", "twofish"]


class EpigramTest(unittest.TestCase):

    def test_create_basic_epigram(self):
        content = "quick brown fox"
        category = "category"

        epigram = Epigram(content, category)

        self.assertEqual(epigram.content, content)
        self.assertEqual(epigram.category, category)
        self.assertIsNotNone(epigram.uuid)


redfish_epigram = Epigram('blah', 'test_data')


class EpigramStoreTest(unittest.TestCase):
    def setUp(self):
        (handle, path) = mkstemp
        self.db = EpigramStore(path)

    def test_no_rows(self):
        result = self.db.get_epigram()
        self.assertEqual(result.content, EpigramStore.NO_RESULTS_FOUND.content)

    def test_bad_schema(self):
        result = self.db.get_epigram()
        self.assertEqual(result.content, EpigramStore.GENERAL_ERROR.content)

    def test_add_and_get_epigram(self):
        self.db.add_epigram(redfish_epigram)
        result = self.db.get_epigram()
        self.assertEqual(result.content, redfish_epigram.content)


class FortuneImporterTest(unittest.TestCase):
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
