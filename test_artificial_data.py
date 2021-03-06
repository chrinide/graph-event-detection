import unittest
import random
import numpy as np
import networkx as nx
import itertools

from collections import Counter
from nose.tools import assert_equal, assert_true
from scipy.spatial.distance import cosine

from dag_util import get_roots
from interactions import InteractionsUtil as IU
from artificial_data import random_topic, random_events, \
    random_noisy_interactions, make_artificial_data, \
    gen_event_with_known_tree_structure, \
    get_gen_cand_tree_params


class ArtificialDataTest(unittest.TestCase):
    def setUp(self):
        np.random.seed(123456)
        random.seed(123456)
        self.params = {
            # main events
            'n_events': 5,
            'event_size_mu': 500,
            'event_size_sigma': 0.00001,
            'participant_mu': 5,
            'participant_sigma': 1,
            ## minor events
            'n_minor_events': 0,
            'minor_event_size_mu': 50,
            'minor_event_size_sigma': 0.0001,
            'minor_event_participant_mu': 5,
            'minor_event_participant_sigma': 1,
            ## shared
            'n_total_participants': 20,
            'min_time': 10,
            'max_time': 600,
            'event_duration_mu': 510,
            'event_duration_sigma': 0.0001,
            'n_topics': 10,
            'topic_scaling_factor': 1000,
            'topic_noise': 0.00001,
            'n_noisy_interactions': 1000,
            'n_noisy_interactions_fraction': 0.1,
            'alpha': 1.0,
            'tau': 0.8,
            'forward_proba': 0.3,
            'reply_proba': 0.5,
            'create_new_proba': 0.2,
            'dist_func': cosine
        }

    def seems_like_uniform_distribution(self, array):
        topic_2nd, topic_1st = np.sort(array)[-2:]
        assert_true((topic_1st / topic_2nd) < 10)

    def seems_like_skewed_distribution(self, array):
        max_2nd, max_1st = np.sort(array)[-2:]
        assert_true((max_1st / max_2nd) > 10000)

    def test_random_topic(self):
        topic, _ = random_topic(10, 0.00001)
        np.testing.assert_almost_equal(1, topic.sum())
        self.seems_like_skewed_distribution(topic)

    def test_random_topic_with_taboo(self):
        topic, main_topic = random_topic(10, 0.00001, taboo_topics=range(9))
        np.testing.assert_almost_equal(1, topic.sum())
        self.seems_like_skewed_distribution(topic)
        assert_equal(9, topic.argmax())
        assert_equal(9, main_topic)

    def test_uniform_topic(self):
        topic, _ = random_topic(10, 1)
        self.seems_like_uniform_distribution(topic)

    def adjust_params(self):
        for f in ('n_noisy_interactions', 'n_noisy_interactions_fraction',
                  'dist_func',
                  'n_minor_events', 'minor_event_size_mu',
                  'minor_event_size_sigma',
                  'minor_event_participant_mu',
                  'minor_event_participant_sigma'):
            del self.params[f]

    def test_random_events(self):
        self.adjust_params()

        events, _ = random_events(**self.params)
        assert_equal(self.params['n_events'], len(events))

        sizes = np.array([e.number_of_nodes() for e in events])
        np.testing.assert_almost_equal(
            self.params['event_size_mu'],
            np.mean(sizes)
        )

        times = lambda e: [e.node[n]['timestamp'] for n in e.nodes_iter()]
        mean_duration = np.mean([max(times(e)) - min(times(e))
                                 for e in events])
        np.testing.assert_almost_equal(
            510,
            mean_duration,
            decimal=-1
        )
        
        unique_participants = lambda e: set(itertools.chain(
            *[[e.node[n]['sender_id']] + e.node[n]['recipient_ids']
              for n in e.nodes_iter()]
        ))
        mean_n_participants = np.mean(
            [len(unique_participants(e))
             for e in events]
        )
        np.testing.assert_almost_equal(
            5,
            mean_n_participants,
            decimal=0
        )
        
        for e in events:
            topic_mean = np.mean([e.node[n]['topics']
                                  for n in e.nodes_iter()],
                                 axis=0)
            topic_2nd, topic_1st = np.sort(topic_mean)[-2:]
            assert_true((topic_1st / topic_2nd) > 10000)

    def test_random_events_with_taboo(self):
        self.adjust_params()
        events, taboos = random_events(taboo_topics=range(9),
                                       accumulate_taboo=False,
                                       **self.params)
        for e in events:
            for i in e.nodes_iter():
                assert_equal(9, e.node[i]['topics'].argmax())

        assert_equal(set(range(9)), taboos)

    def test_random_events_with_taboo_and_accumulation(self):
        self.adjust_params()
        events, taboos = random_events(
            taboo_topics=range(5),
            accumulate_taboo=True,
            **self.params
        )
        new_topics = set([e.node[n]['topics'].argmax()
                          for e in events
                          for n in e.nodes_iter()])
        
        assert_equal(set(range(5, 10)), set(new_topics))
        assert_equal(set(range(10)), taboos)

    def test_random_noisy_interactions(self):
        intrs = random_noisy_interactions(
            self.params['n_noisy_interactions'],
            self.params['min_time'],
            self.params['max_time'],
            self.params['n_total_participants'],
            self.params['n_topics'],
            self.params['topic_noise'],
        )
        assert_equal(self.params['n_noisy_interactions'],
                     len(intrs))
        topic_mean = np.mean([i['topics'] for i in intrs], axis=0)
        self.seems_like_uniform_distribution(topic_mean)
        
        np.testing.assert_almost_equal(
            305,
            np.mean([i['timestamp'] for i in intrs]),
            decimal=-3
        )
        
        freq = Counter(itertools.chain(
            *[[i['sender_id']] + i['recipient_ids']
              for i in intrs]
        ))
        freq = np.array(freq.values(),
                        dtype=np.float64)
        self.seems_like_uniform_distribution(freq / freq.sum())

    def test_random_noisy_interactions_with_taboo(self):
        intrs = random_noisy_interactions(
            self.params['n_noisy_interactions'],
            self.params['min_time'],
            self.params['max_time'],
            self.params['n_total_participants'],
            self.params['n_topics'],
            self.params['topic_noise'],
            taboo_topics=range(9)
        )
        topics = set([i['topics'].argmax() for i in intrs])
        assert_equal(set(range(10)), topics)

    def test_make_artificial_data(self):
        events, all_interactions, params = make_artificial_data(**self.params)
        assert_equal(self.params['n_events'],
                     len(params))
        assert_equal(
            self.params['n_events'],
            len(events)
        )
        assert_equal(
            self.params['event_size_mu'] * self.params['n_events'] +
            self.params['n_noisy_interactions'],
            len(all_interactions)
        )
        for i in all_interactions:
            assert_true('message_id' in i)
            # make sure it's jsonable
            assert_true(isinstance(i['topics'], list))

        # all ids are unique
        all_ids = list(itertools.chain(*[e.nodes() for e in events]))
        assert_equal(len(all_ids), len(set(all_ids)))

        for e in events:
            # make sure nodes are relabeled
            for n in e.nodes_iter():
                assert_equal(n, e.node[n]['message_id'])

            interactions = [e.node[n] for n in e.nodes_iter()]
            assert_equal(len(interactions),
                         IU.get_meta_graph(
                             interactions,
                             decompose_interactions=False,
                             remove_singleton=True,
                             given_topics=True).number_of_nodes())
            for i in interactions:
                assert_true(isinstance(i['topics'], list))

        for i in all_interactions:
            assert_true(i['sender_id'].startswith('u-'))
    
    def test_make_artificial_data_with_small_noise_percentage(self):
        fraction = 0.1
        self.params['n_noisy_interactions'] = None
        self.params['n_noisy_interactions_fraction'] = fraction
        events, all_interactions, _ = make_artificial_data(**self.params)
        n_event_interactions = sum([1 for e in events for _ in e])
        total = len(all_interactions)
        assert_equal(
            int(n_event_interactions * fraction),
            total - n_event_interactions
        )

    def test_make_artificial_data_with_large_noise_percentage(self):
        fraction = 1.1
        self.params['n_noisy_interactions'] = None
        self.params['n_noisy_interactions_fraction'] = fraction
        events, all_interactions, _ = make_artificial_data(**self.params)
        n_event_interactions = sum([1 for e in events for _ in e])
        total = len(all_interactions)
        assert_equal(
            int(n_event_interactions * fraction),
            total - n_event_interactions
        )

    def test_make_artificial_data_with_minor_events(self):
        self.params['n_minor_events'] = 10
        events, all_interactions, _ = make_artificial_data(**self.params)
        assert_equal(
            self.params['event_size_mu'] * self.params['n_events'] +
            self.params['minor_event_size_mu'] * self.params['n_minor_events'] +
            self.params['n_noisy_interactions'],
            len(all_interactions)
        )
        event_msg_ids = set([e.node[n]['message_id']
                             for e in events
                             for n in e.nodes_iter()])
        event_topics = set([np.asarray(e.node[n]['topics']).argmax()
                            for e in events
                            for n in e.nodes_iter()])
        other_topics = set()
        for i in all_interactions:
            id_ = i['message_id']
            if id_ not in event_msg_ids:  # either noise or minor
                topic = np.asarray(i['topics']).argmax()
                other_topics.add(topic)
                assert(topic not in event_topics)
        # should complement each other and sum to all topics
        assert_equal(set(range(10)),
                     other_topics | event_topics)


