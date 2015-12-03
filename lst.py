from collections import defaultdict

from networkx.classes.digraph import DiGraph
from networkx.algorithms.dag import topological_sort


def lst_dag_general(G, r, U,
                    cost_func,
                    node_reward_key='r',
                    edge_cost_key='c',
                    edge_weight_decimal_point=None,
                    debug=False):
    """
    cost_func(node, D table, graph, edge_cost_key, [(cost at child , child)])

    It should return cost as integer type(fixed point is used when appropriate)
    """
    if edge_weight_decimal_point:
        if debug:
            print("fixed point approximation enabled")
        U = int(U * (10**edge_weight_decimal_point))

    ns = G.nodes()
    if debug:
        print("total #nodes {}".format(len(ns)))
    
    A, D, BP = {}, {}, {}
    for n in ns:
        A[n] = {}  # maximum sum of node u at a cost i
        A[n][0] = G.node[n][node_reward_key]

        D[n] = {}  # set of nodes included corresponding to A[u][i]
        D[n][0] = {n}

        BP[n] = defaultdict(list)  # backpointer corresponding to A[u][i]

    for n_i, n in enumerate(
            topological_sort(G, reverse=True)):  # leaves come first

        if debug:
            print("#nodes processed {}".format(n_i))

        children = G.neighbors(n)
        if debug:
                print('{}\'s children={}'.format(n, children))
        reward = G.node[n][node_reward_key]
        if len(children) == 1:
            child = children[0]
            if debug:
                print('child={}'.format(child))
            for i in A[child]:
                c = cost_func(n, D, G, edge_cost_key,
                              edge_weight_decimal_point,
                              [(i, child)])
                assert isinstance(c, int)
                if c <= U:
                    A[n][c] = A[child][i] + reward
                    D[n][c] = D[child][i] | {n}
                    BP[n][c] = [(child, i)]
        elif len(children) > 1:
            assert len(children) == 2
            lchild, rchild = children

            for i in A[lchild]:
                c = cost_func(n, D, G, edge_cost_key,
                              edge_weight_decimal_point,
                              [(i, lchild)])
                assert isinstance(c, int)
                if debug:
                    print('n={}, D={}, cost_child_tuples={}'.format(
                        n, D, [(i, lchild)])
                    )
                    print('c={}'.format(c))
                if c <= U:
                    if A[n].get(c) is None or A[lchild][i] + reward > A[n][c]:
                        A[n][c] = A[lchild][i] + reward
                        D[n][c] = D[lchild][i] | {n}
                        BP[n][c] = [(lchild, i)]

            for i in A[rchild]:
                c = cost_func(n, D, G, edge_cost_key,
                              edge_weight_decimal_point,
                              [(i, rchild)])
                assert isinstance(c, int)
                if c <= U:
                    if A[n].get(c) is None or A[rchild][i] + reward > A[n][c]:
                        A[n][c] = A[rchild][i] + reward
                        D[n][c] = D[rchild][i] | {n}
                        BP[n][c] = [(rchild, i)]
            
            for i in A[lchild]:
                for j in A[rchild]:
                    c = cost_func(n, D, G, edge_cost_key,
                                  edge_weight_decimal_point,
                                  [(i, lchild), (j, rchild)])
                    assert isinstance(c, int)
                    lset, rset = D[lchild][i], D[rchild][j]
                    if c <= U:
                        if (A[n].get(c) is None or
                            A[lchild][i] + A[rchild][j] + reward > A[n][c]) and \
                           len(lset & rset) == 0:
                            A[n][c] = A[lchild][i] + A[rchild][j] + reward
                            D[n][c] = D[lchild][i] | D[rchild][j] | {n}
                            BP[n][c] = [(lchild, i), (rchild, j)]

            if n == r:  # no need to continue once we processed root
                break
                
    best_cost = max(xrange(U + 1),
                    key=lambda i: A[r][i] if i in A[r] else float('-inf'))
    tree = DiGraph()
    stack = []
    if debug and len(stack) == 0:
        print('stack empty')
        print(A)
    for n, cost in BP[r][best_cost]:
        stack.append((r, n, cost))
    while len(stack) > 0:
        if debug:
            print('stack size: {}'.format(len(stack)))
            print('stack: {}'.format(stack))
        
        parent, child, cost = stack.pop(0)
        tree.add_edge(parent, child)

        # copy the attributes
        tree[parent][child] = G[parent][child]
        tree.node[parent] = G.node[parent]
        tree.node[child] = G.node[child]

        for grandchild, cost2 in BP[child][cost]:
            if debug:
                print(grandchild, cost2)
            stack.append((child, grandchild, cost2))

    return tree


