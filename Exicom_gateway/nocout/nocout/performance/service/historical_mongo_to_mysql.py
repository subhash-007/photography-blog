"""
mongo_aggregation_to_mysql.py
========================================

Usage:
python mongo_aggregation_to_mysql.py -t 0.5 -s service_perf_half_hourly -d performance_performanceservicebihourly
python mongo_aggregation_to_mysql.py -t 0.5 -s network_perf_half_hourly -d performance_performancenetworkbihourly
python mongo_aggregation_to_mysql.py -t 1 -s network_perf_hourly -d performance_performancenetworkhourly
python mongo_aggregation_to_mysql.py -t 168 -s inventory_perf_weekly -d performance_performanceinventoryweekly
Options ::
t - Time frame for which data to be imported [Hours]
s - Source mongodb collection
d - Destinatoin mysql historical perf table
"""

from nocout_site_name import *
import imp
from datetime import datetime, timedelta
import mysql.connector
from mysql.connector import connect
import sys
import optparse

mongo_module = imp.load_source('mongo_functions', '/omd/sites/%s/nocout/utils/mongo_functions.py' % nocout_site_name)
config_mod = imp.load_source('configparser', '/omd/sites/%s/nocout/configparser.py' % nocout_site_name)

configs = config_mod.parse_config_obj(historical_conf=True)
desired_site = filter(lambda x: x == nocout_site_name, configs.keys())[0]
desired_config = configs.get(desired_site)

mongo_configs = {
		'host': desired_config.get('host'),
		'port': int(desired_config.get('port')),
		'db_name': 'nocout'
		}
mysql_configs = {
		'host': desired_config.get('ip'),
		'port': int(desired_config.get('sql_port')),
		'user': desired_config.get('user'),
		'password': desired_config.get('sql_passwd'),
		'database': desired_config.get('sql_db')
		}
parser = optparse.OptionParser()
parser.add_option('-s', '--source_db', dest='source_db', type='str')
parser.add_option('-d', '--destination_db', dest='destination_db', type='str')
parser.add_option('-t', '--hours', dest='hours', type='choice', choices=['0.5', '1', '24', '168'])
options, remainder = parser.parse_args(sys.argv[1:]) 
if options.source_db and options.destination_db and options.hours:
	hist_perf_table = options.source_db
	hist_perf_mysql_table = options.destination_db
	hours = eval(options.hours)

def mysql_main():
	"""
	Mysql connection and insert operation
	"""

        global mongo_configs
	table = hist_perf_mysql_table
	docs = []
	# Range to read data from mongo historical
	#end_time = datetime.now() + timedelta(days=1)
	end_time = datetime.now()
	#end_time = datetime(2015, 10, 21, 00, 40, 00)
	#print end_time,"end_time----------"
	start_time = end_time - timedelta(hours=hours)
	#print start_time,"start_time------"
	start_time, end_time = start_time + timedelta(hours=1), end_time + timedelta(hours=1)
	# First read data from historical mongo database
	docs = read_historical_mongo_data(start_time, end_time, configs=mongo_configs)
	print '-- Doc Length --'
	print len(docs)
	if docs:
	        mysql_db = mysql_conn()
	        mysql_export(table, mysql_db, docs)


def mysql_export(table, db, data_values):
	print data_values,"data_values==========before======"
	data_values = map(lambda e: (e['host'], e['service'], e['site'][:-8], e['site'], e['ip_address'], e['ds'],None,None, e['min'], e['max'], e['avg'], None, None, e['time'].strftime('%s'), e['time'].strftime('%s')), data_values)

	print data_values,"data_values==========after======"
	################### updated for bhutan #########################################
	insert_query = "INSERT INTO %s" % table
	insert_query += """
	(device_name, service_name, machine_name, site_name, ip_address, data_source, severity, current_value,
	min_value, max_value, avg_value, warning_threshold, critical_threshold, sys_timestamp, check_timestamp)
	 VALUES (%s, %s, %s, %s, %s, %s, %s, replace(%s,"@"," "), replace(%s,"@"," "), replace(%s,"@"," "), replace(%s,"@"," "), %s, %s, %s, %s)
	"""
	#print insert_query,"insert_query"
	################################################################################
	cursor = db.cursor()
	try:
		cursor.executemany(insert_query, data_values)
	except mysql.connector.Error as err:
		raise mysql.connector.Error, err
	db.commit()
	cursor.close()



def read_historical_mongo_data(start_time, end_time, **configs):
	db = None
	docs = []
       	db = mongo_module.mongo_conn(
		host=configs.get('configs').get('host'),
			port=configs.get('configs').get('port'),
			db_name=configs.get('configs').get('db_name')
			)
	#print 'start_time, end_time ---'
	print start_time, end_time
	if db:
		#if hist_perf_table == 'service_perf_half_hourly':
		#	cur = db.service_perf_half_hourly.find({"time": {"$gt": start_time, "$lt": end_time}})
		#elif hist_perf_table == 'network_perf_half_hourly':
		#	cur = db.network_perf_half_hourly.find({"time": {"$gt": start_time, "$lt": end_time}})
		#elif hist_perf_table == 'service_perf_hourly':
		#	cur = db.service_perf_hourly.find({"time": {"$gt": start_time, "$lt": end_time}})
		#elif hist_perf_table == 'network_perf_hourly':
		#	cur = db.network_perf_hourly.find({"time": {"$gt": start_time, "$lt": end_time}})
		#elif hist_perf_table == 'network_perf_daily':
		#	cur = db.network_perf_daily.find({"time": {"$gt": start_time, "$lt": end_time}})
		print db,"db=========="
		#cur = db[hist_perf_table].find({'time': {'$gt': start_time, '$lte': end_time}})
                #cur = db[hist_perf_table].find({'time': {'$gt': start_time, '$lte': end_time}})

                cur = db[hist_perf_table].find({'time': {'$gt': start_time, '$lt': end_time}})
		print cur ,"cur======="        
		for doc in cur:
			print doc,"doc=========="
			docs.append(doc)
	
		return docs


def mysql_conn():
	global mysql_configs
	db = None
	db = connect(host=mysql_configs['host'], user=mysql_configs['user'],
			password=mysql_configs['password'], database=mysql_configs['database'], port=mysql_configs['port'])

	return db


if __name__ == '__main__':
	mysql_main()
