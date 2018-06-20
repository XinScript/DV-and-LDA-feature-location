#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''

Utility Funcitons.

'''

import logging
import os
import numpy
import scipy
import scipy.spatial
from . import config
import javalang

logger = logging.getLogger('cfl.utils')

SQRT2 = numpy.sqrt(2)


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



# def evaluate_mrr_with_frms(q_ranks):
#     x =  [(1/metas[0][0]) for qid , metas in q_ranks.items()]
#     return numpy.mean(x)

    

def calculate_mrr(ranks):
    x = [(1 / metas[0][0]) for qid, metas in ranks.items()]
    return numpy.mean(x)


class ConfigObj(dict):
    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError("No such attribute: " + name)

    def __setattr__(self, name, value):
        self[name] = value


LAN_EXT = {
    'JAVA':'.java',
    'PYTHON':'.py'
}
