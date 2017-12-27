#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uuid as uuid_stdlib
import records
import logging
import sqlite3
import os
from pudb import set_trace
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker, relationship
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    DateTime,
    Sequence,
    Float
)
import datetime


""" fim - fortune improved """


log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
# logging.basicConfig(level=logging.DEBUG)


DBSession = scoped_session(sessionmaker())
Base = declarative_base()


class Bucket(Base):
    """ Epigrams belong to a single bucket, which is used to classify content.

        Buckets are categories and the primary mechanism of organization within
        FIM.  They will typically map to a single content source (e.g. fortune
        text file), however this is not a requirement.

        Buckets are the primary mechanism used by the "Bucket Sort" algothorim.
        See the readme for the details
    """

    __tablename__ = 'bucket'
    bucket_id = Column(Integer, primary_key=True)
    name = Column(String(50))
    item_weight = Column(Integer)

    def __str__(self):
        return f"<Bucket bucket_id={self.bucket_id}, name={self.name}>"


def generate_uuid():
    return str(uuid_stdlib.uuid4())


class Epigram(Base):
    """ This is the basic unit of content in fim.

        An epigram is a brief, interesting, memorable, and sometimes surprising
        or satirical statement. The word is derived from the Greek: ἐπίγραμμα
        epigramma "inscription" from ἐπιγράφειν epigraphein "to write on, to
        inscribe", and the literary device has been employed for over two
        millennia.

        BTW 'epigram' was directly lifted from the fortune man page *shrugs*.

    """
    __tablename__ = 'epigram'
    # TODO: make this a uuid
    epigram_uuid = Column(
        Integer, default=generate_uuid(), primary_key=True)
    bucket = relationship("Bucket", backref="epigram")
    bucket_id = Column(Integer, ForeignKey("bucket.bucket_id"))
    created_date = Column(String, default=datetime.datetime.now)
    modified_date = Column(String, default=datetime.datetime.now)
    content_source = Column(String)
    content_text = Column(String)
    content = Column(String)
    # where the content originated from, (i.e. intro blog post)
    source_url = Column(String)
    # used with content_type (i.e. asciicast overview)
    action_url = Column(String)
    context_url = Column(String)  # deep dive info link (i.e. github repo)

    def __str__(self):
        return f"<Epigram epigram_uuid={self.epigram_uuid}, \
            bucket_id={self.bucket_id}, content={self.content}>"

    @classmethod
    def generate_uuid():
        return str(uuid_stdlib.uuid4())


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


class EpigramStore():
    """ This class encapsulates the internal datastore (SQLite)"""

    ERROR_BUCKET = Bucket(bucket_id=123, name="error")
    NO_RESULTS_FOUND = Epigram(
        content="Your princess is in another castle. ", bucket_id=123)
    GENERAL_ERROR = Epigram(content="Always bring a towel", bucket_id=123)

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
        log.debug("Inserting epigram " + str(epigram))
        insert_query = """
        insert into epigram(epigram_uuid, bucket_id, content, created_date)
         values (:uuid, :bucket_id, :content, date('now'))
        """
        self._db.query(insert_query, uuid=epigram.epigram_uuid,
                       bucket_id=epigram.bucket_id,
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
