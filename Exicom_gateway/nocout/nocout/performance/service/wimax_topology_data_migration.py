"""
inventory_status_tables_migration.py
====================================

Script to bulk insert current status data (for inventory_services) from
Teramatrix pollers to mysql in 1 day time interval.

Current status data means for each (host, service) pair only most latest entry would
be kept in the database, which describe the status for that inventory service running on a host,
at any given time.

Inventory services include: Services that should run once in a day.

"""

from nocout_site_name import *
import mysql.connector
from datetime import datetime, timedelta
import socket
import imp
import time

mongo_module = imp.load_source('mongo_functions', '/omd/sites/%s/nocout/utils/mongo_functions.py' % nocout_site_name)
utility_module = imp.load_source('utility_functions', '/omd/sites/%s/nocout/utils/utility_functions.py' % nocout_site_name)
config_module = imp.load_source('configparser', '/omd/sites/%s/nocout/configparser.py' % nocout_site_name)

def main(**configs):
    """
    The entry point for the all the functions in this file,
    calls all the appropriate functions in the file

    Kwargs:
        configs (dict): A python dictionary containing object key identifiers
	as configuration values, read from main configuration file config.ini
    Example:
        {
	"site": "nocout_gis_slave",
	"host": "localhost",
	"user": "root",
	"ip": "localhost",
	"sql_passwd": "admin",
	"nosql_passwd": "none",
	"port": 27019 # The port being used by mongodb process
	"inventory_status_tables": {
	    "nosql_db": "nocout" # Mongodb database name
	    "sql_db": "nocout_dev" # Sql database name
	    "scripit": "inventory_status_tables_migration" # Script which would do all the migrations
	    "table_name": "performance_servicestatus" # Sql table name

	    }
	}
    """
    print configs	
    data_values = []
    values_list = []
    docs = []
    #db = mysql_conn(configs=configs)
    # Get the time for latest entry in mysql
    #start_time = get_latest_entry(db_type='mysql', db=db, site=configs.get('site'),table_name=configs.get('table_name'))
    utc_time = datetime(1970, 1,1,5,30)


    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=5)
    start_epoch = int(time.mktime(start_time.timetuple()))
    end_epoch = int(time.mktime(end_time.timetuple()))

    print start_time,end_time
    
    for i in range(len(configs.get('mongo_conf'))):
    	docs = read_data(start_epoch, end_epoch, configs=configs.get('mongo_conf')[i], db_name=configs.get('nosql_db'))
    	for doc in docs:
        	values_list = build_data(doc)
        	data_values.extend(values_list)
    if data_values:
    	insert_data(configs.get('table_name'), data_values, configs=configs)
    	print "Data inserted into my mysql db"
    else:
	print "Data is not present in mongodb in this time frame in %s" % (configs.get('table_name') )
    

def read_data(start_time, end_time, **kwargs):
    """
    Function to read data from mongodb

    Args:
        start_time (int): Start time for the entries to be fetched
	end_time (int): End time for the entries to be fetched

    Kwargs:
	kwargs (dict): Store mongodb connection variables 
    """

    db = None
    port = None
    docs = []
    #end_time = datetime(2014, 6, 26, 18, 30)
    #start_time = end_time - timedelta(minutes=10)
    docs = [] 
    db = mongo_module.mongo_conn(
        host=kwargs.get('configs')[1],
        port=int(kwargs.get('configs')[2]),
        db_name=kwargs.get('db_name')
    ) 
    if db:
        cur = db.wimax_topology_data.find({
            "check_timestamp": {"$gt": start_time, "$lt": end_time}
        })
        for doc in cur:
            docs.append(doc)
     
    return docs

def build_data(doc):
	"""
	Function to make data that would be inserted into mysql db

	Args:
	    doc (dict): Single mongodb document
	"""
	values_list = []
	time = doc.get('time')
	configs = config_module.parse_config_obj()
        for config, options in configs.items():
		machine_name = options.get('machine')
	for i in range(len(doc.get('connected_device_ip'))): 
        	t = (
        	doc.get('device_name'),
        	doc.get('service_name'),
        	machine_name,
        	doc.get('site_name'),
        	doc.get('data_source'),
        	doc.get('sys_timestamp'),
        	doc.get('check_timestamp'),
        	doc.get('ip_address'),
		doc.get('sector_id')[i],
		doc.get('connected_device_ip')[i],
		doc.get('connected_device_mac')[i],
		None
        	)
		values_list.append(t)
		t = ()
	return values_list

def insert_data(table, data_values, **kwargs):
	"""
        Function to bulk insert data into mysqldb

	Args:
	    table (str): Mysql table to which to be inserted
	    data_value (list): List of data tuples

	Kwargs (dict): Dictionary to hold connection variables
	"""
	insert_dict = {'0':[],'1':[]}
	db = utility_module.mysql_conn(configs=kwargs.get('configs'))
	for i in range(len(data_values)):
		query = "SELECT * FROM %s " % table +\
                	"WHERE `device_name`='%s' AND `service_name`='%s'" %(str(data_values[i][0]),data_values[i][1])
		cursor = db.cursor()
		#print table
		#print data_values
        	try:
                	cursor.execute(query)
			result = cursor.fetchone()
		except mysql.connector.Error as err:
        		raise mysql.connector.Error, err


		if result:
			query = "DELETE FROM %s " % table +\
                	"WHERE `device_name`='%s' AND `service_name`='%s'" %(str(data_values[i][0]),data_values[i][1])
        		try:
                		cursor.execute(query)
			except mysql.connector.Error as err:
        			raise mysql.connector.Error, err
    			db.commit()
    			cursor.close()
                        insert_dict['0'].append(data_values[i])
                else:
                        insert_dict['0'].append(data_values[i])

	if len(insert_dict['0']):		
		print "insert_dict",insert_dict['0']
		query = "INSERT INTO `%s`" % table
 		query+= """(device_name, service_name, machine_name, 
            	site_name, data_source, sys_timestamp, check_timestamp,ip_address,sector_id,connected_device_ip,connected_device_mac,mac_address) 
           	VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s)
		"""
    		cursor = db.cursor()
    		try:
        		cursor.executemany(query,  insert_dict.get('0'))
    		except mysql.connector.Error as err:
			raise mysql.connector.Error, err
    		db.commit()
    		cursor.close()



if __name__ == '__main__':
    main()
