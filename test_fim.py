#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" Tests for fim - fortune improved (2018) """

import unittest

from fim import Epigram, FortuneFile


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


class FortuneIngestTest(unittest.TestCase):
    def test_load_file(self):
        fortunes = FortuneFile(FORTUNE_FILE)
        i = 0
        for f in fortunes.process():
            self.assertEqual(f.content, fortunes[i])
            i += 1


if __name__ == '__main__':
    unittest.main()
