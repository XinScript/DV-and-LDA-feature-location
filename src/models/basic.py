from gensim.corpora import MalletCorpus

import os
import corpora
import config


def create_query(project):

    base_path = os.path.join(project.path_dict['base'], 'summed')

    os.makedirs(base_path) if not os.path.exists(base_path) else None

    corpus_fname = os.path.join(base_path, 'queries' + config.CORPUS_EXT)

    if os.path.exists(corpus_fname):
        return corpora.OrderedCorpus(corpus_fname)

    else:
        queries = []
        pp = corpora.GeneralCorpus()
        ids = project.load_ids()
        for idx in ids:
            with open(os.path.join(project.path_dict['query'], idx + '.txt')) as f:
                content = f.read()

            doc_vec = list(pp.preprocess(content))
            queries.append((doc_vec, (idx, 'query')))

        corpora.OrderedCorpus.serialize(corpus_fname, queries, metadata=True)

        return corpora.OrderedCorpus(corpus_fname)


def create_corpus(project):

    base_path = os.path.join(project.path_dict['base'], 'summed')

    os.makedirs(base_path) if not os.path.exists(base_path) else None

    base_path = project.path_dict['base']

    corpus_fname = os.path.join(base_path, 'code' + config.CORPUS_EXT)

    if os.path.exists(corpus_fname):
        corpus = corpora.OrderedCorpus(corpus_fname)

    else:
        corpus = corpora.GitCorpus(project, project.release_interval[1])

        corpora.OrderedCorpus.serialize(corpus_fname, corpus, metadata=True)

        corpus = corpora.OrderedCorpus(corpus_fname)


    return corpus
