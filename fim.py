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


class Bucket():
    """ Epigrams belong to a single bucket, which is used to classify content.

        Buckets are categories and the primary mechanism of organization within
        FIM.  They will typically map to a single content source (e.g. fortune
        text file), however this is not a requirement.

        Buckets are the primary mechanism used by the "Bucket Sort" algothorim.
        See the readme for the details
    """

    def __init__(self, name, **kwargs):
        """ Buckets must have a name.  All other fields are optional

            Arguments:
            - name (str) - buckets must contain

            Keyword Args
            - bucket_id (int) - the autoincrementing int from the DB
            - name (str) - redudant, not used
            - item_weight (int) - the multiple for each individual content.
                                    used in the BucketSort

            NOTE: these args map directly into the dict returned from the

            TODO: I dont like the redudant name...
        """

        self._name = name

        if 'item_weight' in kwargs:
            self._item_weight = kwargs['item_weight']

        if 'bucket_id' in kwargs:
            self._id = kwargs['bucket_id']

    @property
    def name(self):
        return self._name

    @property
    def id(self):
        try:
            return self._id
        except AttributeError:
            return None

    @property
    def item_weight(self):
        return self._item_weight


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
        self._filename = filename

        if not os.path.exists(self._filename):
            self._init_db()

        db_uri = 'sqlite:///' + self._filename
        log.debug("Initializing db" + db_uri)

        self._db = records.Database(db_uri)

    def _init_db(self, new_file=False):
        """ Create the schema in the DB using a native sqlite3 connection

        This method uses the native connection.  This could probably
        be refactored to use the native SQLAlchemy engine...
        """
        log.debug("Adding schema")
        sqlite_db = sqlite3.connect(self._filename)

        with open("schema.sql", 'r', encoding='utf-8') as f:
            schema = f.read()
            sqlite_db.executescript(schema)

        sqlite_db.commit()
        sqlite_db.close()

    def get_epigram(self, uuid=None, internal_fetch_ratio=1.0, bucket=None):
        """ Get a epigram considering filter criteria and weight rules

            Keyword Arguments:
            uuid (str) - return this specific epigram
            internal_fetch_ratio (int) - see the README for info on the
                                                  weighting algorithm

            Return:
            An Epigram (obviously)
        """
        return self._select_epigram()

    def add_epigram(self, epigram):
        """ Add an epigram to the store

        Positional Arguments:
        epigram - the epigram to add

        Returns: the newly generated epigram

        """
        solo = SoloEpigramImporter(epigram)
        self.add_epigram_via_importer(solo)

    def add_epigram_via_importer(self, importer):
        """ Method that does stuff

            Positional Arguments:
            content (str) - the plain text content of the epigram

            Keyword Arguments:
            uuid (str) - a unique id for the item (generated if blank)

            Return:
            object (str) - desc
        """
        t = self._db.transaction()
        for e in importer.process():
            self._insert_epigram(e)
        t.commit()

    def _insert_epigram(self, epigram):
        log.debug("Inserting epigram for " + epigram.bucket)
        insert_query = """
        insert into epigram(epigram_uuid, bucket_id, content, created_date)
         values (:uuid, :bucket_id, :content, date('now'))
        """
        self._db.query(insert_query, uuid=epigram.uuid,
                       bucket_id=epigram.bucket,
                       content=epigram.content)

    def _select_epigram(self):
        log.debug("Query for epigram")
        select_query = """
        select * from epigram limit 1
        """
        r = self._db.query(select_query)

        if len(r) >= 1:
            row = r[0]
            return Epigram(row.content, row.bucket_id)
        else:
            return EpigramStore.NO_RESULTS_FOUND


def main():
    pass


if __name__ == '__main__':
    main()
