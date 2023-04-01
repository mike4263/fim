#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# We have to parse command line options initially to start the prompt
# which will prevent the slow down on startup

import argparse
def setup_argparse():
    parent_parser = argparse.ArgumentParser(prog='fim.py')

    parent_parser.add_argument('--gpt', help="Query ChatGPT to get context about this epigram",
                               action="store_true")
    parent_parser.add_argument('--bucket', help="constrain searches to this bucket")
    parent_parser.add_argument('--openai', nargs=1, help="Your OpenAI API Token")
    parent_parser.add_argument('--db', help="path to db file")
    parent_parser.add_argument('--display_bucket', '-d', help="display the name of the bucket",
                               action="store_true")

    subparsers = parent_parser.add_subparsers(dest='command')

    child_parser = argparse.ArgumentParser(add_help=False)
    child_parser.add_argument('--gpt', help="Query ChatGPT to get context about this epigram",
                              action="store_true")

    import_parser = subparsers.add_parser('import')
    import_parser.add_argument('source_type', choices=['fortune'])
    import_parser.add_argument('path', help='path to the file or directory to import', metavar='PATH')

    context_parser = subparsers.add_parser('context')
    context_parser.add_argument('--openai', nargs=1, help="Your OpenAI API Token")
    # context_parser.add_argument('context_type', choices=['gpt','dalle'])

    save_parser = subparsers.add_parser('save')
    chat_parser = subparsers.add_parser('chat')
    bucket_parser = subparsers.add_parser('buckets')
    rcfile_parser = subparsers.add_parser('rcfile')
    return parent_parser.parse_args()


args = setup_argparse()


if args.command == "rcfile" or args.command == "buckets":
    # exclude output so STDOUT pipe works properly
    pass
elif args.command == "content" or args.command == "chat":
    print("\x1b[1m[fim]\x1b[0m restoring an epigram")
else:
    print("\x1b[1m[fim]\x1b[0m selecting an epigram")

import uuid as uuid_stdlib
import logging
import re
import os
import glob
import random
import sys
import secrets
from pathlib import Path
# from prompt_toolkit import print_formatted_text
import toml as toml
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.sql.expression import func
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    create_engine, text
)
import datetime
from prompt_toolkit import prompt
import openai
import time

from toml import TomlDecodeError

""" fim - fortune improved """

log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler(sys.stdout))
# logging.basicConfig(level=logging.ERROR)
log.setLevel(logging.INFO)

# Configuration File Constants
MAIN = 'main'
BUCKET = 'buckets'
OPENAI_TOKEN = 'openai_token'

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
    item_weight = Column(Integer, default=1)

    #    def __init__(self, name, **kwargs):
    #        super()
    #        self.name = name
    #        self.bucket_id = mydefault()

    def __str__(self):
        return f"<Bucket bucket_id={self.bucket_id}, name={self.name}>"

    def public(self):
        pass


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
    gpt_completion = Column(String)

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

    def public(self):
        """ This is necessary to fix a pylint error """
        pass


