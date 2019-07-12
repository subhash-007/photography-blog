"""
inventory_mongo_aggregation_daily.py
====================================

Script to import the data from live mongodb `nocout_inventory_service_perf` collection to 
historical mysqldb `performance_performanceinventorydaily` table, direcly
"""

from nocout_site_name import *
import mysql.connector
from datetime import datetime, timedelta
import imp
import time

mongo_module = imp.load_source('mongo_functions', '/omd/sites/%s/nocout/utils/mongo_functions.py' % nocout_site_name)
utility_module = imp.load_source('utility_functions', '/omd/sites/%s/nocout/utils/utility_functions.py' % nocout_site_name)
config_mod = imp.load_source('configparser', '/omd/sites/%s/nocout/configparser.py' % nocout_site_name)

configs = config_mod.parse_config_obj(historical_conf=True)
desired_site = filter(lambda x: x == nocout_site_name, configs.keys())[0]
desired_config = configs.get(desired_site)

mongo_configs = {
		'host': desired_config.get('host'),
		'port': desired_config.get('port'),
		'db_name': 'nocout'
		}

mysql_configs = {
		'user': desired_config.get('user'),
		'sql_passwd': desired_config.get('sql_passwd'),
		'ip': desired_config.get('ip'),
		'sql_db': desired_config.get('sql_db'),
		'sql_port': desired_config.get('sql_port')
		}


def main(**configs):
    data_values = []
    values_list = []
    docs = []
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=1440)
    start_epoch = int(time.mktime(start_time.timetuple()))
    end_epoch = int(time.mktime(end_time.timetuple()))

    
    docs = read_data(start_epoch, end_epoch, configs=mongo_configs)
    for doc in docs:
	    values_list = build_data(doc)
	    data_values.extend(values_list)
    if data_values:
    	insert_data('performance_performanceinventorydaily', data_values, configs=mysql_configs)
    else:
	    print 'No data in Mongodb in this time frame'
    

def read_data(start_time, end_time, **kwargs):

    """
    function for reading the data from mongodb database for inventory services.After reading the data
    Args: start_time (time of last record enrty)
    Kwargs: end_time(current time) ,multiple arguments fetched from config.ini
    Return : None
    Raises: No exception

    """
    db = None
    port = None
    docs = []
    print 'start_time, end_time'
    print start_time, end_time
    db = mongo_module.mongo_conn(
        host=kwargs.get('configs').get('host'),
        port=int(kwargs.get('configs').get('port')),
        db_name=kwargs.get('configs').get('db_name')
    ) 
    if db:
        cur = db.nocout_inventory_service_perf_data.find({
            "check_timestamp": {"$gt": start_time, "$lt": end_time}
        })
        for doc in cur:
            docs.append(doc)
     
    return docs

def build_data(doc):
	"""
	function for building the data based on the collected record from mongodb database for inventory services.
	Arg: doc (extracted doc from the mongodb )
	Kwargs: None
	Return : formatted record for the mysql
	Raises: No exception
	"""
	values_list = []
	machine = doc['site_name'][:-8]

        t = (
        doc.get('device_name'),
        doc.get('service_name'),
	machine,
        doc.get('site_name'),
        doc.get('ip_address'),
        doc.get('data_source'),
        doc.get('severity'),
        doc.get('current_value'),
        doc.get('min_value'),
        doc.get('max_value'),
        doc.get('avg_value'),
        doc.get('warning_threshold'),
        doc.get('critical_threshold'),
        doc.get('sys_timestamp'),
        doc.get('check_timestamp'),
        )
	values_list.append(t)
	t = ()
	return values_list

def insert_data(table, data_values, **kwargs):
	"""
	function for building the data based on the collected record from mongodb database for inventory services.
	Arg: table (mysql database table name)
	Kwargs: data_values (formatted record)
	Return : None
	Raises: mysql.connector.Error
	"""
	db = utility_module.mysql_conn(configs=kwargs.get('configs'))
	query = 'INSERT INTO `%s` ' % table
	query += """
                (device_name, service_name, machine_name, site_name,
                ip_address, data_source, severity, current_value, min_value, max_value, avg_value,
		warning_threshold, critical_threshold, sys_timestamp, check_timestamp)
                VALUES(%s,%s, %s, %s, %s, %s, %s,replace(%s,"@"," "),replace(%s,"@"," "),replace(%s,"@"," "),replace(%s,"@"," "),%s,%s,%s,%s)
                """
	cursor = db.cursor()
    	try:
        	cursor.executemany(query, data_values)
    	except mysql.connector.Error as err:
        	raise mysql.connector.Error, err
    	db.commit()
    	cursor.close()



if __name__ == '__main__':
    main()
