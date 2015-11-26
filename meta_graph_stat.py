import numpy as np
from pprint import pformat


class MetaGraphStat(object):
    def __init__(self, g):
        self.g = g
        if len(g.nodes()) == 0 or len(g.edges()) == 0:
            raise ValueError("Empty graph(#nodes={}, #edges={}. Root {})".format(
                len(g.nodes()), len(g.edges()),
                g.nodes()[0]
            ))

    def time_span(self):
        if len(self.g.nodes()) == 0:
            return {'start_time': None,
                    'end_time': None}
        else:
            ds = [self.g.node[i]['datetime']
                  for i in self.g.nodes()
                  if 'datetime' in self.g.node[i]]
            return {'start_time': min(ds),
                    'end_time': max(ds)}

    def edge_costs(self):
        costs = np.asarray([self.g[s][t]['c'] for s, t in self.g.edges()])
        return {'histogram': np.histogram(costs)}
        
    def basic_structure_stats(self):
        in_degrees = np.asarray([self.g.in_degree(n)
                                 for n in self.g.nodes()],
                                dtype=np.int64)
        out_degrees = np.asarray([self.g.out_degree(n)
                                  for n in self.g.nodes()],
                                 dtype=np.int64)
        degrees = in_degrees + out_degrees

        return {
            '#nodes': len(self.g.nodes()),
            '#singleton': len(np.nonzero(degrees == 0)[0]),
            '#edges': len(self.g.edges()),
            'in_degree': {
                'min': in_degrees.min() if in_degrees.size else None,
                'max': in_degrees.max() if in_degrees.size else None,
                'average': in_degrees.mean(),
                'median': np.median(in_degrees)
            },
            'out_degree': {
                'min': out_degrees.min() if len(in_degrees) > 0 else None,
                'max': out_degrees.max() if len(in_degrees) > 0 else None,
                'average': out_degrees.mean(),
                'median': np.median(out_degrees)
            }
        }

    def summary(self):
        return pformat(
            {m: getattr(self, m)()
             for m in dir(self)
             if not m.startswith('_') and m != 'summary' and callable(getattr(self, m))})

