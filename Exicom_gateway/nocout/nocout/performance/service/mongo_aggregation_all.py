"""
mongo_aggregation_all.py
==================================

Usage ::
python mongo_aggregation_all.py -t 1 -f hourly -s network_perf_half_hourly -d network_perf_hourly
python mongo_aggregation_all.py -t 1 -f hourly -s service_perf_half_hourly -d service_perf_hourly
python mongo_aggregation_all.py -t 24 -f daily -s network_perf_hourly -d network_perf_daily
python mongo_aggregation_all.py -t 24 -f daily -s service_perf_hourly -d service_perf_daily
python mongo_aggregation_all.py -t 168 -f weekly -s service_perf_daily -d service_perf_weekly
python mongo_aggregation_all.py -t 168 -f weekly -s inventory_perf_daily -d inventory_perf_weekly
Options ::
t - Time frame for read operation [Hours]
s - Source Mongodb collection
d - Destination Mongodb collection
f - Time frame for script viz. daily, hourly etc.
"""

from nocout_site_name import *
import imp
import sys
from datetime import datetime, timedelta
from operator import itemgetter
from pprint import pprint
import collections
import optparse

mongo_module = imp.load_source('mongo_functions', '/opt/omd/sites/%s/nocout/utils/mongo_functions.py' % nocout_site_name)
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
parser.add_option('-s', '--source', dest='source_db', type='choice', choices=['service_perf_half_hourly',
'network_perf_half_hourly', 'service_perf_hourly', 'network_perf_hourly', 'interface_perf_daily', 'inventory_perf_daily'])
parser.add_option('-d', '--destination', dest='destination_db', type='choice', choices=['service_perf_hourly',
'network_perf_hourly', 'network_perf_daily', 'service_perf_daily', 'interface_perf_weekly', 'inventory_perf_weekly'])
parser.add_option('-t', '--hours', dest='hours', type='choice', choices=['1', '24', '168'])
parser.add_option('-f', '--timeframe', dest='timeframe', type='choice', choices=['hourly', 'daily', 'weekly'])
options, remainder = parser.parse_args(sys.argv[1:])
print options
print remainder
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
	global mongo_configs
	docs = []
	end_time = datetime.now()
	#end_time = datetime(2014, 10, 15)
	start_time = end_time - timedelta(hours=hours)
	# Read data from mongodb, performance live data
    	docs = sorted(read_data(start_time, end_time, configs=mongo_configs), key=itemgetter('host'))
	print '## Docs len ##'
	print len(docs)
	for doc in docs:
		quantify_perf_data(doc)

def read_data(start_time, end_time, **configs):
	db = None
	docs = []
       	db = mongo_module.mongo_conn(
		host=configs.get('configs').get('host'),
			port=configs.get('configs').get('port'),
			db_name=configs.get('configs').get('db_name')
			)
	print start_time, end_time
	if db:
		#if perf_table == 'network_perf_half_hourly':
	        #        cur = db.network_perf_half_hourly.find({ "time" : { "$gt": start_time, "$lt": end_time}})
		#elif perf_table == 'service_perf_half_hourly':
	        #        cur = db.service_perf_half_hourly.find({ "time" : { "$gt": start_time, "$lt": end_time}})
		#elif perf_table == 'network_perf_hourly':
	        #        cur = db.network_perf_hourly.find({ "time" : { "$gt": start_time, "$lt": end_time}})
		#elif perf_table == 'service_perf_hourly':
	        #        cur = db.service_perf_hourly.find({ "time" : { "$gt": start_time, "$lt": end_time}})
		#elif perf_table == 'inventory_perf_daily':
	        #        cur = db.inventory_perf_daily.find({ "time" : { "$gt": start_time, "$lt": end_time}})
		#elif perf_table == 'interface_perf_daily':
	        #        cur = db.interface_perf_daily.find({ "time" : { "$gt": start_time, "$lt": end_time}})
		cur = db[perf_table].find({'time': {'$gt': start_time, '$lt': end_time}})
        
	for doc in cur:
		docs.append(doc)
	
	return docs


