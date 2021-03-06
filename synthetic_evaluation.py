import itertools
import cPickle as pkl
import pandas as pd
import numpy as np

from collections import defaultdict
from glob import glob
from sklearn import metrics
from nose.tools import assert_equal
from util import json_load
from experiment_util import parse_result_path
from max_cover import k_best_trees
from evaluation import evaluate_meta_tree_result


def group_paths(result_paths, keyfunc, sort_keyfunc=None):
    """
    key: lambda
    
    return :flattened array
    """
    exp_params = [(p, parse_result_path(p))
                  for p in result_paths]
    ret = []
    key = lambda (_, params): keyfunc(params)
    exp_params = sorted(exp_params, key=key)  # sort them
    for k, g in itertools.groupby(
            exp_params, key):
        if sort_keyfunc is None:
            sorted_g = sorted(list(g))
        else:
            sorted_g = sorted(list(g),
                              key=lambda (p, param):
                              sort_keyfunc(param))
        ret.append((k, [p for p, _ in sorted_g]))
    return ret


def get_values_by_key(result_paths, key, map_func):
    return [map_func(parse_result_path(p)[key])
            for p in result_paths]


def get_interaction_ids(path):
    return [i['message_id']
            for i in json_load(path)]


def evaluate_general(
        result_paths, interactions_paths, events_paths, metrics,
        x_axis_name, x_axis_type,
        group_key, group_key_name_func, sort_keyfunc=None,
        xticks=[],
        K=10):
    """
    Return a 3D table
    group_key: the legend part
    metrics: the y axis
    x_axis_name, sort_keyfunc: the x axis
    """
    groups = group_paths(result_paths, group_key, sort_keyfunc)

    # inferring x labels
    if not xticks:
        xticks = set()
        for k, paths in groups:
            xticks |= set(get_values_by_key(
                    groups[0][1],
                    x_axis_name,
                    x_axis_type)
                          )
        xticks = sorted(xticks)

    group_keys = [k for k, _ in groups]
    legend_names = [group_key_name_func(k)
                    for k in group_keys]

    # get metric names
    example_true_events = pkl.load(open(events_paths[0]))
    example_all_entry_ids = get_interaction_ids(
        interactions_paths[0]
    )
    metric_names = evaluate_meta_tree_result(
        example_true_events,
        k_best_trees(
            pkl.load(open(groups[0][1][0])), K
        ),
        example_all_entry_ids,
        metrics
    ).keys()  # extra computing

    # enchance groups with other paths
    result_path2all_paths = {
        tpl[0]: tpl
        for tpl in zip(result_paths, interactions_paths, events_paths)
    }
    enhanced_groups = defaultdict(list)
    for k, result_paths in groups:
        i = 0
        for x in xticks:

            if i < len(result_paths) and x_axis_type(parse_result_path(result_paths[i])[x_axis_name]) == x:
                enhanced_groups[k].append(
                    result_path2all_paths[result_paths[i]]
                    )
                i += 1
            else:
                # the result is absent
                enhanced_groups[k].append((None, None, None))

    data3d = []
    for method, _ in groups:
        data2d = []
        for result_path, interactions_path, events_path in enhanced_groups[method]:
            if result_path is None:
                data2d.append([np.nan for m in metric_names])
            else:
                data2d.append(evaluate_meta_tree_result(
                    pkl.load(open(events_path)),
                    k_best_trees(pkl.load(open(result_path)), K),
                    get_interaction_ids(interactions_path),
                    metrics).values()
                              )
        data3d.append(data2d)
    print metric_names
    # method, x_axis, metric

    # some checking on size of results for different methods should be done
    # filling None if possible

    # 3d array: (method, U, metric)
    # data3d = np.array([
    #     [evaluate_meta_tree_result(
    #         pkl.load(open(events_path)),
    #         k_best_trees(pkl.load(open(result_path)), K),
    #         get_interaction_ids(interactions_path),
    #         metrics).values()
    #      for result_path, interactions_path, events_path in enhanced_groups[key]]
    #     for key, _ in groups])

    # change axis to to (metric, method, U)
    data3d = np.swapaxes(data3d, 0, 1)
    data3d = np.swapaxes(data3d, 0, 2)

    group_keys = [group_key_name_func(k)
                  for k in group_keys]
    ret = {}
    for metric, matrix in itertools.izip(metric_names, data3d):
        ret[metric] = pd.DataFrame(matrix, columns=xticks, index=group_keys)

    return ret


metrics = [metrics.adjusted_rand_score,
           metrics.adjusted_mutual_info_score,
           metrics.homogeneity_score,
           metrics.completeness_score,
           metrics.v_measure_score]

def evaluate_against_noise(result_paths, interactions_paths, events_paths,
                           metrics, xticks):
    assert_equal(len(result_paths),
                 len(interactions_paths))
    assert_equal(len(interactions_paths),
                 len(events_paths))
    
    result = evaluate_general(
        result_paths,
        interactions_paths,
        events_paths,
        metrics,
        xticks=xticks,
        x_axis_name='fraction', x_axis_type=float,
        group_key=lambda p: p['args'][0],
        group_key_name_func=lambda m: m,
        sort_keyfunc=lambda k: float(k['fraction']),
        K=1
    )
    return result


def evaluate_against_event_size(
    result_paths, interactions_paths, events_paths,    
    metrics, xticks):
    assert_equal(len(result_paths),
                 len(interactions_paths))
    assert_equal(len(interactions_paths),
                 len(events_paths))
    
    result = evaluate_general(
        result_paths,
        interactions_paths,
        events_paths,
        metrics,
        xticks=xticks, x_axis_name='event_size', x_axis_type=int,
        group_key=lambda p: p['args'][0],
        group_key_name_func=lambda m: m,
        sort_keyfunc=lambda k: float(k['event_size']),
        K=1
    )
    return result


def main():
    import argparse

    parser = argparse.ArgumentParser('')
    parser.add_argument('--experiment_paths',
                        nargs='+')
    parser.add_argument('--xticks', 
                        type=float,
                        nargs='+')
    parser.add_argument('--output_path', required=True)
    parser.add_argument('--experiment', choices=('noise', 'event_size'), required=True)

    args = parser.parse_args()

    experiment_results = [pkl.load(open(p))
                          for p in args.experiment_paths]

    interactions_paths = [e['interactions'] for e in experiment_results]
    result_paths = [e['result'] for e in experiment_results]
    events_paths = [e['true_events'] for e in experiment_results]
    
    m = {'event_size': evaluate_against_event_size, 
         'noise': evaluate_against_noise}
    eval_func = m[args.experiment]
    result = eval_func(
        result_paths, interactions_paths, events_paths, metrics=[], xticks=args.xticks
    )
    pkl.dump(result, open(args.output_path, 'w'))

if __name__ == '__main__':
    main()
