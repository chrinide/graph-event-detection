if [ -z $1 ]; then
	echo "dataset name is not given"
	exit -1
fi

dataset=$1
pickle_dir="tmp/${dataset}"
extra=$2

# output_dir="/cs/home/hxiao/public_html/event_html/data/${dataset}"
output_dir="html/data/${dataset}"
remote_host="shell.cs.helsinki.fi"
remote_dir="/cs/home/hxiao/public_html/event_html/data/${dataset}"

if [ ! -d "${output_dir}/timeline" ]; then
	mkdir -p "${output_dir}/timeline"
fi

for p in $(ls ${pickle_dir}/result-*.pkl); do
	echo "${p}"
	output_name=$(basename ${p})
	output_name="${output_name%.*}.json"

	if [ ! -f ${output_dir}/timeline/${output_name} ]; then
		python dump_vis_timeline_data.py \
			--cand_trees_path ${p} \
			--interactions_path data/${dataset}/interactions.* \
			--people_path data/${dataset}/people.* \
			--corpus_dict_path  data/${dataset}/dict.pkl \
			--lda_model_path $(ls data/${dataset}/model-*.lda) \
			--output_path "${output_dir}/timeline/${output_name}" \
			-k 10 \
			${extra}
		echo "Writing to '${output_dir}/timeline/${output_name}'"
	else
		echo "computed, ingore ${output_dir}/timeline/${output_name}"
	fi
done

echo "dumping timeline names..."
python dump_all_event_json_names.py \
    ${output_dir}/timeline \
    ${output_dir}/timeline_names.json

# chmod -R a+rx /cs/home/hxiao/public_html/event_html/data
rsync -vr  ${output_dir}/timeline ${remote_host}:${remote_dir}/
rsync -v ${output_dir}/timeline_names.json ${remote_host}:${remote_dir}/
ssh ${remote_host} "chmod -R a+rx ${remote_dir}"