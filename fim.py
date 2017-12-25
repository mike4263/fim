#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uuid as uuid_stdlib

""" fim - fortune improved """


class ContentSource():
    """ Base class for all of the content type """

    def __init__(self, uri):
        pass

    def process(self):
        """ yields Epigrams """
        yield None


class FortuneFile(ContentSource):
    def __init__(self, uri):
        pass


class Epigram():
    """ This is the basic unit of content in fim.

        An epigram is a brief, interesting, memorable, and sometimes surprising
        or satirical statement. The word is derived from the Greek: ἐπίγραμμα
        epigramma "inscription" from ἐπιγράφειν epigraphein "to write on, to
        inscribe", and the literary device has been employed for over two
        millennia.

        BTW 'epigram' was directly lifted from the fortune man page *shrugs*.

        Epigram contain the following items:
            - content - plain text content (5k limit characters)
            - category - Epigram belong to a single Category
            - uuid - unique 128 byte character string.  This is the epigram
                        primary key

        These field names directly map to the EPIGRAM table in the DB.

    """

    def __init__(self, content, category, uuid=None):
        """ Basic constructor for the Epigram

            Method Argument:
                content (str) - the plain text content of the epigram
                category (str) - the category key (optional)

            Optional Params:
                uuid (str) - a unique id for the item (generated if blank)
        """
        self._content = content
        self._category = category

        if (uuid is None):
            self._uuid = uuid_stdlib.uuid4
        else:
            self._uuid = uuid

    @property
    def content(self):
        return self._content

    @property
    def category(self):
        return self._category

    @property
    def uuid(self):
        return self._uuid


def main():
    pass


if __name__ == '__main__':
    main()
