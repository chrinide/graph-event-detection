p check_k_best_trees.py \
	--cand_trees_path tmp/islamic/result-greedy--U=5.0--dijkstra=False--timespan=28days----decompose_interactions=False--dist_func=euclidean--preprune_secs=28days.pkl \
	--interactions_path data/islamic/interactions.json \
	--people_path data/islamic/people.json \
	--corpus_dict_path  data/islamic/dict.pkl \
	--lda_model_path data/islamic/model-100-50.lda \
	-k 10
