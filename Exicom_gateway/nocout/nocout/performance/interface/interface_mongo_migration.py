"""
interface_mongo_migration.py
==========================

Script to bulk insert data from Teramatrix Pollers into
central mysql db, for interface services.
The data in the Teramatrix Pollers is stored in Mongodb.

Interface services include : Services which runs once an Hour.
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
	"status": {
	    "nosql_db": "nocout" # Mongodb database name
	    "sql_db": "nocout_dev" # Sql database name
	    "script": "status_mongo_migration" # Script which would do all the migrations
	    "table_name": "performance_performancestatus" # Sql table name

	    }
	}
    """
    data_values = []
    values_list = []
    docs = []
    db = utility_module.mysql_conn(configs=configs)
    utc_time = datetime(1970, 1,1,5,30)


    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=60)
    start_epoch = int(time.mktime(start_time.timetuple()))
    end_epoch = int(time.mktime(end_time.timetuple()))

    print start_time,end_time
    
    for i in range(len(configs.get('mongo_conf'))):
    	docs = read_data(start_epoch, end_epoch, configs=configs.get('mongo_conf')[i], db_name=configs.get('nosql_db'))
    	for doc in docs:
        	values_list = build_data(doc)
        	data_values.extend(values_list)
    #print configs,"configs+++++++++++"
    if data_values:
    	insert_data(configs.get('table_name'), data_values, configs=configs)
    	print "Data inserted into performance_performancestatus table"
    else:
	print "No data in the mongo db in this time frame"
    

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
        cur = db.status_perf.find({
            "check_timestamp": {"$gt": start_time, "$lt": end_time}
        })
        for doc in cur:
            docs.append(doc)
   # print docs,"docs___________-" 
    return docs

def build_data(doc):
	"""
	Function to make tuples to be stored into mysql db

	Args:
	    doc (dict): Single mongodb entry

	Returns:
	    List of tuples, each tuple would correspond to one row in mysql db
	"""
	values_list = []
	time = doc.get('time')
        configs = config_module.parse_config_obj()
	for config, options in configs.items():
		machine_name = options.get('machine')

	if str(doc.get('current_value')) not in ["Requested@Resource@not@Configured", "Communication@Fail@or@Device@Power@Off", "commFail"] :
		t = (
		doc.get('device_name'),
		doc.get('service_name'),
		doc.get('sys_timestamp'),
		doc.get('check_timestamp'),
		################# update for bhutan #############

		#replace "@" with space
		str(doc.get('current_value')).replace("@"," "),
		str(doc.get('min_value')).replace("@"," "),
		str(doc.get('max_value')).replace("@"," "),
		str(doc.get('avg_value')).replace("@"," "),
		##################################################
		#doc.get('warning_threshold'),
		#doc.get('critical_threshold'),
		doc.get('severity'),
		#doc.get('site_name'),
		doc.get('data_source'),
		#doc.get('ip_address'),
		#machine_name,
		#doc.get('age')
		)
		values_list.append(t)
	t = ()
	print values_list,"values_list&&&&&&&&&&&&&&&"
	return values_list

def insert_data(table, data_values, **kwargs):
	"""
	Function to bulk insert data into mysql db

	Args:
	    table (str): Mysql table name
            data_values (list): List of data tuples

	Kwargs:
	    kwargs: Mysqldb connection variables
	"""
	db = utility_module.mysql_conn(configs=kwargs.get('configs'))
	query = 'INSERT INTO `%s` ' % table
	query += """
                (device_id,service_name,sys_timestamp,check_timestamp,
                current_value,min_value,max_value,avg_value,
                severity,data_source
                )
                VALUES(%s, %s, %s, %s, %s, %s,%s,%s,%s,%s)
                """
	cursor = db.cursor()
    	try:
		print "$$QUERY$$",query,data_values
        	cursor.executemany(query, data_values)
    	except mysql.connector.Error as err:
        	raise mysql.connector.Error, err
    	db.commit()
    	cursor.close()



if __name__ == '__main__':
    main()