class Impression(Base):
    """ Track the views for each epigram """
    __tablename__ = 'impression'
    impression_id = Column(Integer, primary_key=True)
    bucket_id = Column(Integer, ForeignKey("bucket.bucket_id"))
    bucket = relationship("Bucket", backref="impression")
    epigram_uuid = Column(String, ForeignKey("epigram.epigram_uuid"))
    epigram = relationship("Epigram", backref="impression")
    impression_date = Column(String)
    saved = Column(Boolean)
    gpt_completion = Column(String)

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

    def public(self):
        """ This is necessary to fix a pylint error """
        pass


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
    def process_fortune_file(cls, file_contents):
        delimiter = re.compile(r'^%$')
        e = ''
        for file in file_contents.split("\n"):
            if re.search(delimiter, file):
                yield e.rstrip()
                e = ""
            else:
                e += file + "\n"


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
    SQL_DIR = "sql"

    def __init__(self, filename):
        """ Construct the store (connect to db, optionally retrieve all rows)

            Positional Arguments:
            filename (str) - the path to the SQLite database

            Optional Params:
            force_random (Bool)  -
        """
        self._filename = filename

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
            raise RuntimeError("FileNotFound: " + uri)

        sql_files.sort()

        for fname in sql_files:
            with open(fname, 'r') as sql_text:
                log.debug(f"Processing %s file" % (fname))
                self._execute_sql(sql_text.read())

    def _execute_sql(self, sql_text):
        with self._engine.connect() as conn:
            conn.exec_driver_sql(sql_text)
            # onn self._engine.execute(sql_text)

    def _get_weighted_bucket(self):
        """
        Using the patented BucketSort(TM) Technology this queries the impressions_calculated
        table.  This factors in the relative weights of each bucket compared to its actual
        impressions.  Buckets that have exceeded their allowable view percentage are excluded
        from selection.

        The selection itself is using the random.choice() method based on the probabilities

        :return: the bucket_id to use in the get epigram query
        """

        rs = []

        with self._engine.connect() as conn:
            rs = conn.exec_driver_sql("""
            select bucket_id, effective_impression_percentage from impressions_calculated 
             where impression_delta >= 0
            """).all()

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

    def get_epigram_impression(self, uuid=None, internal_fetch_ratio=0.1, force_random=True, bucket_name=None,
                               bucket=None):
        """ Get a epigram considering filter criteria and weight rules

            Keyword Arguments:
            uuid (str) - return this specific epigram
            internal_fetch_ratio (int) - see the README.md for info on the
                                                  weighting algorithm
            bucket_name (str) - the natural key for the buckets
            bucket - a bucket object

            Return:
            An Epigram (obviously)
        """
        q = self._session.query(Epigram).join(Bucket) \
            .filter(func.length(Epigram.content) < 300) \
            .order_by(Epigram.last_impression_date.asc())

        if bucket_name is not None:
            q = q.filter(Bucket.name == bucket_name)
        else:
            bucket = self._get_weighted_bucket()
            if bucket is not None:
                q = q.filter_by(bucket_id=bucket)

        if force_random == True:
            rowCount = q.count() * internal_fetch_ratio * random.random()
            log.debug(f"offsetting by %s rows" % rowCount)
            q = q.offset(int(rowCount))

        # x = q.first()
        x = q.first()

        log.debug(f"Retrieved Epigram {x}")
        if x is None:
            return Impression(epigram=self.NO_RESULTS_FOUND)

        imp = self.add_impression(x)
        return imp

    def get_last_impression(self):
        q = self._session.query(Impression).join(Epigram) \
            .order_by(Epigram.last_impression_date.desc())
        return q.first()

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
        return imp

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

    def get_bucket_info(self):
        bucket_info_list = []
        buckets = self._session.query(Bucket).all()
        for bucket in buckets:
            effective_percentage = self.calculate_effective_percentage(bucket)
            bucket_info_list.append({
                'name': bucket.name,
                'weight': bucket.item_weight,
                'effective_percentage': effective_percentage
            })
        bucket_info_list.sort(key=lambda x: x['effective_percentage'], reverse=True)
        return bucket_info_list

    def calculate_effective_percentage(self, bucket):
        # Query the impressions_calculated view to get the exoected percentage for a given bucket_id
        result = self._session.execute(text(
            f"SELECT expected_weighted_percentage FROM impressions_calculated WHERE bucket_id = %s" % bucket.bucket_id
        )
        ).scalar()
        return result if result else 0

    def update_bucket_weight(self, bucket_name, new_weight):
        """
        Update the item_weight of a bucket with the given bucket_name.

        :param bucket_name: The name of the bucket to update.
        :param new_weight: The new item_weight for the bucket.
        """
        bucket = self._session.query(Bucket).filter(Bucket.name == bucket_name).first()
        if bucket:
            bucket.item_weight = new_weight
            self._session.commit()
        else:
            raise ValueError(f"Bucket not found with name: {bucket_name}")

    def commit(self):
        return self._session.commit()


class FIM():
    _db = None

    def __init__(self, db_name="fim.db", path="/var/fim", **kwargs):
        if not os.path.exists(path):
            os.makedirs(path)

        self._db = EpigramStore(os.path.join(path, db_name))

    def import_fortune(self, path):
        self._db.add_epigrams_via_importer(
            FortuneFileImporter(path))
        log.info("Import complete")

    def get_epigram_impression(self, bucket_name):
        return self._db.get_epigram_impression(bucket_name=bucket_name)

    def get_last_impression(self):
        return self._db.get_last_impression()

    def save_gpt_output(self, impression: Impression, output):
        impression.gpt_completion = output
        self.commit_db()

    def commit_db(self):
        self._db.commit()

    def display_bucket_info(self):
        print("{:<15} {:<10} {:<20}".format("BUCKET", "WEIGHT", "RATIO"))
        print("-" * 45)
        for bucket_info in self._db.get_bucket_info():
            bucket_name = bucket_info['name']
            weight = bucket_info['weight']
            effective_percentage = bucket_info['effective_percentage']
            print("{:<15} {:<10} {:<20.3f}".format(bucket_name, weight, effective_percentage))

    def display_bucket_rc(self, openai, config):

        print("[main]")
        if openai:
            api_key = openai
        else:
            api_key = "Get your key https://platform.openai.com/account/api-keys"

        print(f"openai = \"%s\"" % api_key)

        print()

        print("[buckets]")
        bucket_info_list = self._db.get_bucket_info()
        bucket_info_list.sort(key=lambda x: x['name'])
        for bucket_info in bucket_info_list:
            bucket_name = bucket_info['name']
            weight = bucket_info['weight']
            print("{:<15} = {:<10} ".format(bucket_name, weight))

    def update_bucket_weight(self, bucket_name, new_weight):
        self._db.update_bucket_weight(bucket_name, new_weight)


