"""
mongo_aggregation_freq_based_base.py
====================================

Usage ::
python mongo_aggregation_freq_based_base.py -t 24 -f daily -s status_perf -d interface_perf_daily
python mongo_aggregation_freq_based_base.py -t 168 -f weekly -s nocout_inventory_service_perf_data -d inventory_perf_weekly
Options ::
t - Time frame to read data from source db [Hours]
"""

from nocout_site_name import *
import imp
import sys
from datetime import datetime, timedelta
from itertools import groupby
from operator import itemgetter
from pprint import pprint
from collections import defaultdict
import optparse

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
parser = optparse.OptionParser()
parser.add_option('-s', '--source', dest='source_db', type='choice', choices=['status_perf', 'nocout_inventory_service_perf_data'])
parser.add_option('-d', '--destination', dest='destination_db', type='choice', choices=['interface_perf_daily', 'inventory_perf_weekly'])
parser.add_option('-t', '--hours', dest='hours', type='choice', choices=['24', '168'])
parser.add_option('-f', '--timeframe', dest='timeframe', type='choice', choices=['daily', 'weekly'])
options, remainder = parser.parse_args(sys.argv[1:])
if options.source_db and options.destination_db and options.hours and options.timeframe:
	perf_table=options.source_db
	hist_perf_table=options.destination_db
	hours = int(options.hours)
	time_frame = options.timeframe
else:
	print "Usage: service_mongo_aggregation_hourly.py [options]"
	sys.exit(2)

aggregated_data_values = []


def main():
	docs = []
	end_time = datetime.now()
	start_time = end_time - timedelta(hours=hours)
	# Since time is stored as unix epoch in mongodb, convert the time into that format
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
				        quantify_data_based_on_freq(data_source_values)


def read_data(start_time, end_time, **configs):
	db = None
	docs = []
       	db = mongo_module.mongo_conn(
		host=configs.get('configs').get('host'),
			port=configs.get('configs').get('port'),
			db_name='nocout'
			)
	if db:
		#if perf_table == 'status_perf':
		#	cur = db.status_perf.find(
		#			{'sys_timestamp': {'$gt': start_time, '$lt': end_time}})
		#elif perf_table == 'nocout_inventory_service_perf_data':
		#	cur = db.nocout_inventory_service_perf_data.find(
		#			{'sys_timestamp': {'$gt': start_time, '$lt': end_time}})
		cur = db[perf_table].find({'sys_timestamp': {'$gt': start_time, '$lt': end_time}})
        
	for doc in cur:
		docs.append(doc)
	
	return docs


def quantify_data_based_on_freq(docs):
	"""
	Quantifies perf data based on occurences of perf values
	"""
	
	global aggregated_data_values
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
		# First remove the existing entry from aggregated_data_values
		aggregated_data_values = filter(lambda d: not (set(find_query.values()) <= set(d.keys())), aggregated_data_values)
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
		'max': lowest_fre_val,
		'avg': None
		})
	#upsert_aggregated_data(find_query, aggr_data)
	aggregated_data_values.append(aggr_data)

def insert_aggregated_data(docs):
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
		#if hist_perf_table == 'interface_perf_daily':
		#	db.interface_perf_daily.update(find_query, doc,upsert=True)
		#elif hist_perf_table == 'inventory_perf_weekly':
		#	db.inventory_perf_weekly.update(find_query, doc,upsert=True)
		db[hist_perf_table].insert(docs)

def find_existing_entry(find_query):
	"""
	Find the doc for update query
	"""

	docs = []
        # Mongodb connection object
       	#db = mongo_module.mongo_conn(
	#	host=mongo_configs.get('host'),
	#		port=mongo_configs.get('port'),
	#		db_name=mongo_configs.get('db_name')
	#		)
	#if db:
	#	#if hist_perf_table == 'interface_perf_daily':
	#	#	cur = db.interface_perf_daily.find(find_query)
	#	#elif hist_perf_table == 'inventory_perf_weekly':
	#	#	cur = db.inventory_perf_weekly.find(find_query)
	#	cur = db[hist_perf_table].find(find_query)
	#for doc in cur:
	#	docs.append(doc)
	docs = filter(lambda d: set(find_query.values()) <= set(d.keys()), aggregated_data_values)

	return docs


if __name__ == '__main__':
	main()
	insert_aggregated_data(aggregated_data_values)
