#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import numpy
import scipy
import scipy.spatial


logger = logging.getLogger('cfl.utils')

SQRT2 = numpy.sqrt(2)


def calculate_mrr(p):
    vals = list()
    for item in p:
        if item:
            vals.append(1.0 / item)
        else:
            vals.append(0.0)

    return numpy.mean(vals)


def hellinger_distance(p, q):
    p = numpy.abs(numpy.array(p))
    q = numpy.abs(numpy.array(q))
    return scipy.linalg.norm(numpy.sqrt(p) - numpy.sqrt(q)) / SQRT2


def kullback_leibler_divergence(p, q):
    p = numpy.array(p)
    q = numpy.array(q)
    return scipy.stats.entropy(p, q)


def cosine_distance(p, q):
    p = numpy.array(p)
    q = numpy.array(q)
    return scipy.spatial.distance.cosine(p, q)


def jensen_shannon_divergence(p, q):
    p = numpy.array(p)
    q = numpy.array(q)
    M = (p + q) / 2
    return (kullback_leibler_divergence(p, M) +
            kullback_leibler_divergence(p, M)) / 2


def total_variation_distance(p, q):
    p = numpy.array(p)
    q = numpy.array(q)
    return numpy.sum(numpy.abs(p - q)) / 2


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


def norm_phi(model):
    for topicid in range(model.num_topics):
        topic = model.state.get_lambda()[topicid]
        topic = topic / topic.sum()  # normalize to probability dist
        yield topicid, topic


def download_file(url, destdir):
    # modified from http://stackoverflow.com/a/16696317
    # delay import until now
    import requests
    local_filename = os.path.join(destdir, url.split('/')[-1])
    if not os.path.exists(local_filename):
        # NOTE the stream=True parameter
        r = requests.get(url, stream=True)
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    f.flush()
    return local_filename


def obj_binary_search(objs, field, target):
    if target < getattr(objs[0], field):
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


def is_py_file(name):
    return name.endswith('.py')
