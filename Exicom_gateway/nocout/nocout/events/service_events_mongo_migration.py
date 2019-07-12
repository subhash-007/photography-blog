"""
service_events_mongo_migration.py

File contains code for migrating the embeded mongodb data to mysql database.This File is specific to service events data and only migrates the data for event service configured on devices.

"""

from nocout_site_name import *
import mysql.connector
from datetime import datetime, timedelta
from events_rrd_migration import get_latest_event_entry
import socket
import imp
import time
mongo_module = imp.load_source('mongo_functions', '/omd/sites/%s/nocout/utils/mongo_functions.py' % nocout_site_name)
utility_module = imp.load_source('utility_functions', '/omd/sites/%s/nocout/utils/utility_functions.py' % nocout_site_name)
config_module = imp.load_source('configparser', '/omd/sites/%s/nocout/configparser.py' % nocout_site_name)

def main(**configs):
    """

    Main function for the migrating the data from mongodb to mysql db.Latest record time in mysql is carried out and from latest record time to
    current time all records are migrated from mongodb to mysql.
    Args: Multiple arguments for configuration
    Kwargs: None
    Return : None
    Raise : No exception

    """

    data_values = []
    values_list = []
    docs = []
    db = utility_module.mysql_conn(configs=configs)
    for i in range(len(configs.get('mongo_conf'))):
	end_time = datetime.now()
    	start_time = get_latest_event_entry(
		    db_type='mysql',
		    db=db,
		    site=configs.get('mongo_conf')[i][0],
		    table_name=configs.get('table_name')
    	)
    	if start_time is None:
		start_time = end_time - timedelta(minutes=15)

        print "start_time",start_time
        print "end_time",end_time

	start_time = end_time - timedelta(minutes=2)
        #print "start_time",start_time
        #print "end_time",end_time

    	start_time = utility_module.get_epoch_time(start_time)
    	end_time = utility_module.get_epoch_time(end_time)
   
   	 # Read data function reads the data from mongodb and insert into mysql
    	docs = read_data(start_time, end_time,configs=configs.get('mongo_conf')[i], db_name=configs.get('nosql_db'))
    	for doc in docs:
        	values_list = build_data(doc)
        	data_values.extend(values_list)
    print data_values
    if data_values:
        insert_data(configs.get('table_name'), data_values, configs=configs)
        print "Data inserted into mysql db"
    else:
        print "No data in the mongo db in this time frame"

def read_data(start_time, end_time, **kwargs):
    """
    Function reads the data from mongodb specific event tables for services and return the document
    Args: start_time(check_timestamp field in mongodb record is checked with start_time and end_time and data is extracted only
          for time interval)
    Kwargs: end_time (time till to collect the data)
    Return : document containing data for this time interval
    Raise : No exception

    """

    db = None
    port = None
    docs = []
    db = mongo_module.mongo_conn(
        host=kwargs.get('configs')[1],
        port=int(kwargs.get('configs')[2]),
        db_name=kwargs.get('db_name')
    )
    if db:
            cur = db.nocout_service_event_log.find({
                "check_timestamp": {"$gt": start_time, "$lt": end_time}
            })
            for doc in cur:
            	docs.append(doc)
    return docs

def build_data(doc):
	"""
        Function builds the data collected from mongodb for events according to mysql table schema and return the formatted record
        Args: doc (document fetched from the mongodb database for specific time interval)
        Kwargs: None
        Return : formatted document containing data for multiple devices
        Raise : No exception

        """

	values_list = []
	configs = config_module.parse_config_obj()
	for config, options in configs.items():
		machine_name = options.get('machine')
	t = (
        doc.get('device_name'),
        doc.get('service_name'),
        doc.get('sys_timestamp'),
	doc.get('check_timestamp'),
        #doc.get('description'),
        doc.get('severity'),
	str(doc.get('current_value')).replace("@"," "),
	str(doc.get('min_value')).replace("@"," "),
	str(doc.get('max_value')).replace("@"," "),
	str(doc.get('avg_value')).replace("@"," "),
	#doc.get('warning_threshold'),
	#doc.get('critical_threshold'),
        #doc.get('site_name'),
	doc.get('data_source'),
	#doc.get('ip_address'),
	#doc.get('age'),
	#machine_name
	)
	values_list.append(t)
	t = ()
	return values_list

def insert_data(table,data_values,**kwargs):
	"""
        Function insert the formatted record into mysql table for multiple devices
        Args: table (mysql table on which we have to insert the data.table information is fetched from config.ini)
        Kwargs: data_values (list of formatted doc )
        Return : None
        Raise : MYSQLdb.error

        """

	db = utility_module.mysql_conn(configs=kwargs.get('configs'))
	query = 'INSERT INTO `%s` ' % table
	query += """
		(device_id,service_name,sys_timestamp,check_timestamp,
		severity,current_value,min_value,max_value,avg_value
		,data_source)
		VALUES(%s ,%s,%s,%s,%s,%s,%s,%s,%s,%s)
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
