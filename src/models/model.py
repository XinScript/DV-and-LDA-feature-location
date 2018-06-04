from numpy import mean
import csv
import os
import logging
import multiprocessing
from gensim.corpora import Dictionary, MalletCorpus
from gensim.models import Doc2Vec, LdaModel
from gensim.matutils import sparse2full
from collections import defaultdict
from common.error import InstantiationError

from corpus.corpora import LabeledCorpus, OrderedCorpus, GeneralCorpus, GitCorpus
from common import util
from common import CONFIG


# Abstract class cannot be instantiated 
class General():
    
    def __init__(self, project, goldset_level):
        self.project = project
        self.logger = util.get_logger('model_gen_rank',project)
        self.goldset_level = goldset_level
        if self.__class__ == General:
            raise InstantiationError

    def create_query(self):

        base_path = self.project.path_dict['base']

        corpus_fname = os.path.join(base_path, '.'.join([self.__class__.__name__, 'query', CONFIG.CORPUS_EXT]))

        if os.path.exists(corpus_fname):
            corpus = OrderedCorpus(corpus_fname)

        else:
            queries = []
            pp = GeneralCorpus(self.project)
            ids = self.project.load_ids()
            for idx in ids:
                with open(os.path.join(self.project.path_dict['query'], idx + '.txt')) as f:
                    content = f.read()

                doc_vec = list(pp.preprocess(content))
                queries.append((doc_vec, (idx, 'query')))

            OrderedCorpus.serialize(corpus_fname, queries, metadata=True)
            corpus = OrderedCorpus(corpus_fname)
        return corpus

    def create_corpus(self):

        base_path = self.project.path_dict['base']

        corpus_fname = os.path.join(base_path, '.'.join([self.__class__.__name__, 'code',  CONFIG.CORPUS_EXT]))

        if os.path.exists(corpus_fname):
            corpus = OrderedCorpus(corpus_fname)

        else:
            corpus = GitCorpus(self.project)

            OrderedCorpus.serialize(corpus_fname, corpus, metadata=True)

            corpus = OrderedCorpus(corpus_fname)

        return corpus

    def create_model(self):
        raise NotImplementedError

    def predict(self, query_topic, doc_topic, distance_measure=util.cosine_distance):
        self.logger.info('Getting ranks between %d query topics and %d doc topics',
                    len(query_topic), len(doc_topic))
        goldsets = self.project.load_goldsets(self.goldset_level)
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
                self.logger.info("Could not find goldset for query %s", qid)

        self.logger.info('Returning %d ranks', len(ranks))
        return ranks

    def get_ranks(self):
        ranks = self.read_ranks()
        if not ranks:
            corpus = self.create_corpus()
            queries = self.create_query()
            model = self.create_model(corpus)
            query_topics = self.get_topics(model, queries)
            doc_topics = self.get_topics(model, corpus)
            ranks = self.predict(query_topics, doc_topics)
            self.write_ranks(ranks)
        return ranks
    
    def get_rels(self, goldset, q_dist):
        rels = []
        for idx, rank in enumerate(q_dist):
            distance, fpath = rank
            if fpath in goldset:
                rels.append((idx + 1, distance, fpath))
        return rels

    

    def write_ranks(self, ranks):

        base_path = os.path.join(self.project.path_dict['base'], self.__class__.__name__, 'num_topics_'+str(self.num_topics)+'_iter_'+str(self.iterations))

        if not os.path.exists(base_path):
            os.makedirs(base_path)

        fname = os.path.join(base_path, '.'.join([self.__class__.__name__, self.goldset_level, CONFIG.RANK_EXT]))
        if not os.path.exists(fname):
            with open(fname, 'w') as f:
                writer = csv.writer(f)
                writer.writerow(['id', 'rank', 'distance', 'item'])
                for qid, rank in ranks.items():
                    for idx, distance, fpath in rank:
                        writer.writerow([qid, idx, distance, fpath])
        self.logger.info('Have written ranks to disk:{}'.format(fname))

    def read_ranks(self):
        ranks = defaultdict(list)
        base_path = os.path.join(self.project.path_dict['base'], self.__class__.__name__, 'num_topics_' + str(self.num_topics) + '_iter_' + str(self.iterations))

        if not os.path.exists(base_path):
            os.makedirs(base_path)

        fname = os.path.join(base_path, '.'.join([self.__class__.__name__, self.goldset_level, CONFIG.RANK_EXT]))
        if os.path.exists(fname):
            with open(fname, 'r') as f:
                reader = csv.reader(f)
                next(reader)
                for qid, idx, dist, d_path in reader:
                    ranks[qid].append((int(idx), float(dist), d_path))
            self.logger.info('Successfully loaded previous ranks from:{}'.format(fname))
        return ranks
    
    def get_topics(self):
        raise NotImplementedError

