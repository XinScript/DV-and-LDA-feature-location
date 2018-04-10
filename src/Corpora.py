#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Code for generating the corpora.
"""
import os
import Util
from Error import *
import Project
import Config

from collections import namedtuple

import re
import os

import gensim
import Preprocessing

import logging
logger = logging.getLogger('pfl.corpora')

class GeneralCorpus(gensim.interfaces.CorpusABC):
    def __init__(self, project=None, id2word=None, split=True, lower=True, remove_stops=True, min_len=3, max_len=40, allow_update=True):
        self.project = project

        if id2word is None:
            id2word = gensim.corpora.Dictionary()
            logger.debug('[gen] Creating new dictionary %s for %s %s',
                         id(id2word), self.__class__.__name__, id(self))

        else:
            logger.debug('[gen] Using provided dictionary %s for %s %s',
                         id(id2word), self.__class__.__name__, id(self))

        self.id2word = id2word

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
                    raise AttributeError('config options "{}"not exists.'.format(k))
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
        document = Preprocessing.to_unicode(document)
        words = Preprocessing.tokenize(document)

        if self.split:
            words = Preprocessing.split(words)

        if self.lower:
            words = (word.lower() for word in words)

        if self.remove_stops:
            words = Preprocessing.remove_stops(words, Preprocessing.FOX_STOPS)
            words = Preprocessing.remove_stops(words, Preprocessing.PYTHON_RESERVED)

        words = (word for word in words if len(word) >=
                 self.min_len and len(word) <= self.max_len)
        return words

    def __iter__(self):
        """
        The function that defines a corpus.

        Iterating over the corpus must yield sparse vectors, one for each
        document.
        """
        for text,meta in self.gen():
            yield self.id2word.doc2bow(text, allow_update=self.allow_update),meta

    def __len__(self):
        return self.length  # will throw if corpus not initialized


class GitCorpus(GeneralCorpus):
    
    def __init__(self, project, ref, id2word=None, split=True, lower=True, remove_stops=True, min_len=3, max_len=40, allow_update=True):
        if not isinstance(project, Project.GitProject):
            raise NotGitProjectError
        else:
            self.ref = ref

            super().__init__(project=project, id2word=id2word)


    def _make_meta(self,**kwargs):
        return kwargs

    def gen(self):

        length = 0

        head = self.project.repo.head.commit

        self.project.repo.git.checkout(self.ref)

        for dirpath, dirnames, filenames in os.walk(self.project.src_path):
            dirnames[:] = [d for d in dirnames if d is not '.git']
            for filename in filenames:
                if Util.is_py_file(filename):
                    path = os.path.join(dirpath, filename)
                    meta = self._make_meta(path=path[len(self.project.src_path):])

                    with open(filename) as f:
                        document = f.read()
                        words = self.preprocess(document)
                        length += 1
                        yield words, meta

        self.length = length

        self.project.repo.git.checkout(head)
        # switch back to head
