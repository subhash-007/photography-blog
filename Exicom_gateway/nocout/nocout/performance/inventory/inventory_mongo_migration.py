"""
inventory_mongo_migration.py

File contains the data migrations of mongodb to mysql db for inventory services. Inventory services run once a day.

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
    Main function for reading the data from mongodb database for inventory services.After reading the data ,it is formatted according to mysql
    table schema and inserted into mysql db
    Args: Multiple argument fetched from config.ini
    Return : None
    Raises: No exception
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

    #print start_time,end_time
    
    for i in range(len(configs.get('mongo_conf'))):
    	docs = read_data(start_epoch, end_epoch, configs=configs.get('mongo_conf')[i], db_name=configs.get('nosql_db'))
    	for doc in docs:
        	values_list = build_data(doc)
        	data_values.extend(values_list)
    if data_values:
    	insert_data(configs.get('table_name'), data_values, configs=configs)
    	print "Data inserted into performance_performanceinventory table"
    else:
	print "No data in the mongo db in this time frame"
    

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
    #end_time = datetime(2014, 6, 26, 18, 30)
    #start_time = end_time - timedelta(minutes=10)
    docs = []
    db = mongo_module.mongo_conn(
        host=kwargs.get('configs')[1],
        port=int(kwargs.get('configs')[2]),
        db_name=kwargs.get('db_name')
    ) 
    if db:
        cur = db.nocout_inventory_service_perf_data.find({
            "check_timestamp": {"$gt": start_time, "$lt": end_time}
        })
        for doc in cur:
            docs.append(doc)
    #print docs,"docs8888"
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
	time = doc.get('time')
        configs = config_module.parse_config_obj()
	for config, options in configs.items():
		machine_name = options.get('machine')
	if str(doc.get('current_value')) not in ["Requested@Resource@not@Configured", "Communication@Fail@or@Device@Power@Off","commFail"] :
		t = (
		doc.get('device_name'),
		doc.get('service_name'),
		doc.get('sys_timestamp'),
		doc.get('check_timestamp'),
		str(doc.get('current_value')).replace("@"," "),
		str(doc.get('min_value')).replace("@"," "),
		str(doc.get('max_value')).replace("@"," "),
		str(doc.get('avg_value')).replace("@"," "),
		#doc.get('warning_threshold'),
		#doc.get('critical_threshold'),
		doc.get('severity'),
		#doc.get('site_name'),
		doc.get('data_source'),
		#doc.get('ip_address'),
		#machine_name
		)
		values_list.append(t)
	t = ()
	#print values_list,"values_list0000"	
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
                (device_id,service_name,sys_timestamp,check_timestamp,
                current_value,min_value,max_value,avg_value,
                severity,data_source
                )
                VALUES(%s, %s,%s,%s,%s,%s,%s,%s,%s,%s)
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
