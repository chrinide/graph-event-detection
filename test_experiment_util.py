import unittest
import random
import networkx as nx
import os
import numpy as np
import glob
import cPickle as pkl

from nose.tools import assert_equal, assert_true
from collections import Counter
from datetime import timedelta

from .experiment_util import sample_rooted_binary_graphs_within_timespan,\
    experiment_signature,\
    sample_nodes_by_weight,\
    sample_nodes_by_out_degree,\
    get_number_and_percentage, \
    parse_result_path


CURDIR = os.path.dirname(os.path.abspath(__file__))


def test_experiment_signature():
    assert_equal("", experiment_signature())
    assert_equal("a=1--b=two--c=True--d=1.5--f=28days"
                 "--g={\"a\":1,\"b\":2}",
                 experiment_signature(a=1, b='two', c=True, d=1.5,
                                      f=timedelta(weeks=4),
                                      g={'a': 1, 'b': 2})
    )


def test_sample_nodes_by_weight():
    random.seed(123456)
    g = nx.DiGraph()
    g.add_node(0, w=100)
    g.add_node(1, w=10)
    g.add_node(2, w=1)

    w_func = lambda n: g.node[n]['w']
    for i in xrange(1, 4):
        assert_equal(
            range(i), sample_nodes_by_weight(g, w_func, i)
        )
    assert_equal(
        range(3), sample_nodes_by_weight(g, w_func, 100)
    )


def test_sample_nodes_by_out_degree():
    random.seed(123456)
    g = nx.DiGraph()
    n = 5
    for i in xrange(n):
        for j in xrange(i+1, n):
            g.add_edge(i, j)

    all_results = []
    for i in xrange(1000):
        all_results += sample_nodes_by_out_degree(g, 1)

    cnt = Counter(all_results)
    
    assert_equal(399, cnt[0])
    assert_equal(293, cnt[1])
    assert_equal(197, cnt[2])
    assert_equal(111, cnt[3])
    assert_equal(0, cnt[4])


def test_get_cand_n_number_and_percetnge():
    total = 100
    assert_equal(
        (10, 0.1),
        get_number_and_percentage(total, 10, 0.2)
    )
    assert_equal(
        (20, 0.2),
        get_number_and_percentage(total, None, 0.2)
    )
    assert_equal(
        (100, 1.0),
        get_number_and_percentage(total, -1, 0.2)
    )
    assert_equal(
        (100, 1.0),
        get_number_and_percentage(total, 101, 0.2)
    )


def test_parse_result_path():
    path = "/a/b/result-greedy--U=0.3--dijkstra=False--timespan=8----decompose_interactions=False--dist_func=euclidean--preprune_secs=8.pkl"
    assert_equal(
        {
            'U': '0.3',
            'dijkstra': 'False',
            'timespan': '8',
            'decompose_interactions': 'False',
            'dist_func': 'euclidean',
            'preprune_secs': '8',
            'args': ['greedy']
        },
        parse_result_path(path)
    )
    

def test_parse_result_path_1():
    path = 'result--fraction=0.2--greedy--U=0.5--dijkstra=False--timespan=8----decompose_interactions=False--dist_func=euclidean--preprune_secs=8----cand_tree_percent=0.5--root_sampling=out_degree.pkl'
    assert_equal('0.2',
                 parse_result_path(path)['fraction'])
