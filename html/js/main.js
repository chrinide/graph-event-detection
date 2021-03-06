
$(document).ready(function(){
	function get_meta_config(){
		return {
			'dataset': $('#dataset').find(":selected").val(),
			'base_name': $('#dataPathSelection').find(":selected").val(),
			'graph_type': $('#graphTypeForm').find(":checked").val(),
			'context_flag': $('#contextFlagForm').find(":checked").val(),
			'event_index': $('#eventIndexSelection').find(':selected').val()
		}
	}

	function get_graph_data_url(mc){
		return "data/"+ mc.dataset + "/" + mc.context_flag + "/" + mc.graph_type + "/"  + mc.base_name;
	}

	function get_id2interaction_url(mc){
		return "data/"+ mc.dataset + "/id2interactions.json";
	}
	function get_id2people_url(mc){
		return "data/"+ mc.dataset + "/id2people.json";
	}

	
	var EDGE_BROADCAST = 1, EDGE_REPLY = 4, EDGE_RELAY = 7,	NODE_EVENT = 4;
	var palette = d3.scale.ordinal()
		.domain([EDGE_BROADCAST, EDGE_REPLY, EDGE_RELAY])
		.range(d3.scale.category10().range());
	var cluster_palette = d3.scale.category20c();
	// var sender_scale = d3.scale.oridinal()
	// 	.domain()

	var format_time = d3.time.format("%Y-%m-%d");

	function get_config(mc){
		var url_dict = {
			id2interaction_url: get_id2interaction_url(mc),
			id2people_url: get_id2people_url(mc),
			graph_data_url: get_graph_data_url(mc)
		};
		var context_flag_config = {
			'event': {
				force: {charge: -200, linkDistance: 10}
			},
			'contexted_event': {
				force: {charge: -200, linkDistance: 200}
			}
		};
		var get_people_id_func = function(info) {
			return info['id'];
		}
		var dataset_config = {
			enron: {
				people_repr: function(info){
					return info['email'].replace("@enron.com", "");
				}
			},
			islamic: {
				people_repr: get_people_id_func
			},
			sklearn: {
				people_repr: get_people_id_func
			},
			bloomberg: {
				people_repr: get_people_id_func,
			}
		}
		var dataset_setting = $.extend(
			{
				node_label: function(d){						
					return '(' + d['r'] * (Math.pow(10, 4)) + ')' + d.subject;
				}
			},
			dataset_config[mc.dataset]
		);
		
		var graph_type_config = {
			'original_graph': {
				force: {charge: -200, linkDistance: 20},
				tip: {
					html: function(d){
						return dict2html(d, ['id', 'desc']);
					}
				},
				node: {
					stroke: 'black',
					label: function(d){
						return d.name;
					}
				}
			},
			'meta_graph': {
				svg: {width: 1200, height: 750},
				force: {charge: -100, linkDistance: 10},
				tip: {
					html: function(d){
						console.log('iteraction:', d);
						// d['date'] = format_time(new Date(d['timestamp']*1000));

						d['sender_str'] = d.sender.name;
						d['recipients_str'] = _.map(d['recipients'], function(r){
							return r.name;
						}).join(',  ');
						return dict2html(d, ['subject', 'body', 'hashtags', 'sender_id', 'recipient_ids', 'datetime', 'message_id']);
					}
				},
				node: {
					fill: function(d){
						// return cluster_palette(d['cluster_label']);
						console.log(d);
						if(d['root']){
							return 'red';
						}
						else{
							return "#888";
						}
					},
					r: function(d){
						// console.log(d);
						if(d['root']){
							return 20;// d['retweet_count'] + 1;
						}
						else{
							// return 5;
							return 5;
						}
					},
					label: function(d){
						return d.body.substring(0, 60) + '..';
					}
				},
				link: {
					stroke: function(d){
						var s = d['source'], t = d['target'];
						if(s["sender_id"] == t["sender_id"]){
							console.log("broadcast..")
							return palette(EDGE_BROADCAST); // broadcast
						}
						else if(_.intersection(s["recipient_ids"], [t["sender_id"]]).length > 0 && 
								_.intersection(t["recipient_ids"], [s["sender_id"]]).length > 0){
							// console.log('s["recipient_ids"]', s["recipient_ids"])
							// console.log('t["sender_id"]', t["sender_id"])
							// console.log(_.intersection(s["recipient_ids"], [t["sender_id"]]));

							// console.log('t["recipient_ids"]', t["recipient_ids"])
							// console.log('s["sender_id"]', s["sender_id"])
							// console.log(_.intersection(t["recipient_ids"], [s["sender_id"]]));
							console.log("reply..")
							return palette(EDGE_REPLY); // reply
						}
						else if(_.intersection(s["recipient_ids"], [t["sender_id"]]).length > 0 && 
								_.intersection(t["recipient_ids"], [s["sender_id"]]).length == 0){
							console.log("relay..")
							return palette(EDGE_RELAY); // relay
						}else{
							throw new Exception("impossible!");
						}
					},
					strokeWidth: function(d){
						// if(d['c'] > 0.8){
						// 	return 10;
						// }
						// else{
						// 	return 2;
						// }
						// var max = 4;
						// console.log(d['c']);
						// var width = Math.round(max * d['c'])+1;
						// return width;
						return 2;
					},
					label: function(d){
						// console.log(d['c']);
						// return '';
						return d['c'].toFixed(2);
						if(d['c'] >= 0.5){
							return d['c'].toFixed(2);
						}
						else{
							return '';
						}
					}
				}
			}
		};
		var ret = $.extend(
			true, // deep
			{
				svg: {width: 1280, height: 1280},
				force: {charge: -150, linkDistance: 500},
				tip: {
					offset: [0, 0],
					html: function(d){
						return "boiler-plate";
					}
				},
				link: {
					stroke: "gray",
					strokeWidth: 1.5,
					opacity: 1,
					label: ''
				},
				node: {
					r: function(d){
						if(d['event']){
							return 8;
						}
						else{
							return 5;
						}
					},
					fill: function(d){
						if(d['event']){
							return palette(NODE_EVENT);
						}
						else{
							return '#bbb';
						}
					},
					label: function(d){
						return '';
					}
				}
			},
			context_flag_config[mc.context_flag],
			graph_type_config[mc.graph_type],
			mc,
			url_dict
		);
		var charge_from_input = parseInt($("#charge").val());
		if(charge_from_input){
			ret.force.charge = charge_from_input;
		}
		var linkDistance_from_input = parseInt($("#linkDistance").val());
		if(linkDistance_from_input){
			ret.force.linkDistance = linkDistance_from_input;
		}
		return ret;
	};

	var CLEAR_SVG = true;
	init_dataset_and_paths_widget("event_names.json")
	
	$('#submitButton').on('click', function(){
		var mc = get_meta_config();
		var data_path = get_graph_data_url(mc);
		if(CLEAR_SVG){
			$('svg').remove();
		}
		console.log(mc);
		// console.log(data_path);
		load_event_1(get_config(mc));
	});
	/*
	// load_event(result_paths[0], 0);
	$('#dataPathSelection').on('change', function(){
	var path = $(this).find(":selected").val();

	load_event(path, 0);	 
	})
	$('#eventIndexSelection').on('change', function(){	 
	var index = parseInt($(this).find(":selected").val());
	console.log("change to index: ", index);
	var path = $('#dataPathSelection').find(":selected").val();
	if(CLEAR_SVG){
	$('svg').remove();
	}
	load_event(path, index);
	});
	*/
	$('#dataset option:eq(0)').change();
})