class Lda(General):
    def __init__(self, project, goldset_level, num_topics=500, chunksize=2000, passes=10, alpha='symmetric', iterations=30):
        super().__init__(project, goldset_level)
        self.num_topics = num_topics
        self.chunksize = chunksize
        self.passes = passes
        self.iterations = iterations
        self.alpha = alpha

    def create_query(self):
        base_path = self.project.path_dict['base']
        corpus_fname = os.path.join(base_path, '.'.join([self.__class__.__name__, 'query', CONFIG.CORPUS_EXT]))
        # dict_fname = os.path.join(base_path, '.'.join([self.__class__.__name__, 'query', CONFIG.ID2WORD_EXT]))
        dict_fname = os.path.join(base_path, '.'.join([self.__class__.__name__, 'code', CONFIG.ID2WORD_EXT]))
        if not os.path.exists(corpus_fname):
            id2word = Dictionary()
            queries = []
            pp = GeneralCorpus(project=self.project)
            ids = self.project.load_ids()
            for idx in ids:
                with open(os.path.join(self.project.path_dict['query'], idx + '.txt')) as f:
                    content = f.read()

                doc_vec = list(pp.preprocess(content))
                bow = id2word.doc2bow(doc_vec, allow_update=True)
                queries.append((bow, (idx, 'query')))
            MalletCorpus.serialize(corpus_fname, queries, id2word=id2word,metadata=True)
        else:
            self.logger.info('load previous queries.')
        id2word = None
        if os.path.exists(dict_fname):
            id2word = Dictionary.load(dict_fname)
        corpus = MalletCorpus(corpus_fname, id2word=id2word)
        return corpus

    def create_corpus(self):
        base_path = self.project.path_dict['base']

        corpus_fname = os.path.join(base_path, '.'.join([self.__class__.__name__, 'code', CONFIG.CORPUS_EXT]))
        dict_fname = os.path.join(base_path, '.'.join([self.__class__.__name__, 'code', CONFIG.ID2WORD_EXT]))

        if os.path.exists(corpus_fname) and dict_fname:
            id2word = Dictionary.load(dict_fname)
            # corpus = MalletCorpus(corpus_fname, id2word=id2word,metadata=True)
            self.logger.info('load previous corpus.')
        else:
            corpus = GitCorpus(self.project)

            id2word = corpus.id2word

            MalletCorpus.serialize(corpus_fname, corpus,id2word=id2word, metadata=True)

            id2word.save(dict_fname)

        corpus = MalletCorpus(corpus_fname, id2word=id2word)

        return corpus

    def create_model(self, corpus):
        # base_path = self.project.path_dict['base']

        base_path = os.path.join(self.project.path_dict['base'], self.__class__.__name__, 'num_topics_'+str(self.num_topics)+'_iter_'+str(self.iterations))

        if not os.path.exists(base_path):
            os.makedirs(base_path)

        model_fname = os.path.join(base_path, '.'.join([self.__class__.__name__, 'code',  CONFIG.MODEL_EXT]))

        if os.path.exists(model_fname):
            self.logger.info('load previous Lda model.')
            model = LdaModel.load(model_fname)
        else:
            model = LdaModel(corpus=corpus,
                             id2word=corpus.id2word,
                             num_topics=self.num_topics,
                             alpha=self.alpha,
                             chunksize=self.chunksize,
                             passes=self.passes,
                             iterations=self.iterations,
                             eval_every=None,
                             update_every=None)
            
            model.save(model_fname)
        
        return model

    def get_topics(self,model, corpus, by_ids=None, full=True):
        self.logger.info('Getting doc topic for corpus with length %d', len(corpus))
        doc_topic = list()
        corpus.metadata = True
        old_id2word = corpus.id2word
        corpus.id2word = model.id2word

        for doc, meta in corpus:
            if by_ids is None or metadata[0] in by_ids:
                # get a vector where low topic values are zeroed out.
                topics = model[doc]
                if full:
                    topics = sparse2full(topics, model.num_topics)

                # this gets the "full" vector that includes low topic values
                topics = model.__getitem__(doc, eps=0)
                topics = [val for id, val in topics]

                doc_topic.append((meta[0], topics))

        corpus.metadata = False
        corpus.id2word = old_id2word
        self.logger.info('Returning doc topic of length %d', len(doc_topic))

        return doc_topic


