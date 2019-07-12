from nocout_site_name import *
import imp
from datetime import datetime, timedelta
import mysql.connector
from mysql.connector import connect

mongo_module = imp.load_source('mongo_functions', '/omd/sites/%s/nocout/utils/mongo_functions.py' % nocout_site_name)
config_mod = imp.load_source('configparser', '/omd/sites/%s/nocout/configparser.py' % nocout_site_name)

configs = config_mod.parse_config_obj(historical_conf=True)
desired_site = filter(lambda x: x == nocout_site_name, configs.keys())[0]
desired_config = configs.get(desired_site)

mongo_configs = {
		'host': desired_config.get('host'),
		'port': int(desired_config.get('port')),
		'db_name': 'nocout_historical'
		}
mysql_configs = {
		'host': desired_config.get('ip'),
		'port': int(desired_config.get('sql_port')),
		'user': desired_config.get('user'),
		'password': desired_config.get('sql_passwd'),
		'database': desired_config.get('sql_db')
		}

def mysql_main():
	"""
	Mysql connection and insert operation
	"""

	table = 'performance_performancestatusdaily'
	docs = []
	# Range to read data from mongo historical
	end_time = datetime.now()
	start_time = end_time - timedelta(days=1)
	# First read data from historical mongo database
	docs = read_historical_mongo_data(start_time, end_time, configs=mongo_configs)
	#print '-- DOCS --'
	#print docs
	if docs:
	        mysql_db = mysql_conn()
	        mysql_export(table, mysql_db, docs)


def mysql_export(table, db, data_values):
	data_values = map(lambda e: (e['host'], e['service'], e['site'][:-8], e['site'], e['ip_address'], e['ds'], None, None, e['min'], e['max'], None, None, None, e['time'].strftime('%s'), e['time'].strftime('%s')), data_values)

	insert_query = "INSERT INTO %s" % table
	insert_query += """
	(device_name, service_name, machine_name, site_name, ip_address, data_source, severity, current_value,
	min_value, max_value, avg_value, warning_threshold, critical_threshold, sys_timestamp, check_timestamp)
	 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
	"""
	#print insert_query
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
		cur = db.interface_perf_daily.find({"time": {"$gt": start_time, "$lt": end_time}})
        
	for doc in cur:
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
