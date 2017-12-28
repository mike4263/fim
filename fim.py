#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uuid as uuid_stdlib
import logging
import re
import os
import glob
from pudb import set_trace
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    create_engine
)
import datetime


""" fim - fortune improved """


log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
# logging.basicConfig(level=logging.DEBUG)


Session = sessionmaker()
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

    epigram_uuid = Column(
        String, default=generate_uuid(), primary_key=True)
    bucket = relationship("Bucket", backref="epigram")
    bucket_id = Column(Integer, ForeignKey("bucket.bucket_id"))
    created_date = Column(String, default=datetime.datetime.now())
    modified_date = Column(String, default=datetime.datetime.now())
    content_source = Column(String)
    content_text = Column(String)
    content = Column(String)
    # where the content originated from, (i.e. intro blog post)
    source_url = Column(String)
    # used with content_type (i.e. asciicast overview)
    action_url = Column(String)
    context_url = Column(String)  # deep dive info link (i.e. github repo)

    def __init__(self, **kwargs):
        self.epigram_uuid = generate_uuid()

        if 'content' in kwargs:
            self.content = kwargs['content']

        if 'bucket' in kwargs:
            self.bucket = kwargs['bucket']
        # if 'uuid' not in kwargs:

    def __str__(self):
        return f"<Epigram epigram_uuid={self.epigram_uuid}, " + \
            f"bucket_id={self.bucket_id}, " + \
            f"bucket={self.bucket}>"

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
    """ This file handles the loading of epigram from files in the legacy
        fortune format.  This is a simple structure with content delimited by
        % characters on single markers.  Like:

        redfish
        %
        bluefish
        %
        onefish
        twofish
        %
        something else
        %

    Positional Arguments:
    - uri (str) - the file path to the fortunes.  If this is a directory,
                  then the entire directory will be loaded


    Keyword Arguments:
    - bucket (Bucket) - the bucket that this fortune file should belone to
                          if not specified, this is the the basename of the
                          of the file w\\o extension
    """

    def __init__(self, uri, bucket=None):

        if not os.path.exists(uri):
            raise AttributeError(f"File {uri} does not exist")

        # normalize this
        uri = os.path.realpath(uri)

        if os.path.isdir(uri):
            self._filenames = glob.glob(uri + "/*")
            log.debug(self._filenames)
        elif os.path.isfile(uri):
            self._filenames = [uri]
        else:
            raise RuntimeError("Unexpected filetype for " + uri)

        self._bucket = bucket

    def process(self):
        for fname in self._filenames:
            with open(fname, 'r') as fortune_file:
                bucket = None
                if self._bucket is None:
                    bucket = self._determine_bucket(fname)
                else:
                    bucket = self._bucket

                for snippet in self.process_fortune_file(fortune_file.read()):
                    yield Epigram(content=snippet, bucket=bucket)

    def _determine_bucket(self, file_name):
        base_name = os.path.basename(file_name)
        bucket_name = os.path.splitext(base_name)[0]
        return Bucket(name=bucket_name)

    @classmethod
    def process_fortune_file(self, file_contents):
        delimiter = re.compile(r'^%$')
        e = ''
        for f in file_contents.split("\n"):
            if re.search(delimiter, f):
                yield e.rstrip()
                e = ""
            else:
                e += f + "\n"


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

        db_uri = 'sqlite:///' + self._filename
        self._engine = create_engine(db_uri, echo=False)
        log.debug("Initializing db" + db_uri)
        Session.configure(bind=self._engine)
        self._session = Session()
        Base.metadata.create_all(self._engine)

    def get_epigram(self, uuid=None, internal_fetch_ratio=1.0, bucket=None):
        """ Get a epigram considering filter criteria and weight rules

            Keyword Arguments:
            uuid (str) - return this specific epigram
            internal_fetch_ratio (int) - see the README for info on the
                                                  weighting algorithm

            Return:
            An Epigram (obviously)
        """
        (x, ) = self._session.query(Epigram)
        log.debug(x)
        return x

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
        for e in importer.process():
            # log.debug("Inserting Epigram " + str(e))
            self._session.add(e)
        self._session.commit()


def main():
    pass


if __name__ == '__main__':
    main()