def test_gen_event_with_known_tree_structure():
    event_size = 100
    participants_n = 10
    event = gen_event_with_known_tree_structure(
        event_size=event_size,
        participants=range(participants_n),
        start_time=10, end_time=110,
        event_topic_param=random_topic(10, topic_noise=0.0001)[0],
        topic_noise=1,
        alpha=1.0, tau=0.8,
        forward_proba=0.3,
        reply_proba=0.5,
        create_new_proba=0.2
    )

    for n in event.nodes_iter():
        sid, rid = event.node[n]['sender_id'], event.node[n]['recipient_ids'][0]
        assert_true(sid != rid)

    for s, t in event.edges_iter():
        sid1, rid1 = event.node[s]['sender_id'], event.node[s]['recipient_ids'][0]
        sid2, rid2 = event.node[t]['sender_id'], event.node[t]['recipient_ids'][0]
        c_type = event[s][t]['c_type']
        if c_type == 'r':
            assert_equal(sid1, rid2)
            assert_equal(sid2, rid1)
        elif c_type == 'f':
            assert_equal(rid1, sid2)
            assert_true(rid2 != sid1)
        else:
            assert_equal(sid1, sid2)

    interactions = [event.node[n] for n in event.nodes_iter()]
    g = IU.get_meta_graph(
        interactions,
        decompose_interactions=False,
        remove_singleton=True,
        given_topics=True,
        convert_time=False
    )
    assert_equal(1, len(get_roots(g)))
    assert_equal(event_size, len(interactions))
    
    assert_true(nx.is_arborescence(event))


def test_get_gen_cand_tree_params():
    event_size = 100
    participants_n = 10
    event = gen_event_with_known_tree_structure(
        event_size=event_size,
        participants=range(participants_n),
        start_time=10, end_time=110,
        event_topic_param=random_topic(10, topic_noise=0.1)[0],
        topic_noise=1,
        alpha=1.0, tau=0.8,
        forward_proba=0.3,
        reply_proba=0.5,
        create_new_proba=0.2
    )
    event = IU.assign_edge_weights(event, cosine)
    params = get_gen_cand_tree_params(event)

    assert_true(params['U'] > 0)
    assert_equal(99, params['preprune_secs'])
    assert_equal([0], params['roots'])
