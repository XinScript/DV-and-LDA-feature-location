#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Code for generating the corpora.
"""
import os
import gensim
import logging
import re
import os
from collections import namedtuple

from common.project import GitProject
from common.error import NotGitProjectError
from common import util
from . import preprocessing

logger = logging.getLogger('pfl.corpora')


class GeneralCorpus(gensim.interfaces.CorpusABC):
    def __init__(self, project=None, id2word=None, split=True, lower=True, remove_stops=True, min_len=3, max_len=40, allow_update=True):
        self.project = project

        if not id2word:
            id2word = gensim.corpora.Dictionary()
            logger.debug('[gen] Creating new dictionary %s for %s %s',
                         id(id2word), self.__class__.__name__, id(self))

        else:
            logger.debug('[gen] Using provided dictionary %s for %s %s',
                         id(id2word), self.__class__.__name__, id(self))

        self.id2word = id2word

        self.split = split
        self.lower = split
        self.lower = lower
        self.remove_stops = remove_stops
        self.min_len = remove_stops
        self.max_len = max_len
        self.allow_update = allow_update

        if not allow_update:
            self.id2word.add_documents(self.gen())

        super().__init__()

    def config(self, **kwargs):
        if kwargs:
            for k, v in kwargs:
                if k in self.__dict__:
                    setattr(self, k, v)
                else:
                    raise AttributeError(
                        'config options "{}"not exists.'.format(k))
        else:
            return self.__dict__

    @property
    def id2word(self):
        return self._id2word

    @id2word.setter
    def id2word(self, val):
        logger.debug('[gen] Updating dictionary %s for %s %s', id(val),
                     self.__class__.__name__, id(self))
        self._id2word = val

    def preprocess(self, document):
        document = preprocessing.to_unicode(document)
        words = preprocessing.tokenize(document)

        if self.split:
            words = preprocessing.split(words)

        if self.lower:
            words = (word.lower() for word in words)

        if self.remove_stops:
            words = preprocessing.remove_stops(words, preprocessing.FOX_STOPS)
            words = preprocessing.remove_stops(
                words, preprocessing.PYTHON_RESERVED)

        words = (word for word in words if len(word) >=
                 self.min_len and len(word) <= self.max_len)
        return words

    def __iter__(self):
        """
        The function that defines a corpus.

        Iterating over the corpus must yield sparse vectors, one for each
        document.
        """
        for text, meta in self.gen():
            yield self.id2word.doc2bow(text, allow_update=self.allow_update), meta

    def __len__(self):
        return self.length  # will throw if corpus not initialized


class GitCorpus(GeneralCorpus):

    def __init__(self, project, ref, id2word=None, split=True, lower=True, remove_stops=True, min_len=3, max_len=40, allow_update=True):
        if not isinstance(project, GitProject):
            raise error.NotGitProjectError
        else:
            super().__init__(
                project=project,
                id2word=id2word,
                split=split,
                lower=lower,
                remove_stops=remove_stops,
                min_len=min_len,
                max_len=max_len,
                allow_update=allow_update)
            self.ref = ref

    def _make_meta(self, **kwargs):
        return kwargs

    def gen(self):

        length = 0

        self.project.repo.git.checkout(self.ref)

        for dirpath, dirnames, filenames in os.walk(self.project.src_path):
            dirnames[:] = [d for d in dirnames if d is not '.git']
            for filename in filenames:
                if util.is_py_file(filename):
                    path = os.path.join(dirpath, filename)
                    meta = (path[len(self.project.src_path) + 1:], 'corpus')

                    with open(path) as f:
                        document = f.read()
                        words = self.preprocess(document)
                        length += 1
                        yield words, meta

        self.length = length

        self.project.repo.git.checkout('master')
        # switch back to head


class OrderedCorpus(gensim.corpora.IndexedCorpus):
    def __init__(self, filename):
        self.fname = filename
        self.length = None
        logger.info('Creating %s corpus for file %s',
                    self.__class__.__name__, filename)

    def __iter__(self):
        with gensim.utils.smart_open(self.fname) as f:
            for line in f:
                line = gensim.utils.to_unicode(line)
                words = line.split()
                yield words[2:], (words[0], words[1])

    def __len__(self):
        if self.length == None:
            self.length = sum([1 for _ in self])

        return self.length  # will throw if corpus not initialized

    @staticmethod
    def save_corpus(fname, corpus, id2word=None, metadata=False):
        logger.info("storing corpus in Mallet format into %s" % fname)

        truncated = 0
        offsets = []
        with gensim.utils.smart_open(fname, 'w') as fout:
            enum_corpus = enumerate(corpus.gen()) if hasattr(
                corpus, 'gen') else enumerate(corpus)
            for idx, docs in enum_corpus:
                if metadata:
                    words = docs[0]
                    doc_id, doc_lang = docs[1]
                else:
                    doc_lang = '__unknown__'

                offsets.append(fout.tell())
                try:
                    fout.write('{} {} {}\n'.format(
                        doc_id, doc_lang, ' '.join(words)))
                except Exception:
                    print(docs[0][0])
                    exit()

        if truncated:
            logger.warning("Mallet format can only save vectors with "
                           "integer elements; %i float entries were truncated to integer value" %
                           truncated)

        return offsets

    def docbyoffset(self, offset):
        """
        Return the document stored at file position `offset`.
        """
        with gensim.utils.smart_open(self.fname) as f:
            f.seek(offset)
            return self.line2doc(f.readline())


class LabeledCorpus(gensim.corpora.IndexedCorpus):
    def __init__(self, filename):
        self.filename = filename
        self.length = None
        logger.info('Creating %s corpus for file %s',
                    self.__class__.__name__, filename)

    def __iter__(self):
        with gensim.utils.smart_open(self.filename) as f:
            for line in f:
                line = gensim.utils.to_unicode(line)
                words = line.split()
                yield gensim.models.doc2vec.TaggedDocument(words=words[2:], tags=["DOC__%s" % words[0]])

    def __len__(self):
        if self.length == None:
            self.length = sum([1 for _ in self])

        return self.length  # will throw if corpus not initialized

    @staticmethod
    def save_corpus(fname, corpus, id2word=None, metadata=False):
        if id2word is None:
            logger.info(
                "no word id mapping provided; initializing from corpus")
            id2word = gensim.utils.dict_from_corpus(corpus)

        logger.info("storing corpus in Mallet format into %s" % fname)

        truncated = 0
        offsets = []
        with gensim.utils.smart_open(fname, 'w') as fout:
            enum_corpus = enumerate(corpus.gen()) if hasattr(
                corpus, gen) else enumerate(corpus)
            for doc_id, doc in enum_corpus:
                if metadata:
                    doc_id, doc_lang = doc[1]
                    doc = doc[0]
                else:
                    doc_lang = '__unknown__'

                if id2word:
                    words = []
                    for wordid, value in doc:
                        if abs(int(value) - value) > 1e-6:
                            truncated += 1
                        words.extend([gensim.utils.to_unicode(
                            id2word[wordid])] * int(value))
                else:
                    words = [str(x) for x, y in doc]

                offsets.append(fout.tell())
                fout.write('{} {} {}\n'.format(
                    doc_id, doc_lang, ' '.join(words)))

        if truncated:
            logger.warning("Mallet format can only save vectors with "
                           "integer elements; %i float entries were truncated to integer value" %
                           truncated)

        return offsets

    def docbyoffset(self, offset):
        """
        Return the document stored at file position `offset`.
        """
        with gensim.utils.smart_open(self.fname) as f:
            f.seek(offset)
            return self.line2doc(f.readline())
