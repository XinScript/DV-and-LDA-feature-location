#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import numpy
import scipy
import scipy.spatial
from . import CONFIG
import javalang

logger = logging.getLogger('cfl.utils')

SQRT2 = numpy.sqrt(2)



def get_logger(issue_name,project=None):
    real_name = '.'.join(['plt', issue_name]) if not project else '.'.join(['plt'+project.file_ext, issue_name, project.name])
    logger_path = CONFIG.BASE_PATH if not project else project.path_dict['base']
    fh = logging.FileHandler(filename=os.path.join(logger_path, issue_name+'.txt'))
    fh.setLevel(CONFIG.LOG_LEVEL)
    logger = logging.getLogger(real_name)
    logger.addHandler(fh)
    logger.setLevel(CONFIG.LOG_LEVEL)
    return logger


def cosine_distance(p, q):
    p = numpy.array(p)
    q = numpy.array(q)
    return scipy.spatial.distance.cosine(p, q)


def score(model, fn):
    # thomas et al 2011 msr
    scores = list()
    for a, topic_a in norm_phi(model):
        score = 0.0
        for b, topic_b in norm_phi(model):
            if a == b:
                continue

            score += fn(topic_a, topic_b)

        score *= (1.0 / (model.num_topics - 1))
        logger.debug("topic %d score %f" % (a, score))
        scores.append((a, score))

    return scores



def obj_binary_search(objs, field, target):
    if not objs or target < getattr(objs[0], field):
        return -1

    lo, hi = 0, len(objs) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if target < getattr(objs[mid], field):
            hi = mid - 1
        elif target > getattr(objs[mid], field):
            lo = mid + 1
        else:
            return mid
    return lo


# def get_frms(ranks):
#     frms = list()
#     for r_id, rank in ranks.items():
#         if rank:
#             idx, _ , meta = rank[0]
#             frms.append((idx, r_id, meta))
#     return frms

def evaluate_mrr_with_frms(q_ranks):
    x =  [(1/metas[0][0]) for qid , metas in q_ranks.items()]
    return numpy.mean(x)

    

def calculate_mrr(a, b):
    s = {}
    for qid, metas in a.items():
        first_rank = metas[0][0]
        s[qid] = [1 / first_rank, 0]
    for qid, metas in b.items():
        first_rank = metas[0][0]
        if qid in s:
            s[qid][1] = 1 / first_rank
        else:
            s[qid] = [0, 1 / first_rank]
    x = [i[0] for i in s.values()]
    y = [i[1] for i in s.values()]
    return numpy.mean(x), numpy.mean(y)


class ConfigObj(dict):
    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError("No such attribute: " + name)

    def __setattr__(self, name, value):
        self[name] = value


