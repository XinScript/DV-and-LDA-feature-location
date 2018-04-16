import csv
import os
import logging
import Project
import Corpora
import Util
import Config
from Goldset.CommitGoldsetGenerator import CommitGoldsetGenerator
from gensim.corpora import Dictionary, MalletCorpus
from gensim.models import Doc2Vec
from collections import defaultdict

logger = logging.getLogger('plt.main')

logger.setLevel(Config.LOG_LEVEL)


def create_query(project):

    base_path = project.path_dict['base']

    corpus_fname = os.path.join(base_path, 'queries' + Config.CORPUS_EXT)

    if os.path.exists(corpus_fname):
        return Corpora.OrderedCorpus(corpus_fname)
    else:
        queries = []
        pp = Corpora.GeneralCorpus()
        ids = project.load_ids()
        for idx in ids:
            with open(os.path.join(project.path_dict['query'], idx + '.txt')) as f:
                content = f.read()

            doc_vec = list(pp.preprocess(content))
            queries.append((doc_vec, (idx, 'query')))

        Corpora.OrderedCorpus.serialize(corpus_fname, queries, metadata=True)

        return Corpora.OrderedCorpus(corpus_fname)


def create_corpus(project):

    base_path = project.path_dict['base']

    id2word_fname = os.path.join(base_path, 'code' + Config.ID2WORD_EXT)

    corpus_fname = os.path.join(base_path, 'code' + Config.CORPUS_EXT)

    if os.path.exists(corpus_fname):
        corpus = MalletCorpus(
            corpus_fname, id2word=Dictionary.load(id2word_fname), metadata=True)
    else:
        corpus = Corpora.GitCorpus(project, project.release_interval[1])

        MalletCorpus.serialize(corpus_fname, corpus,
                               id2word=corpus.id2word, metadata=True)

        corpus.id2word.save(id2word_fname)

        corpus = MalletCorpus(
            corpus_fname, id2word=corpus.id2word, metadata=True)

    return corpus


def create_doc2vec_model(project, corpus, num_topics=500, min_count=1):

    base_path = project.path_dict['base']

    model_fname = os.path.join(base_path, 'code' + Config.MODEL_EXT)

    corpus = Corpora.LabeledCorpus(corpus.fname)

    if not os.path.exists(model_fname):
        model = Doc2Vec(corpus, min_count=min_count, vector_size=num_topics)
        model.save(model_fname)
    else:
        model = Doc2Vec.load(model_fname)

    return model


def get_topics(model, corpus):
    topic_arr = []
    for doc, meta in corpus:
        try:
            topics = model.docvecs['DOC__' + meta[0]]
        except KeyError:
            topics = model.infer_vector(doc)
        topic_arr.append((meta, topics))
    return topic_arr


def get_rank_basic(goldsets, query_topic, doc_topic, distance_measure=Util.cosine_distance):
    logger.info('Getting ranks between %d query topics and %d doc topics',
                len(query_topic), len(doc_topic))

    ranks = {}
    for q_meta, query in query_topic:
        qid, _ = q_meta
        q_dist = []

        for d_meta, doc in doc_topic:
            fname, _ = d_meta
            distance = distance_measure(query, doc)
            q_dist.append((distance, fname))

        q_dist.sort()
        if qid in goldsets:
            goldset = goldsets[qid]
            ranks[qid] = get_rels(goldset, q_dist)

        else:
            logger.info("Could not find goldset for query %s", qid)

    logger.info('Returning %d ranks', len(ranks))
    return ranks


def get_rank_sum(model, queries, goldsets, corpus, by_ids=None):
    queries = Corpora.LabeledCorpus(queries.fname)
    corpus = Corpora.LabeledCorpus(corpus.fname)
    logger.info('Getting ranks for Doc2Vec model')

    ranks = dict()
    for query in queries:
        q_dist = list()

        qid = query.tags[0][5:]
        if by_ids is not None and qid not in by_ids:
            logger.info('skipping')
            continue

        qwords = list(filter(lambda x: x in model.wv.vocab, query.words))

        for doc in corpus:
            d_path = doc.tags[0].replace('DOC__', '')
            dwords = list(filter(lambda x: x in model.wv.vocab, doc.words))

            if len(dwords) and len(qwords):
                # best thing to do without inference
                sim = model.n_similarity(qwords, dwords)
                q_dist.append((1.0 - sim, d_path))

        q_dist.sort()
        if qid in goldsets:
            goldset = goldsets[qid]
            ranks[qid] = get_rels(goldset, q_dist)
        else:
            logger.info("Could not find goldset for query %s", qid)

    return ranks


def get_rels(goldset, q_dist):
    rels = []

    for idx, rank in enumerate(q_dist):
        distance, fname = rank
        if fname in goldset:
            rels.append((idx + 1, distance, fname))

    return rels


def write_ranks(project, kind, ranks):
    fname = os.path.join(project.path_dict['base'], kind + Config.RANK_EXT)
    if not os.path.exists(fname):
        with open(fname, 'w') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'rank', 'distance', 'item'])
            for qid, rank in ranks.items():
                for idx, distance, f_name in rank:
                    writer.writerow([qid, idx, distance, f_name])


def read_ranks(project, kind):
    ranks = defaultdict(list)
    fname = os.path.join(project.path_dict['base'], kind + Config.RANK_EXT)
    if os.path.exists(fname):
        with open(fname, 'w') as f:
            reader = csv.reader(f)
            next(reader)
            for g_id, idx, dist, d_path in reader:
                ranks[g_id].append((int(idx), float(dist), d_path))
    logger.info('Successfully loaded previous ranks.')
    return ranks


def get_frms(ranks):
    logger.info('Getting FRMS for %d ranks', len(ranks))
    frms = list()

    for r_id, rank in ranks.items():
        if rank:
            idx, dist, meta = rank[0]
            frms.append((idx, r_id, meta))

    logger.info('Returning %d FRMS', len(frms))
    return frms


def generate_data(name, gen_rule, src_path, version, issue_keywords):

    project = Project.LocalGitProject(
        name, gen_rule, src_path, version, issue_keywords)

    generator = CommitGoldsetGenerator(project)

    generator.generate()

    logger.info('goldset data was successfully generated.')

    project.save()

    logger.info('goldset data was saved.')


def run(project, kind, level):

    ranks = read_ranks(project, kind)
    if not ranks:
        queries = create_query(project)
        corpus = create_corpus(project)
        model = create_doc2vec_model(project, corpus)
        goldsets = project.load_goldsets(level)
        if kind == 'basic':
            query_topics = get_topics(model, queries)
            corpus_topics = get_topics(model, corpus)
            ranks = get_rank_basic(goldsets, query_topics, corpus_topics)
        elif kind == 'sum':
            ranks = get_rank_sum(model, queries, goldsets, corpus)
        write_ranks(project, kind, ranks)

    return get_frms(ranks)


if __name__ == '__main__':
    # generate_data('sage', 'by_commit', '../sources/sage', ('5.0', '5.1'), ['trac'])
    project = Project.GitProject.load('sage', ('5.0', '5.1'))
    run(project, 'basic', 'class')
