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
    data_values = []
    values_list = []
    docs = []
    #db = mysql_conn(configs=configs)
    # Get the time for latest entry in mysql
    #start_time = get_latest_entry(db_type='mysql', db=db, site=configs.get('site'),table_name=configs.get('table_name'))
    utc_time = datetime(1970, 1,1,5,30)


    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=360)
    start_epoch = int(time.mktime(start_time.timetuple()))
    end_epoch = int(time.mktime(end_time.timetuple()))

    print start_time,end_time
    
    #for i in range(len(configs.get('mongo_conf'))):
    docs = read_data(start_epoch, end_epoch, configs=configs.get('mongo_conf')[0], db_name=configs.get('nosql_db'))
    #for doc in docs:
    #   	values_list = build_data(doc)
    #   	data_values.extend(values_list)
    if docs:
    	insert_data(configs.get('table_name'), docs,start_time, configs=configs)
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
        cur = db.device_inventory_status.find({
            "check_timestamp": {"$gt": start_time, "$lt": end_time}
        })
        configs = config_module.parse_config_obj()
        for config, options in configs.items():
                machine_name = options.get('machine')
        for doc in cur:
		time = doc.get('time')
             	t = (
             	doc.get('device_name'),
             	doc.get('service_name'),
	     	#machine_name,
             	#doc.get('site_name'),
             	doc.get('data_source'),
             	doc.get('current_value'),
             	doc.get('min_value'),
             	doc.get('max_value'),
             	doc.get('avg_value'),
             	#doc.get('warning_threshold'),
             	#doc.get('critical_threshold'),
             	doc.get('sys_timestamp'),
             	doc.get('check_timestamp'),
             	#doc.get('ip_address'),
             	doc.get('severity')
             	)
             	docs.append(t)
             	t = ()
     
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
        t = (
        doc.get('device_name'),
        doc.get('service_name'),
        #machine_name,
        #doc.get('site_name'),
        doc.get('data_source'),
        doc.get('current_value'),
        doc.get('min_value'),
        doc.get('max_value'),
        doc.get('avg_value'),
        #doc.get('warning_threshold'),
        #doc.get('critical_threshold'),
        doc.get('sys_timestamp'),
        doc.get('check_timestamp'),
        #doc.get('ip_address'),
        doc.get('severity')
        )
	values_list.append(t)
	t = ()
	return values_list

def insert_data(table, data_values, start_time,**kwargs):
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
                	"WHERE `device_id`='%s' AND `service_name`='%s' AND `data_source`='%s'" %(str(data_values[i][0]),data_values[i][1],data_values[i][2])
		cursor = db.cursor()
        	try:
                	cursor.execute(query)
			result = cursor.fetchone()
		except mysql.connector.Error as err:
        		raise mysql.connector.Error, err
		if result:
			insert_dict['1'].append(data_values[i])
		else:
			insert_dict['0'].append(data_values[i])
	
	if len(insert_dict['1']):
		#updated for bhutan #######################
 		query = "UPDATE `%s` " % table
		query += """SET `device_id`=%s,`service_name`=%s,
		`data_source`=%s, `current_value`=replace(%s,"@"," "),
		`min_value`=replace(%s,"@"," "),`max_value`=replace(%s,"@"," "), `avg_value`=replace(%s,"@"," "),
		`sys_timestamp`=%s,`check_timestamp`=%s,
		`severity`=%s
		WHERE `device_id`=%s AND `data_source`=%s AND `service_name`=%s
		""" 
		try:
			data_values = map(lambda x: x + (x[0], x[2], x[1],), insert_dict.get('1'))
                	cursor.executemany(query, data_values)
		except mysql.connector.Error as err:
        		raise mysql.connector.Error, err
                db.commit()
		cursor.close()

	if len(insert_dict['0']):
		query = "INSERT INTO `%s`" % table
 		query+= """(device_id, service_name,
            	data_source, current_value, min_value, 
            	max_value, avg_value,
            	sys_timestamp, check_timestamp,severity) 
           	VALUES(%s, %s, %s, replace(%s,"@"," "), replace(%s,"@"," "), replace(%s,"@"," "), replace(%s,"@"," "), %s, %s, %s)
		"""
    		cursor = db.cursor()
    		try:
        		cursor.executemany(query, insert_dict.get('0'))
    		except mysql.connector.Error as err:
				raise mysql.connector.Error, err
    		db.commit()
    		cursor.close()

	#cursor=db.cursor()
        #query_delete="""DELETE FROM %s WHERE check_timestamp <= unix_timestamp('%s')"""%(table,str(start_time))
        #print "delete query",query_delete
        #cursor.execute(query_delete)
        #db.commit()
        #cursor.close()

if __name__ == '__main__':
    main()
