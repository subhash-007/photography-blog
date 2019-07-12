from nocout_site_name import *
import imp
from datetime import datetime, timedelta
from itertools import groupby
from operator import itemgetter
from pprint import pprint
from collections import defaultdict

mongo_module = imp.load_source('mongo_functions', '/omd/sites/%s/nocout/utils/mongo_functions.py' % nocout_site_name)
config_mod = imp.load_source('configparser', '/omd/sites/%s/nocout/configparser.py' % nocout_site_name)

configs = config_mod.parse_config_obj(historical_conf=True)
desired_site = filter(lambda x: x == nocout_site_name, configs.keys())[0]
desired_config = configs.get(desired_site)

mongo_configs = {
		'host': desired_config.get('host'),
		'port': int(desired_config.get('port')),
		'db_name': desired_config.get('nosql_db')
		}


def main():
	docs = []
	end_time = datetime.now()
	start_time = end_time - timedelta(days=1)
	# Convert the time into unix epoch time
	start_time, end_time = int(start_time.strftime('%s')), int(end_time.strftime('%s'))
	#start_time, end_time = 1408910008, 1408980008
	print 'start_time', 'end_time'
	print start_time, end_time
	# Read data from mongodb, performance live data
    	docs = sorted(read_data(start_time, end_time, configs=mongo_configs), key=itemgetter('device_name'))
	print '## Doc len ##'
	print len(docs)
        # Grouping based on hosts names
        group_hosts = groupby(docs, key=itemgetter('device_name'))
	for host, services in group_hosts:
		#print "$$$$$$$$$$$$$$$$$$$$$$$$$"
		#print host
		# Sort based on services
		host_services = sorted(list(services), key=itemgetter('service_name'))
		# Grouping based on service types, for a particular host
		group_services = groupby(host_services, key=itemgetter('service_name'))
                for serv_name, serv_data in group_services:
			#print serv_name
			# Docs for a particular service, to be aggregated
			service_doc_list = list(serv_data)
			#pprint(service_doc_list)
			service_doc_list = sorted(service_doc_list, key=itemgetter('data_source'))
			service_data_source_grouping = groupby(service_doc_list, key=itemgetter('data_source'))
			for data_source, values in service_data_source_grouping:
				#print data_source
				data_source_values = list(values)
				if data_source_values:
				        make_interface_perf_daily_data(data_source_values)


def read_data(start_time, end_time, **configs):
	db = None
	docs = []
       	db = mongo_module.mongo_conn(
		host=configs.get('configs').get('host'),
			port=configs.get('configs').get('port'),
			db_name='nocout'
			)
	if db:
	    cur = db.status_perf.find(
			    {'sys_timestamp': {'$gt': start_time, '$lt': end_time}})
        
	for doc in cur:
		docs.append(doc)
	
	return docs


def make_interface_perf_daily_data(docs):
	"""
	Quantifies the interface perf data in 1 day time frame
	"""
	
	# Aggregated data doc to be inserted into historical mongodb 
	aggr_data = {}
	host, ip_address = docs[0].get('device_name'), docs[0].get('ip_address')
	ds, service = docs[0].get('data_source'), docs[0].get('service_name')
	site = docs[0].get('site_name')
	# Convert the time into datetime object
	time = datetime.fromtimestamp(docs[0].get('sys_timestamp')) 
	# Pivot the time to 00:00:00
	time = time.replace(hour=0, minute=0, second=0, microsecond=0)
	# Pivot the time to next day time frame
	time += timedelta(days=1)
	# Find the existing doc to update
	find_query = {
			'host': host,
			'service': service,
			'ds': ds,
			'time': time
			}
	value_frequencies = map(lambda t: t.get('current_value'), docs)
	existing_doc = find_existing_entry(find_query)
	if existing_doc:
		value_frequencies.append(existing_doc[0].get('max'))
		value_frequencies.append(existing_doc[0].get('min'))
	# Count the highest and lowest frequency values
	# Use defaultdict in place of Counter [for python < 2.7]
	occur = defaultdict(int)
	for val in value_frequencies:
		occur[val] += 1
	freq_dist = occur.keys()
	highest_freq_val = freq_dist[0]
	lowest_fre_val = freq_dist[-1]
	aggr_data.update({
		'host': host, 
		'service': service,
		'ip_address': ip_address,
		'ds': ds,
		'site': site,
		'time': time,
		'min': highest_freq_val,
		'max': lowest_fre_val
		})
	upsert_aggregated_data(find_query, aggr_data)

def upsert_aggregated_data(find_query, doc):
	"""
	Insert the data into historical mongodb
	"""

        # Mongodb connection object
       	db = mongo_module.mongo_conn(
		host=mongo_configs.get('host'),
			port=mongo_configs.get('port'),
			db_name=mongo_configs.get('db_name')
			)
	if db:
		db.interface_perf_daily.update(find_query, doc,upsert=True)

def find_existing_entry(find_query):
	"""
	Find the doc for update query
	"""

	docs = []
        # Mongodb connection object
       	db = mongo_module.mongo_conn(
		host=mongo_configs.get('host'),
			port=mongo_configs.get('port'),
			db_name=mongo_configs.get('db_name')
			)
	if db:
		cur = db.interface_perf_daily.find(find_query)
	for doc in cur:
		docs.append(doc)

	return docs


if __name__ == '__main__':
	main()
