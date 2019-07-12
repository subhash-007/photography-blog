"""
historical_mysql_export.py
==========================

Provides functionality to export aggregated data into
historical mysql, using bulk insert.
"""

from nocout_site_name import *
import mysql.connector
import imp
from mysql.connector import connect

mongo_module = imp.load_source('mongo_functions', '/omd/sites/%s/nocout/utils/mongo_functions.py' % nocout_site_name)


def read_data_from_mongo(source_perf_table, start_time, end_time, configs, t_format=None):
	db = None
	docs = []
	db = mongo_module.mongo_conn(
			host=configs.get('host'),
			port=int(configs.get('port')),
			db_name='nocout') 
	if db:
		cur = db[source_perf_table].find({'local_timestamp': {'$gt': start_time, '$lt': end_time}})
		docs = list(cur)
	return docs


def mysql_export(table, db, data_values):
	data_values = map(lambda e: (e['host'], e['service'], e['site'][:-8], e['site'], e['ip_address'], e['ds'], e.get('severity'), e.get('current_value'), e['min'], e['max'], e['avg'], e['war'], e['cric'], e['time'].strftime('%s'), e['check_time'].strftime('%s')), data_values)

	insert_query = "INSERT INTO %s" % table
	insert_query += """
	(device_name, service_name, machine_name, site_name, ip_address, data_source, severity, current_value,
	min_value, max_value, avg_value, warning_threshold, critical_threshold, sys_timestamp, check_timestamp)
	 VALUES (%s, %s, %s, %s, %s, %s, %s, replace(%s,"@"," "), replace(%s,"@"," "), replace(%s,"@"," "), replace(%s,"@"," "), %s, %s, %s, %s)
	"""
	cursor = db.cursor()
	try:
		cursor.executemany(insert_query, data_values)
	except mysql.connector.Error as err:
		raise mysql.connector.Error, err
	db.commit()
	cursor.close()
	db.close()


def mysql_conn(mysql_configs=None, db=None):
	try:
		db = connect(host=mysql_configs['host'], user=mysql_configs['user'],
			password=mysql_configs['password'], database=mysql_configs['database'], port=mysql_configs['port'])
	except mysql.connector.Error, err:
		raise mysql.connector.Error, err 

	return db


def read_data(table, db, start_time, end_time):
	docs = []
	print start_time, end_time
	query = "SELECT * FROM %s WHERE sys_timestamp > %s AND sys_timestamp < %s" % (
			table, start_time, end_time)
	if db:
		try:
			cursor = db.cursor()
			cursor.execute(query)
			docs = dict_rows(cursor)
			cursor.close()
		except mysql.connector.Error as err:
			raise mysql.connector.Error, err
		finally:
			db.close
	
	return docs


def dict_rows(cur):
	desc = cur.description
	return [dict(zip([col[0] for col in desc], row)) for row in cur.fetchall()]


if __name__ == '__main__':
	#mysql_main()
	print "Script can't be run in stand alone mode"