class DV(General):
    def __init__(self, project, goldset_level, num_topics=500,iterations=30, min_count=1):
        super().__init__(project, goldset_level)
        self.num_topics = num_topics
        self.min_count = min_count
        self.iterations = iterations

    def create_model(self, corpus):

        base_path = os.path.join(self.project.path_dict['base'], self.__class__.__name__, 'num_topics_' + str(self.num_topics) + '_iter_' + str(self.iterations))

        if not os.path.exists(base_path):
            os.makedirs(base_path)

        # base_path = self.project.path_dict['base']

        model_fname = os.path.join(base_path, '.'.join([self.__class__.__name__, 'code',  CONFIG.MODEL_EXT]))

        corpus = LabeledCorpus(corpus.fname)

        if not os.path.exists(model_fname):
            # model = Doc2Vec(corpus, min_count=self.min_count, size=self.num_topics, workers=multiprocessing.cpu_count())
            model = Doc2Vec(corpus, min_count=self.min_count, vector_size=self.num_topics, workers=multiprocessing.cpu_count(), epochs=self.iterations)
            model.save(model_fname)

        else:
            model = Doc2Vec.load(model_fname)
            self.logger.info('load previous DV model.')
        return model

    def get_topics(self, model, corpus):
        topic_arr = []
        for doc, meta in corpus:
            try:
                topics = model.docvecs['DOC__' + meta[0]]
            except KeyError:
                topics = model.infer_vector(doc)
            topic_arr.append((meta[0], topics))
        return topic_arr


class WordSum(DV):

    def __init__(self, project, goldset_level):
        super().__init__(project, goldset_level)

    def predict(self, model, queries, corpus, by_ids=None):

        queries = LabeledCorpus(queries.fname)
        corpus = LabeledCorpus(corpus.fname)
        goldsets = self.project.load_goldsets(self.goldset_level)
        self.logger.info('Getting ranks for Doc2Vec model')

        ranks = dict()
        for query in queries:
            q_dist = list()

            qid = query.tags[0][5:]
            if by_ids is not None and qid not in by_ids:
                self.logger.info('skipping')
                continue
            self.logger.info(qid)

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
                self.logger.info("Could not find goldset for query %s", qid)

        return ranks

    def get_ranks(self):
        ranks = self.read_ranks()
        if not ranks:
            queries = self.create_query()
            corpus = self.create_corpus()
            model = self.create_model(corpus)
            ranks = self.predict(model, queries, corpus)
            self.write_ranks(ranks)
        return ranks
