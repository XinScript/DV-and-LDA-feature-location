from numpy import mean
import csv
import os
import logging
import multiprocessing
from gensim.corpora import Dictionary, MalletCorpus
from gensim.models import Doc2Vec
from collections import defaultdict


from corpus.corpora import LabeledCorpus,OrderedCorpus,GeneralCorpus,GitCorpus
from common import util
from common import CONFIG

logger = logging.getLogger('plt.main')

logger.setLevel(CONFIG.LOG_LEVEL)

class Doc2VecModel():
    def __init__(self,project,level,num_topics=500,min_count=1):
        self.project = project
        self.num_topics = num_topics
        self.min_count = min_count
        self.level = level

    def create_query(self):

        base_path = self.project.path_dict['base']

        corpus_fname = os.path.join(base_path, 'queries' + CONFIG.CORPUS_EXT)

        if os.path.exists(corpus_fname):
            corpus = OrderedCorpus(corpus_fname)

        else:
            queries = []
            pp = GeneralCorpus()
            ids = self.project.load_ids()
            for idx in ids:
                with open(os.path.join(self.project.path_dict['query'], idx + '.txt')) as f:
                    content = f.read()

                doc_vec = list(pp.preprocess(content))
                queries.append((doc_vec, (idx, 'query')))

            OrderedCorpus.serialize(corpus_fname, queries, metadata=True)
            corpus =  OrderedCorpus(corpus_fname)
        return corpus
        

    def create_corpus(self):

        base_path = self.project.path_dict['base']

        corpus_fname = os.path.join(base_path, 'code' + CONFIG.CORPUS_EXT)

        if os.path.exists(corpus_fname):
            corpus = OrderedCorpus(corpus_fname)

        else:
            corpus = GitCorpus(self.project, self.project.release_interval[1])

            OrderedCorpus.serialize(
                corpus_fname, corpus, metadata=True)

            corpus = OrderedCorpus(corpus_fname)

        return corpus

    def create_model(self, corpus):

        base_path = self.project.path_dict['base']

        model_fname = os.path.join(base_path, 'code' + CONFIG.MODEL_EXT)

        corpus = LabeledCorpus(corpus.fname)

        if not os.path.exists(model_fname):
            model = Doc2Vec(corpus, min_count=self.min_count,vector_size=self.num_topics, workers=multiprocessing.cpu_count(),)
            model.save(model_fname)
        else:
            model = Doc2Vec.load(model_fname)

        return model

    def get_topics(self,model, corpus):
        topic_arr = []
        for doc, meta in corpus:
            try:
                topics = model.docvecs['DOC__' + meta[0]]
            except KeyError:
                topics = model.infer_vector(doc)
            topic_arr.append((meta[0], topics))
        return topic_arr

    def predict(self,query_topic, doc_topic, distance_measure=util.cosine_distance):
        logger.info('Getting ranks between %d query topics and %d doc topics',
                    len(query_topic), len(doc_topic))
        goldsets = self.project.load_goldsets(self.level)
        ranks = {}
        for qid, query in query_topic:
            q_dist = []

            for fpath, doc in doc_topic:
                distance = distance_measure(query, doc)
                q_dist.append((distance, fpath))

            q_dist.sort()
            if qid in goldsets:
                goldset = goldsets[qid]
                ranks[qid] = self.get_rels(goldset, q_dist)

            else:
                logger.info("Could not find goldset for query %s", qid)

        logger.info('Returning %d ranks', len(ranks))
        return ranks

    def get_rels(self,goldset, q_dist):
        rels = []
        for idx, rank in enumerate(q_dist):
            distance, fpath = rank
            if fpath in goldset:
                rels.append((idx + 1, distance, fpath))

        return rels

    def write_ranks(self, ranks, name):

        fname = os.path.join(self.project.path_dict['base'], name + CONFIG.RANK_EXT)
        if not os.path.exists(fname):
            with open(fname, 'w') as f:
                writer = csv.writer(f)
                writer.writerow(['id', 'rank', 'distance', 'item'])
                for qid, rank in ranks.items():
                    for idx, distance, fpath in rank:
                        writer.writerow([qid, idx, distance, fpath])
        logger.info('Have written ranks to disk:{}'.format(fname))

    def read_ranks(self, name):
        ranks = defaultdict(list)
        fname = os.path.join(self.project.path_dict['base'], name + CONFIG.RANK_EXT)
        if os.path.exists(fname):
            with open(fname, 'r') as f:
                reader = csv.reader(f)
                next(reader)
                for qid, idx, dist, d_path in reader:
                    ranks[qid].append((int(idx), float(dist), d_path))
            logger.info('Successfully loaded previous ranks from:{}'.format(fname))
        return ranks

    def get_ranks(self):
        name = '.'.join(['basic', self.level])
        ranks = self.read_ranks(name)
        if not ranks:
            queires = self.create_query()
            corpus = self.create_corpus()
            model = self.create_model(corpus)
            query_topics = self.get_topics(model,queires)
            corpus_topics = self.get_topics(model,corpus)
            ranks = self.predict(query_topics,corpus_topics)
            self.write_ranks(ranks,name)
        return ranks


class WordSumModel(Doc2VecModel):

    def __init__(self, project, level, num_topics=500, min_count=1):
        super().__init__(project, level, num_topics, min_count)

    def predict(self, model, queries, corpus, by_ids=None):

        queries = LabeledCorpus(queries.fname)
        corpus = LabeledCorpus(corpus.fname)
        goldsets = self.project.load_goldsets(self.level)
        logger.info('Getting ranks for Doc2Vec model')

        ranks = dict()
        for query in queries:
            q_dist = list()

            qid = query.tags[0][5:]
            if by_ids is not None and qid not in by_ids:
                logger.info('skipping')
                continue
            logger.info(qid)

            qwords = list(filter(lambda x: x in model.wv.vocab, query.words))

            for doc in corpus:
                d_path = doc.tags[0].replace('DOC__', '')
                dwords = list(filter(lambda x: x in model.wv.vocab, doc.words))

                if len(dwords) and len(qwords):
                    sim = model.n_similarity(qwords, dwords)
                    q_dist.append((1.0 - sim, d_path))
            q_dist.sort()
            if qid in goldsets:
                goldset = goldsets[qid]
                ranks[qid] = self.get_rels(goldset, q_dist)
            else:
                logger.info("Could not find goldset for query %s", qid)

        return ranks

    def get_ranks(self):
        name = '.'.join(['sum', self.level])
        ranks = self.read_ranks(name)
        if not ranks:
            queires = self.create_query()
            corpus = self.create_corpus()
            model = self.create_model(corpus)
            print('start predict')
            ranks = self.predict(model, queires, corpus)
            self.write_ranks(ranks, name)
        return ranks