class OpenAI():
    EXPLAIN_PROMPT = """
    This output is from an application that is designed to display pithy, insightful, meaningful epigrams to users.  
    Please explain this epigram, including any information about individuals referenced within, explaining the humor, 
    identifying the origin.  If you are aware of any significant references to popular culture, please explain otherwise
     stay silent. 
    """

    MODEL = 'gpt-3.5-turbo'

    # MODEL = 'gpt-4'

    def __init__(self, api_key):
        openai.api_key = api_key
        self.messages = []

    def complete_epigram(self, epigram):
        self.messages.append({"role": "user", "content": self.EXPLAIN_PROMPT})
        self.messages.append({"role": "user", "content": "The epigram comes from a file called " + epigram.bucket.name})
        self.messages.append({"role": "user", "content": "You identify as FIM - fortune improved"})
        self.messages.append({"role": "user", "content": epigram.content})

        return self._send_message()

    def chat(self, chat_prompt):
        self.messages.append({"role": "user", "content": chat_prompt})
        return self._send_message()

    def _send_message(self):
        print("\x1b[1m[fim]\x1b[0m invoking ChatGPT..")
        completion = openai.ChatCompletion.create(model=self.MODEL, messages=self.messages)

        print("\x1b[1A\x1b[2K\x1b[G", end="")
        log.debug(completion)
        choices = completion.choices[0]
        # self.messages.append(completion.choices[0])
        return completion.choices[0].message.content


def context(openai_api, imp, chat=False):
    gpt = OpenAI(openai_api)
    output = gpt.complete_epigram(imp.epigram)
    print(fmt(output))
    print()

    if chat:
        print("\x1b[1m[fim]\x1b[0m chat session enter 'quit' to leave, CTRL+Enter to send your message")

    while chat:
        input_prompt = prompt('Enter prompt: ', multiline=True, vi_mode=False)

        if input_prompt == "quit":
            chat = False
        else:
            print()
            print(fmt(gpt.chat(input_prompt)))
            print()

    return output


def fmt(text, width=78, indent=2):
    lines = text.split('\n')

    formatted_lines = []
    current_line = ''
    for line in lines:
        words = line.split()
        for word in words:
            if len(current_line) + len(word) + 1 <= width - indent:
                current_line += word + ' '
            else:
                formatted_lines.append(' ' * indent + " > " + current_line.rstrip())
                current_line = word + ' '
        if current_line:
            formatted_lines.append(' ' * indent + " > " + current_line.rstrip())
            current_line = ''

    return '\n'.join(formatted_lines)


def print_epigram(epigram, display_bucket=False):
    print()
    print(epigram.content)
    print()

    if display_bucket:
        print("\x1b[1m[fim]\x1b[0m bucket: %s" % (epigram.bucket.name))

def main():
    fimrc = str(Path.home()) + "/.fimrc"
    if os.path.exists(fimrc):
        with open(fimrc) as f:
            try:
                config = toml.load(f)
            except TomlDecodeError as e:
                log.error("Invalid Configuration File: %s (line %d column %d char %d)"
                          % (e.msg, e.lineno, e.colno, e.pos))
                exit(1)

    # determine OpenAI token
    try:
        openai_env = os.environ['OPENAI_ACCESS_TOKEN']
    except KeyError:
        openai_env = None

    if args.openai is not None:
        openai_api = args.openai[0]
    elif openai_env is not None:
        openai_api = openai_env
    elif os.path.exists(fimrc):
        try:
            openai_api = config[MAIN][OPENAI_TOKEN]
        except KeyError:
            openai_api = None
    else:
        openai_api = None

    if openai_api:
        log.debug("OpenAI Token : " + openai_api)

    # Determine Home directory
    home_dir = str(Path.home()) + "/.fim/"
    container_path = "/var/fim/"

    if args.db is not None:
        path = args.db
    elif os.path.exists(container_path):
        path = container_path
    else:
        path = home_dir

    log.debug(path)
    fim = FIM(path=path)

    if os.path.exists(fimrc) and BUCKET in config:
        for bucket in config[BUCKET]:
            weight = config[BUCKET][bucket]
            try:
                fim.update_bucket_weight(bucket, weight)
                log.debug(f"Updating %s with %d weight" % (bucket, weight))
            except RuntimeError as e:
                log.error(f"Unable to %s with %d weight" % (bucket, weight))
                log.error(e)

    if args.command != "rcfile" or arg.commands != "buckets":
        print("\x1b[1A\x1b[2K\x1b[G", end="")

    if args.command == "import":
        if args.source_type == 'fortune':
            fim.import_fortune(args.path)
        else:
            raise NotImplementedError
    elif args.command == "context" or args.command == "chat":
        imp = fim.get_last_impression()
        print_epigram(imp.epigram)
        chat_mode = True if args.command == "chat" else False
        output = context(openai_api, imp, chat=chat_mode)
        fim.save_gpt_output(imp, output)
    elif args.command == "save":
        imp = fim.get_last_impression()
        imp.saved = True
        fim.commit_db()

        print_epigram(imp.epigram)

        print("\x1b[1m[fim]\x1b[0m saved")

    elif args.command == "buckets":
        fim.display_bucket_info()

    elif args.command == "rcfile":
        fim.display_bucket_rc(openai_api, config)
    else:
        imp = fim.get_epigram_impression(args.bucket)
        print_epigram(imp.epigram, display_bucket=args.display_bucket)
        if args.gpt:
            output = context(openai_api, imp)
            fim.save_gpt_output(imp, output)


if __name__ == '__main__':
    main()
