#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uuid as uuid_stdlib
import records
import logging
import sqlite3
import os
from pudb import set_trace


""" fim - fortune improved """


log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
# logging.basicConfig(level=logging.DEBUG)


class BaseImporter():
    """ Base class for all of the content type """

    def __init__(self, uri):
        pass

    def process(self):
        yield None


class FortuneFileImporter(BaseImporter):
    def __init__(self, uri):
        pass

    def process(self):
        raise NotImplementedError()


class SoloEpigramImporter(BaseImporter):
    """ Add a single epigram """

    def __init__(self, epigram):
        self._epigram = epigram

    def process(self):
        yield self._epigram


class Epigram():
    """ This is the basic unit of content in fim.

        An epigram is a brief, interesting, memorable, and sometimes surprising
        or satirical statement. The word is derived from the Greek: ἐπίγραμμα
        epigramma "inscription" from ἐπιγράφειν epigraphein "to write on, to
        inscribe", and the literary device has been employed for over two
        millennia.

        BTW 'epigram' was directly lifted from the fortune man page *shrugs*.

        Epigram contain the following items:
          - epigram_uuid - unique 128 byte character string.
          - bucket_id - Epigram belong to a single bucket
          - content - plain text content (5k limit characters)

        These field names directly map to the EPIGRAM table in the DB.

    """

    def __init__(self, content, bucket, uuid=None):
        """ Basic constructor for the Epigram

            Method Argument:
                content (str) - the plain text content of the epigram
                bucket (str) - the bucket key (optional)

            Optional Params:
                uuid (str) - a unique id for the item (generated if blank)
        """
        self._content = content
        self._bucket = bucket

        if (uuid is None):
            self._uuid = str(uuid_stdlib.uuid4())
        else:
            self._uuid = uuid

    @property
    def content(self):
        return self._content

    @property
    def bucket(self):
        return self._bucket

    @property
    def uuid(self):
        return self._uuid


class EpigramStore():
    """ This class encapsulates the internal datastore (SQLite)"""

    NO_RESULTS_FOUND = Epigram("Your princess is in another castle. ", "error")
    GENERAL_ERROR = Epigram("Always bring a towel", "error")

    def __init__(self, filename, skip_dupes=False, _epigram_cache=[]):
        """ Construct the store (connect to db, optionally retrieve all rows)

            Positional Arguments:
            filename (str) - the path to the SQLite database

            Optional Params:
            skip_dupes (bool) - check each new epigram using fuzzy string
                                    matching.  Requires all existing records
                                    to be loaded into memory.

            Private Class Variables:
              _epigram_cache (list of Epigram) - internal loaded cached
        """
        raise NotImplementedError()

    def get_epigram(self, uuid=None, internal_fetch_ratio=1.0, category=None):
        """ Get a epigram considering filter criteria and weight rules

            Keyword Arguments:
            uuid (str) - return this specific epigram
            internal_fetch_ratio (int) - see the README for info on the
                                                  weighting algorithm

            Return:
            An Epigram (obviously)
        """
        raise NotImplementedError()

    def add_epigram(self, epigram):
        """ Add an epigram to the store

        Positional Arguments:
        epigram - the epigram to add

        Returns: the newly generated epigram

        """
        raise NotImplementedError()

    def add_epigram_via_importer(self, importer):
        """ Method that does stuff

            Positional Arguments:
            content (str) - the plain text content of the epigram

            Keyword Arguments:
            uuid (str) - a unique id for the item (generated if blank)

            Return:
            object (str) - desc
        """
        raise NotImplementedError()


def main():
    pass


if __name__ == '__main__':
    main()
