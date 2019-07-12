"""
service_status_tables_migration.py
==========================

Script to bulk insert current status data (for services) from
Teramatrix pollers to mysql in 5 min interval for all services except Ping.

Current status data means for each (host, service) pair only most latest entry would
be kept in the database, which describe the status for that service running on a host,
at any given time.

"""


from nocout_site_name import *
import mysql.connector
from datetime import datetime,timedelta
import subprocess
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
	"service_status_tables": {
	    "nosql_db": "nocout" # Mongodb database name
	    "sql_db": "nocout_dev" # Sql database name
	    "scripit": "service_status_tables_migration" # Script which would do all the migrations
	    "table_name": "performance_servicestatus" # Sql table name

	    }
	}
    """
    data_values = []
    values_list = []
    docs = []
    db = utility_module.mysql_conn(configs=configs)
    print db, "db0000"
    """
    start_time variable would store the latest time uptill which mysql
    table has an entry, so the data having time stamp greater than start_time
    would be imported to mysql, only, and this way mysql would not store
    duplicate data.
    """
    #for i in range(len(configs.get('mongo_conf'))):
    start_time = mongo_module.get_latest_entry(
		    	db_type='mysql', 
		    	db=db,
		    	site=configs.get('mongo_conf')[0][0],
		    	table_name=configs.get('table_name'),
			service = True
    )	
    print start_time,"start_time-----"
    #start_time = datetime.now() - timedelta(minutes=5)
    end_time = datetime.now()
    # Get all the entries from mongodb having timestam0p greater than start_time
    docs = read_data(start_time, end_time, configs=configs.get('mongo_conf')[0], db_name=configs.get('nosql_db'))
    print "docs",docs
    configs1 = config_module.parse_config_obj()
    for conf, options in configs1.items():
            machine_name = options.get('machine')
    for doc in docs:
	local_time_epoch = utility_module.get_epoch_time(doc.get('local_timestamp'))
    	# Advancing loca_timestamp/sys_timestamp to next 5 mins time frame
        check_time_epoch = utility_module.get_epoch_time(doc.get('check_time')) - doc.get('age')
        t = (
            #uuid,
            doc.get('host'),
            doc.get('service'),
            #machine_name,
            #doc.get('site'),
            doc.get('ds'),
            #updated for bhutan ####################################		
            str(doc.get('data')[0].get('value')).replace("@"," "),
            str(doc.get('data')[0].get('value')).replace("@"," "),
            str(doc.get('data')[0].get('value')).replace("@"," "),
            str(doc.get('data')[0].get('value')).replace("@"," "),
	    ########################################################	
            #doc.get('meta').get('war'),
            #doc.get('meta').get('cric'),
            local_time_epoch,
            check_time_epoch,
            #doc.get('ip_address'),
            doc.get('severity'),
	    #doc.get('age')
        )
        data_values.append(t)
	t = ()
    if data_values:
    	insert_data(configs.get('table_name'), data_values, db,start_time,configs=configs)
   	print "Data inserted into my mysql db"
    else:
    	print "No data in mongodb in this time frame for table %s" % (configs.get('table_name'))

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
    docs = [] 
    db = mongo_module.mongo_conn(
        host=kwargs.get('configs')[1],
        port=int(kwargs.get('configs')[2]),
        db_name=kwargs.get('db_name')
    )
    
    if db:
	if start_time is None:
		cur = db.device_service_status.find()
	else:
        	cur = db.device_service_status.find({
            	"check_time": {"$gt": start_time, "$lt": end_time}
        	})
        for doc in cur:
            docs.append(doc)
    return docs

def build_data(doc):
    """
    Function to make tuples out of python dict,
    data would be stored in mysql db in the form of python tuples

    Args:
	doc (dict): Single mongodb entry

    Returns:
        A list of tuples, one tuple corresponds to a single row in mysql db
    """
    values_list = []
    #uuid = get_machineid()
    configs = config_module.parse_config_obj()
    for config, options in configs.items():
	    machine_name = options.get('machine')
    local_time_epoch = utility_module.get_epoch_time(doc.get('local_timestamp'))
    # Advancing loca_timestamp/sys_timestamp to next 5 mins time frame

    for entry in doc.get('data'):
	if not entry:
		continue
	check_time_epoch = utility_module.get_epoch_time(entry.get('time'))
    	local_time_epoch = check_time_epoch
        t = (
            #uuid,
            doc.get('host'),
            doc.get('service'),
            #machine_name,
            #doc.get('site'),
            doc.get('ds'),
            entry.get('value'),
            entry.get('value'),
            entry.get('value'),
            entry.get('value'),
            #doc.get('meta').get('war'),
            #doc.get('meta').get('cric'),
            local_time_epoch,
            check_time_epoch,
	    #doc.get('ip_address'),
	    doc.get('severity'),
	)
        values_list.append(t)
        t = ()
    return values_list

def insert_data(table, data_values, db, start_time,**kwargs):
	"""
        Function to bulk insert data into mysqldb

	Args:
	    table (str): Mysql table to which to be inserted
	    data_value (list): List of data tuples

	Kwargs (dict): Dictionary to hold connection variables
	"""
	insert_dict = {'0':[],'1':[]}
	#db = utility_module.mysql_conn(configs=kwargs.get('configs'))
	for i in range(len(data_values)):
		query = "SELECT * FROM %s " % table +\
                	"WHERE `device_id`='%s' AND  `service_name`='%s' AND `data_source` ='%s'" %(str(data_values[i][0]),data_values[i][1],data_values[i][2])
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
 		query = "UPDATE `%s` " % table
		query += """SET `device_id`=%s,`service_name`=%s,
		`data_source`=%s, `current_value`=%s,
		`min_value`=%s,`max_value`=%s, `avg_value`=%s,
		`sys_timestamp`=%s,`check_timestamp`=%s,
		`severity`=%s
		WHERE `device_id`=%s AND `service_name`=%s AND `data_source` = %s
		"""
		try:
			data_values = map(lambda x: x + (x[0], x[1],x[2]), insert_dict.get('1'))
                	cursor.executemany(query, data_values)
		except mysql.connector.Error as err:
			print "Error in MySQL Update -------", data_values
        		raise mysql.connector.Error, err
                db.commit()
		cursor.close()

	if len(insert_dict['0']):
		query = "INSERT INTO `%s`" % table
 		query+= """(device_id, service_name,
            	data_source, current_value, min_value, 
            	max_value, avg_value, 
            	sys_timestamp, check_timestamp,severity) 
           	VALUES(%s, %s, %s, %s, %s, %s, %s ,%s,%s,%s)
		"""
    		cursor = db.cursor()
    		try:
        		cursor.executemany(query, insert_dict.get('0'))
    		except mysql.connector.Error as err:
			print "Error in MySQL Insert-----",insert_dict.get('0')	
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
