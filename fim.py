#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uuid as uuid_stdlib
import logging
import re
import os
import glob
import random
import sys
from pathlib import Path
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
log.addHandler(logging.StreamHandler(sys.stdout))
#logging.basicConfig(level=logging.ERROR)
log.setLevel(logging.INFO)

Session = sessionmaker()
Base = declarative_base()

# this is my homebrew id generator for bucket id generatio
i = 0
def mydefault():
    global i
    i += 1
    return i


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
    item_weight = Column(Integer, default=1)

#    def __init__(self, name, **kwargs):
#        super()
#        self.name = name
#        self.bucket_id = mydefault()


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
    modified_date = Column(String)
    last_impression_date = Column(String)
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
            self.bucket_id = self.bucket.bucket_id
        # if 'uuid' not in kwargs:

    def __str__(self):
        return f"<Epigram epigram_uuid={self.epigram_uuid}, " + \
            f"bucket_id={self.bucket_id}, " + \
            f"bucket={self.bucket}>"

    @classmethod
    def generate_uuid(cls):
        return str(uuid_stdlib.uuid1())


class Impression(Base):
    """ Track the views for each epigram """
    __tablename__ = 'impression'
    impression_id = Column(Integer, primary_key=True)
    bucket_id = Column(Integer, ForeignKey("bucket.bucket_id"))
    bucket = relationship("Bucket", backref="impression")
    epigram_uuid = Column(String, ForeignKey("epigram.epigram_uuid"))
    epigram = relationship("Epigram", backref="impression")
    impression_date = Column(String)

    def __init__(self, **kwargs):

        if 'epigram' in kwargs:
            self.epigram = kwargs['epigram']
            self.epigram_uuid = self.epigram.epigram_uuid
            self.impression_date = datetime.datetime.now()

            if self.epigram.bucket is not None:
                self.bucket = self.epigram.bucket
                self.bucket_id = self.bucket.bucket_id

    def __str__(self):
        return f"<Impression impression_id={self.impression_id}, " + \
            f"epigram_uuid={self.epigram_uuid}, " + \
            f"bucket_id={self.bucket_id}, " + \
            f"bucket={self.bucket}>"


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
        content="Your princess is in another castle. (404: File Not Found) ", bucket_id=123)
    GENERAL_ERROR = Epigram(content="Always bring a towel (500: General Error)", bucket_id=123)
    SQL_DIR="sql"

    def __init__(self, filename, force_random=False, skip_dupes=False, _epigram_cache=[]):
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
        self._force_random = force_random

        db_uri = 'sqlite:///' + self._filename
        self._engine = create_engine(db_uri, echo=False)
        log.debug("Initializing db" + db_uri)
        Session.configure(bind=self._engine)
        self._session = Session()
        Base.metadata.create_all(self._engine)
        self._load_sql_files()



    def _load_sql_files(self, file_dir=SQL_DIR):
        uri = os.path.realpath(file_dir)

        if os.path.isdir(uri):
            sql_files = glob.glob(uri + "/*")
        elif os.path.isfile(uri):
            sql_files = [uri]
        else:
            raise RuntimeError("FileNotFound: "  + uri)

        sql_files.sort()

        for fname in sql_files:
            with open(fname, 'r') as sql_text:
                log.debug(f"Processing %s file" % (fname))
                self._execute_sql(sql_text.read())

    def _execute_sql(self, sql_text):
        self._engine.execute(sql_text)


    def _get_weighted_bucket(self):
        """
        Using the patented BucketSort(TM) Technology this queries the impressions_calculated
        table.  This factors in the relative weights of each bucket compared to its actual
        impressions.  Buckets that have exceeded their allowable view percentage are excluded
        from selection.

        The selection itself is using the random.choice() method based on the probabilities

        :return: the bucket_id to use in the get epigram query
        """

        rs = self._engine.execute("""
            select bucket_id, effective_impression_percentage from impressions_calculated 
             where impression_delta >= 0
            """)

        buckets = []
        probabilties = []

        for row in rs:
            buckets.append(row[0])
            probabilties.append(row[1])

        try:
            bucket = random.choices(buckets, weights=probabilties)[0]
            return bucket
        except:
            return None



    def get_epigram(self, uuid=None, internal_fetch_ratio=1.0, bucket_name=None, bucket=None):
        """ Get a epigram considering filter criteria and weight rules

            Keyword Arguments:
            uuid (str) - return this specific epigram
            internal_fetch_ratio (int) - see the README.adoc for info on the
                                                  weighting algorithm
            bucket_name (str) - the natural key for the buckets
            bucket - a bucket object

            Return:
            An Epigram (obviously)
        """
        q = self._session.query(Epigram).join(Bucket).order_by(Epigram.last_impression_date.asc())

        if bucket_name is not None:
            q = q.filter(Bucket.name == bucket_name)
        else:
            bucket = self._get_weighted_bucket()
            if bucket is not None:
                q = q.filter_by(bucket_id = bucket)

        if self._force_random == True:
            rowCount = q.count()
            q = q.offset(int(rowCount * random.random()))

        x = q.first()

        log.debug(f"Retrieved Epigram {x}")
        if x is None:
            return self.NO_RESULTS_FOUND
        else:
            self.add_impression(x)
            return x

    def add_epigram(self, epigram):
        """ Add an epigram to the store

        Positional Arguments:
        epigram - the epigram to add

        Returns: the newly generated epigram

        """
        solo = SoloEpigramImporter(epigram)
        self.add_epigrams_via_importer(solo)

    def add_epigrams_via_importer(self, importer):
        """ Method that does stuff

            Positional Arguments:
            content (str) - the plain text content of the epigram

            Keyword Arguments:
            uuid (str) - a unique id for the item (generated if blank)

            Return:
            object (str) - desc
        """
        for e in importer.process():
            log.debug("Inserting Epigram " + str(e))
            self._session.add(e)
        self._session.commit()

    def add_impression(self, epigram):
        """ Add the impression for the epigram

            Positional Arguments:
            epigram (Epigram) - the epigram viewed
        """
        imp = Impression(epigram=epigram)
        log.debug(f"Impression tracked - {imp}")
        epigram.last_impression_date = datetime.datetime.now()
        self._session.add(imp)
        self._session.commit()

    def get_impression_count(self, bucket_name=None, unique=False):
        """
        This function will retrieve a count of the impressions.  By default,
        it will return the number of all impressions.  You can filter via
        these keyword arguments:

        * epigram_uuid (not implemented)
        * bucket_name (str) - constrain to a single bucket
        * unique (bool) - only count unique impressions
        """

        q = self._session.query(Impression).join(Bucket)

        if bucket_name is not None:
            q = q.filter(Bucket.name == bucket_name)

        return q.count()

    def get_bucket(self, bucket_name):
        """
        Retrieve the Bucket specified by the name

        :return: a Bucket object
        """
        return self._session.query(Bucket).filter(Bucket.name == bucket_name).first()

    def get_buckets(self):
        """
        Retrieve all the Buckets in the system
        """
        return self._session.query(Bucket).all()




def main():
    CONTAINER_PATH = "/var/fim/fortune.db"
    HOME_DIR = str(Path.home())+"/.fim/fortune.db"

    if os.path.exists(CONTAINER_PATH):
        # this is a container with a mounted fim dir
        db = EpigramStore(CONTAINER_PATH)
    elif os.path.exists(HOME_DIR):
        db = EpigramStore(HOME_DIR)
    else:
        # This means we are running inside of the container
        db = EpigramStore("/app/fortune.db", force_random=True)

    print(db.get_epigram().content)


if __name__ == '__main__':
    main()