def lst_dag_local(G, r, U,
                  node_reward_key='r',
                  edge_cost_key='c',
                  edge_weight_decimal_point=None,
                  debug=False):
    pass


def lst_dag(G, r, U,
            node_reward_key='r',
            edge_cost_key='c',
            edge_weight_decimal_point=None,
            fixed_point_func=round,
            debug=False):
    """
    Param:
    -------------
    binary_dag: a DAG in networkx format. Each node can have at most 2 child
    r: root node in dag
    U: the maximum threshold of edge weight sum

    Return:
    maximum-sum subtree rooted at r whose sum of edge weights <= A
    ------------
    """
    # round edge weight to fixed decimal point if necessary
    G = G.copy()
    if edge_weight_decimal_point:
        multiplier = 10**edge_weight_decimal_point
        for s, t in G.edges():
            G[s][t][edge_cost_key] = int(
                fixed_point_func(
                    G[s][t][edge_cost_key] * multiplier
                )
            )
        U = int(U * multiplier)

    if debug:
        print('U => {}'.format(U))

    ns = G.nodes()
    if debug:
        print("total #nodes {}".format(len(ns)))
    
    A, D, BP = {}, {}, {}
    for n in ns:
        A[n] = {}  # maximum sum of node u at a cost i
        A[n][0] = G.node[n][node_reward_key]

        D[n] = {}  # set of nodes included corresponding to A[u][i]
        D[n][0] = {n}

        BP[n] = defaultdict(list)  # backpointer corresponding to A[u][i]

    for n_i, n in enumerate(
            topological_sort(G, reverse=True)):  # leaves come first

        if debug:
            print("#nodes processed {}".format(n_i))
        
        children = G.neighbors(n)
        reward = G.node[n][node_reward_key]
        if len(children) == 1:
            child = children[0]
            w = G[n][child][edge_cost_key]
            for i in xrange(U, w - 1, -1):
                if (i-w) in A[child]:
                    A[n][i] = A[child][i-w] + reward
                    D[n][i] = D[child][i-w] | {n}
                    BP[n][i] = [(child, i-w)]
        elif len(children) > 1:
            assert len(children) == 2, "{} != 2".format(len(children))
            lchild, rchild = children
            lw = G[n][lchild][edge_cost_key]
            rw = G[n][rchild][edge_cost_key]

            for i in xrange(U, min(lw, rw) - 1, -1):
                max_val = float('-inf')
                max_nodes = None
                prev = None

                if i - lw >= 0 and (i - lw) in A[lchild]:
                    max_val = A[lchild][i - lw] + reward
                    max_nodes = D[lchild][i - lw] | {n}
                    prev = [(lchild, i - lw)]
                
                if (i - rw >= 0
                    and (i - rw) in A[rchild]
                    and A[rchild][i - rw] + reward > max_val):
                    max_val = A[rchild][i - rw] + reward
                    max_nodes = D[rchild][i - rw] | {n}
                    prev = [(rchild, i - rw)]

                for j in xrange(i - lw - rw, -1, -1):
                    if j in A[lchild] and (i-j-lw-rw) in A[rchild]:
                        val = A[lchild][j] + A[rchild][i-j-lw-rw] + reward
                        lset, rset = D[lchild][j], D[rchild][i-j-lw-rw]
                        if val > max_val and len(lset & rset) == 0:
                            max_val = val
                            max_nodes = lset | rset | {n}
                            prev = [(lchild, j), (rchild, i-j-lw-rw)]

                if max_nodes != None:
                    # we should have at least one *feasible* solution
                    A[n][i] = max_val
                    D[n][i] = max_nodes
                    BP[n][i] = prev
            if n == r:  # no need to continue once we processed root
                break
                
    if debug:
        print('A\n', A)

    best_cost = max(xrange(U + 1),
                    key=lambda i: A[r][i] if i in A[r] else float('-inf'))
    tree = DiGraph()
    stack = []
    for n, cost in BP[r][best_cost]:
        stack.append((r, n, cost))
    while len(stack) > 0:
        if debug:
            print('stack size: {}'.format(len(stack)))
            print('stack: {}'.format(stack))
        
        parent, child, cost = stack.pop(0)
        tree.add_edge(parent, child)

        # copy the attributes
        tree[parent][child] = G[parent][child]
        tree.node[parent] = G.node[parent]
        tree.node[child] = G.node[child]

        for grandchild, cost2 in BP[child][cost]:
            if debug:
                print(grandchild, cost2)
            stack.append((child, grandchild, cost2))

    return tree
