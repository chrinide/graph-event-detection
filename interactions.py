import os
import re
import nltk
import copy
import logging
import time

import numpy as np
import networkx as nx

from memory_profiler import profile

from util import load_items_by_line, get_datetime, compose

from meta_graph import convert_to_meta_graph

CURDIR = os.path.dirname(os.path.abspath(__file__))

logging.basicConfig(format="%(asctime)s;%(levelname)s;%(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger("InteractionsUtil")
logger.setLevel(logging.DEBUG)


class InteractionsUtil(object):
    """
    To create a topical meta graph, do the following:

    - get_meta_graph
    - add_topics_to_graph
    - assign_vertex_weight
    - round_vertex_weight(if necessary)
    """
    VERTEX_REWARD_KEY = 'r'
    EDGE_COST_KEY = 'c'
    
    stoplist = load_items_by_line(os.path.join(CURDIR, 'lemur-stopwords.txt'))
    valid_token_regexp = re.compile('^[a-z]+$')

    @classmethod
    def clean_interactions(self, interactions):
        """Some cleaning. Functional
        """
        new_interactions = []
        for i in interactions:
            i = copy.deepcopy(i)
            # remove duplicate recipients
            i['recipient_ids'] = list(set(i['recipient_ids']))
            
            # normalize datetime and timestamp
            try:
                i['datetime'] = get_datetime(i['datetime'])
            except TypeError:
                logger.warn(
                    'Error parsing datetime, {} of type {}'.format(
                        i['datetime'],
                        type(i['datetime'])
                    )
                )
                continue
            i['timestamp'] = time.mktime(
                i['datetime'].timetuple()
            )
             
            new_interactions.append(i)
        return new_interactions

    @classmethod
    def decompose_interactions(cls, interactions):
        new_interactions = []
        for i in interactions:
            recs = set(i['recipient_ids'])  # remove duplicates
            if len(recs) > 1:
                new_node_name = lambda rec: u'{}.{}'.format(
                    i['message_id'],
                    rec)
                decomposed_node_names = map(new_node_name, recs)
                for rec in recs:
                    interaction = copy.deepcopy(i)
                    interaction['recipient_ids'] = [rec]

                    # the transformed message_id
                    # can be different from original
                    interaction['message_id'] = new_node_name(rec)

                    interaction['original_message_id'] = i['message_id']

                    # to avoid document vector being calculated multiple times,
                    # we add this additional attr
                    interaction['peers'] = decomposed_node_names

                    new_interactions.append(interaction)
            else:
                interaction = copy.deepcopy(i)
                interaction['message_id'] = unicode(i['message_id'])
                interaction['original_message_id'] = i['message_id']
                interaction['peers'] = []
                new_interactions.append(interaction)
        return new_interactions
    
    @classmethod
    def unzip_interactions(cls, interactions):
        """
        sort interactions by time and
        convert list of interactions to
        tuple of (interaction_names, sources, targets, time_stamps)
        """
        # sorting is important
        interactions = sorted(interactions, key=lambda r: r['datetime'])
        
        interaction_names = [i['message_id'] for i in interactions]
        sources = [i['sender_id'] for i in interactions]
        targets = [i['recipient_ids'] for i in interactions]
        time_stamps = [i['timestamp'] for i in interactions]

        return (interaction_names, sources, targets, time_stamps)

    @classmethod
    def get_meta_graph(cls, interactions,
                       preprune_secs=None,
                       decompose_interactions=True,
                       remove_singleton=True):
        """
        Return the meta graph together with temporally sorted interactions
        
        Decompose interactions if necessary
        """
        if decompose_interactions:
            interactions = cls.decompose_interactions(
                cls.clean_interactions(
                    interactions
                )
            )
        else:
            interactions = cls.clean_interactions(
                interactions
            )

        g = convert_to_meta_graph(*cls.unzip_interactions(interactions),
                                  preprune_secs=preprune_secs)
        for i in interactions:
            n = i['message_id']
            if decompose_interactions:
                g.node[n]['message_id'] = i['original_message_id']
            else:
                g.node[n]['message_id'] = i['message_id']

            g.node[n]['body'] = i['body']
            g.node[n]['subject'] = i['subject']
                    
            g.node[n]['datetime'] = i['datetime']
            g.node[n]['timestamp'] = i['timestamp']

            g.node[n][cls.VERTEX_REWARD_KEY] = 1

            if decompose_interactions:
                g.node[n]['peers'] = i['peers']

            g.node[n]['sender_id'] = i['sender_id']
            g.node[n]['recipient_ids'] = i['recipient_ids']
        
        if remove_singleton:
            for n in g.nodes():
                if g.degree(n) == 0:
                    g.remove_node(n)
        return g

    @classmethod
    def tokenize_document(cls, doc):
        return [
            word for word in nltk.word_tokenize(doc.lower())
            if (word not in cls.stoplist and
                cls.valid_token_regexp.match(word) and
                len(word) > 2 and len(word) < 15)
        ]

    @classmethod
    def add_topics_to_graph(cls, g, lda_model, dictionary, debug=False):
        """
        """
        nodes = g.nodes()
        N = len(nodes)
        for i, n in enumerate(nodes):
            if i % 100 == 0:
                logger.debug('{} / {}'.format(i, N))
            doc = u'{} {}'.format(g.node[n]['subject'], g.node[n]['body'])
            bow = dictionary.doc2bow(cls.tokenize_document(doc))
            topic_dist = lda_model.get_document_topics(
                bow,
                minimum_probability=0
            )
            g.node[n]['topics'] = np.asarray([v for _, v in topic_dist],
                                             dtype=np.float)
            g.node[n]['doc_bow'] = bow
            
        return g

    @classmethod
    def filter_dag_given_root(cls, g, r, filter_func, debug=False):
        """filter nodes given root and some filter function

        Return:
        a DAG, sub_g of which all nodes in sub_g passes filter_func
        """
        sub_g = g.copy()
        
        descendants_of_r = set(nx.descendants(g, r)) | {r}
        
        nodes_to_be_removed = [n for n in sub_g.nodes()
                               if (not filter_func(n) or
                                   n not in descendants_of_r)]
        sub_g.remove_nodes_from(nodes_to_be_removed)

        return sub_g
        
    @classmethod
    def get_rooted_subgraph_within_timespan(cls, g, r, secs, debug=False):
        """collect the subtrees, st, rooted at r that all nodes in st
        are within a timeframe of length secs start from r['datetime']
        """
        return cls.filter_dag_given_root(
            g, r,
            lambda n:
            (g.node[n]['timestamp'] - g.node[r]['timestamp'] <= secs),
            debug
        )
        
    @classmethod
    def assign_edge_weights(cls, g, dist_func, debug=False):
        """
        # TODO: same edge can calculated multiple times due to decomposition
        """
        edges = g.edges()
        N = len(edges)
        for i, (s, t) in enumerate(edges):
            if i % 10000 == 0:
                logger.debug('{}/{}'.format(i, N))
            if cls.EDGE_COST_KEY not in g[s][t]:
                g[s][t][cls.EDGE_COST_KEY] = dist_func(
                    g.node[s]['topics'],
                    g.node[t]['topics'])
        
        return g
        
    @classmethod
    def get_topic_meta_graph(cls, interactions,
                             lda_model, dictionary,
                             dist_func,
                             preprune_secs=None,
                             decompose_interactions=True,
                             debug=False):
        logger.debug('getting meta graph...')
        mg = cls.get_meta_graph(interactions,
                                decompose_interactions=decompose_interactions,
                                preprune_secs=preprune_secs)

        logger.debug('adding topics...')
        tmg = cls.add_topics_to_graph(
            mg,
            lda_model,
            dictionary,
            debug
        )

        logger.debug('assiging _edge weights')
        return cls.assign_edge_weights(tmg,
                                       dist_func,
                                       debug)

    @classmethod
    def compactize_meta_graph(cls, g, map_nodes=True):
        """remove unnecessary fields and convert node name to integer
        """
        g = g.copy()
            
        # remove topics, body, subject to save space
        fields = ['topics', 'subject', 'body', 'peers', 'doc_bow']
        for n in g.nodes():
            for f in fields:
                if f in g.node[n]:
                    del g.node[n][f]
        
        if map_nodes:
            # map node id to integer
            node_str2int = {n: i
                            for i, n in enumerate(g.nodes())}
            return (nx.relabel_nodes(g,
                                     mapping=node_str2int, copy=True),
                    node_str2int)
        else:
            return g
                
    @classmethod
    def preprune_edges_by_timespan(cls, g, secs):
        """for each node, prune its children nodes
        that are temporally far away from it
        """
        g = g.copy()
        for n in g.nodes():
            nbrs = g.neighbors(n)
            for nb in nbrs:
                if g.node[nb]['timestamp'] - g.node[n]['timestamp'] > secs:
                    g.remove_edge(n, nb)
        return g

clean_decom_unzip = compose(
    InteractionsUtil.clean_interactions,
    InteractionsUtil.decompose_interactions,
    InteractionsUtil.unzip_interactions
)

clean_unzip = compose(
    InteractionsUtil.clean_interactions,
    InteractionsUtil.unzip_interactions
)