def quantify_perf_data(doc):
	"""
	Quantifies (int, float) perf data using `min`, `max` and `sum` funcs
	and frequency based data based on number of  occurrences of values
	"""
	
	global aggregated_data_values
        # These services contain perf which can't be evaluated using regular `min`, `max` functions
	wimax_mrotek_services = ['wimax_ss_sector_id', 'wimax_ss_mac', 'wimax_dl_intrf', 'wimax_ul_intrf', 'wimax_ss_ip',
			'wimax_modulation_dl_fec', 'wimax_modulation_ul_fec', 'wimax_ss_frequency',
			'rici_line_1_port_state', 'rici_fe_port_state', 'rici_e1_interface_alarm',
			'rici_device_type', 'mrotek_line_1_port_state', 'mrotek_fe_port_state',
			'mrotek_e1_interface_alarm', 'mrotek_device_type']
	# Aggregated data doc to be inserted into historical mongodb 
	aggr_data = {}
	host, ip_address = doc.get('host'), doc.get('ip_address')
	ds, service = doc.get('ds'), doc.get('service')
	site = doc.get('site')
	time = doc.get('time')
	if time_frame == 'hourly':
		# Pivot the time to H:00:00
		time = time.replace(minute=0, second=0, microsecond=0)
		# Pivoting the time to next hour time frame [as explained in doc string]
		time += timedelta(hours=1)
	elif time_frame == 'daily':
		# Pivot the time to 00:00:00
		time = time.replace(hour=0, minute=0, second=0, microsecond=0)
		# Pivot the time to next day time frame
		time += timedelta(days=1)
	elif time_frame == 'weekly':
		# Pivot the time to 00:00:00
		time = doc.get('time').replace(hour=0, minute=0, second=0, microsecond=0)
		pivot_to_weekday = 7 - time.weekday()
		# Pivoting the time to next Monday 00:00:00 [starting of next week]
		time += timedelta(days=pivot_to_weekday)
	aggr_data = {
			'host': host,
			'service': service,
			'ds': ds,
			'site': site,
			'time':time,
			'ip_address': ip_address,
			'min': doc.get('min'),
			'max': doc.get('max'),
			'avg': doc.get('avg')
			}

	# Find the existing doc to update
	find_query = {
			'host': doc.get('host'),
			'service': doc.get('service'),
			'ds': aggr_data.get('ds'),
			'time': time
			}
	existing_doc = find_existing_entry(find_query)
	print 'existing_doc'
	print existing_doc
	if existing_doc:
		existing_doc = existing_doc[0]
	        values_list = [existing_doc.get('max'), aggr_data.get('max'), 
				existing_doc.get('min'), aggr_data.get('min')]
		if service in wimax_mrotek_services or '_status' in service or '_invent' in service:
			occur = collections.defaultdict(int)
			for val in values_list:
				occur[val] += 1
			freq_dist = occur.keys()
			min_val = freq_dist[0]
			max_val = freq_dist[-1]
			avg_val = None
		else:
			min_val = min(values_list) 
			max_val = max(values_list) 
			if aggr_data.get('avg'):
				avg_val = (existing_doc.get('avg') + aggr_data.get('avg'))/ 2
			else:
			        avg_val = existing_doc.get('avg')
		aggr_data.update({
			'min': min_val,
			'max': max_val,
			'avg': avg_val
			})
		# First remove the existing entry from aggregated_data_values
	        aggregated_data_values = filter(lambda d: not (set(find_query.values()) <= set(d.keys())), aggregated_data_values)
	#upsert_aggregated_data(find_query, aggr_data)
	aggregated_data_values.append(aggr_data)


def insert_aggregated_data(doc):
	"""
	Insert the data into historical mongodb
	"""

        global mongo_configs
        # Mongodb connection object
       	db = mongo_module.mongo_conn(
		host=mongo_configs.get('host'),
			port=mongo_configs.get('port'),
			db_name=mongo_configs.get('db_name')
			)
	if db:
		#if hist_perf_table == 'network_perf_hourly':
		#        db.network_perf_hourly.update(find_query, doc,upsert=True)
		#elif hist_perf_table == 'service_perf_hourly':
		#        db.service_perf_hourly.update(find_query, doc,upsert=True)
		#elif hist_perf_table == 'network_perf_daily':
		#        db.network_perf_daily.update(find_query, doc,upsert=True)
		#elif hist_perf_table == 'service_perf_daily':
		#        db.service_perf_daily.update(find_query, doc,upsert=True)
		#elif hist_perf_table == 'interface_perf_weekly':
		#        db.interface_perf_weekly.update(find_query, doc,upsert=True)
		#elif hist_perf_table == 'inventory_perf_weekly':
		#        db.inventory_perf_weekly.update(find_query, doc,upsert=True)
		db[hist_perf_table].insert(doc)

def find_existing_entry(find_query):
	"""
	Find the doc for update query
	"""
       
        #global mongo_configs
	docs = []
        # Mongodb connection object
       	#db = mongo_module.mongo_conn(
	#	host=mongo_configs.get('host'),
	#		port=mongo_configs.get('port'),
	#		db_name=mongo_configs.get('db_name')
	#		)
	#if db:
		#if hist_perf_table == 'network_perf_hourly':
		#        cur = db.network_perf_hourly.find(find_query)
		#elif hist_perf_table == 'service_perf_hourly':
		#        cur = db.service_perf_hourly.find(find_query)
		#elif hist_perf_table == 'network_perf_daily':
		#        cur = db.network_perf_daily.find(find_query)
		#elif hist_perf_table == 'service_perf_daily':
		#        cur = db.service_perf_daily.find(find_query)
		#elif hist_perf_table == 'interface_perf_weekly':
		#        cur = db.interface_perf_weekly.find(find_query)
		#elif hist_perf_table == 'inventory_perf_weekly':
		#        cur = db.inventory_perf_weekly.find(find_query)
		#cur = db[hist_perf_table].find(find_query)
	#for doc in cur:
	#	docs.append(doc)
	docs = filter(lambda d: set(find_query.values()) <= set(d.keys()), aggregated_data_values)

	return docs

def usage():
	print "Usage: service_mongo_aggregation_hourly.py [options]"


if __name__ == '__main__':
	main()
	print aggregated_data_values
	insert_aggregated_data(aggregated_data_values)
