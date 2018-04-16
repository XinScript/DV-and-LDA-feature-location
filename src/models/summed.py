import os
import corpora
import util
import config

logger = logging.getLogger('plt.main')

logger.setLevel(config.LOG_LEVEL)



def create_query(project):
    base_path = os.path.join(project.path_dict['base'], 'summed')

    os.makedirs(base_path) if not os.path.exists(base_path) else None

    corpus_fname = os.path.join(
        base_path, 'bow.queries' + config.CORPUS_EXT)
    id2word_fname = os.path.join(
        base_path, 'bow.queries' + config.ID2WORD_EXT)

    if os.path.exists(corpus_fname):
        return corpora.MalletCorpus(corpus_fname, id2word=Dictionary.load(id2word_fname))
    else:
        queries = []
        pp = corpora.GeneralCorpus()
        id2word = Dictionary()
        ids = project.load_ids()
        for idx in ids:
            with open(os.path.join(project.path_dict['query'], idx + '.txt')) as f:
                content = f.read()

            doc_vec = id2word.doc2bow(
                pp.preprocess(content), allow_update=True)

            queries.append((doc_vec, (idx, 'query')))

        MalletCorpus.serialize(corpus_fname, queries,
                                id2word=id2word, metadata=True)

        id2word.save(id2word_fname)

        return MalletCorpus(corpus_fname, id2word=id2word)


def create_corpus(project):

    base_path = os.path.join(project.path_dict['base'], 'summed')

    os.makedirs(base_path) if not os.path.exists(base_path) else None

    corpus_fname = os.path.join(base_path, 'bow.code' + config.CORPUS_EXT)
    id2word_fname = os.path.join(
        base_path, 'bow.code' + config.ID2WORD_EXT)

    if os.path.exists(corpus_fname):

        corpus = MalletCorpus(
            corpus_fname, id2word=Dictionary.load(id2word_fname))

    else:

        corpus = corpora.GitCorpus(project, project.release_interval[1])

        MalletCorpus.serialize(corpus_fname, corpus,
                                id2word=corpus.id2word, metadata=True)

        corpus.id2word.save(id2word_fname)

        corpus = corpora.OrderedCorpus(
            corpus_fname, id2word=corpus.id2word)

    return corpus
