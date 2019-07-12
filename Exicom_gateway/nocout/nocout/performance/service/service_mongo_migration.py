"""
service_mongo_migration.py
==========================

Script to bulk insert data from Teramatrix Pollers into
central mysql db, for the services running on hosts,
every 5 minutes
The data in the Teramatrix pollers is stored in mongodb.

Services include: All services except Ping
"""

from nocout_site_name import *
import mysql.connector
from datetime import datetime, timedelta
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
	"network": {
	    "nosql_db": "nocout" # Mongodb database name
	    "sql_db": "nocout_dev" # Sql database name
	    "script": "service_mongo_migration" # Script which would do all the migrations
	    "table_name": "performance_performanceservice" # Sql table name

	    }
	}
    """
    data_values = []
    values_list = []
    docs = []
    db = utility_module.mysql_conn(configs=configs)
    """
    start_time variable would store the latest time uptill which mysql
    table has an entry, so the data having time stamp greater than start_time
    would be imported to mysql, only, and this way mysql would not store
    duplicate data.
    """
    for i in range(len(configs.get('mongo_conf'))):
    	start_time = mongo_module.get_latest_entry(
		    	db_type='mysql', 
		    	db=db,
		    	site=configs.get('mongo_conf')[i][0],
		    	table_name=configs.get('table_name'),
			service = True
    	)	
	start_time = datetime.now() - timedelta(minutes=5)
    	end_time = datetime.now()
	#print configs.get('table_name'),"===="
    	# Get all the entries from mongodb having timestam0p greater than start_time
    	docs = read_data(start_time, end_time, configs=configs.get('mongo_conf')[i], db_name=configs.get('nosql_db'))
	print docs,"sddddddddd"
    	for doc in docs:
        	values_list = build_data(doc)
        	data_values.extend(values_list)
    if data_values:
    	insert_data(configs.get('table_name'), data_values, configs=configs)
    	print "Data inserted into my mysql db"
    else:
	print "No data in mongo db in this time frame"

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
    #end_time = datetime(2014, 6, 26, 18, 30)
    #start_time = end_time - timedelta(minutes=10)
    docs = [] 
    db = mongo_module.mongo_conn(
        host=kwargs.get('configs')[1],
        port=int(kwargs.get('configs')[2]),
        db_name=kwargs.get('db_name')
    )
    print start_time,end_time,"end_time===="
    if db:
	if start_time is None:
		start_time = end_time - timedelta(minutes=5)
		#print start_time,end_time,"end_time===="
		cur = db.service_perf.find({ "data": { "$elemMatch": { "time": { "$gt": start_time, "$lt": end_time}}}})
	else:
		cur = db.service_perf.find({ "data": { "$elemMatch": { "time": { "$gt": start_time, "$lt": end_time}}}})
	print cur,"cur==========="
        for doc in cur:
            docs.append(doc)
    return docs

def build_data(doc):
    """
    Function to make tuples out of python dict,
    data would be stored in mysql db in the form of python tuples

    Args:
	doc (dict): Single mongodb entry

    Kwargs:

    Returns:
        A list of tuples, one tuple corresponds to a single row in mysql db
    """
    values_list = []
    #uuid = get_machineid()
    configs = config_module.parse_config_obj()
    for config, options in configs.items():
	    machine_name = options.get('machine')
    for entry in doc.get('data'):
	if (doc.get('service') != 'PING' and doc.get('service') != 'ping') and str(entry.get('value')) not in ["Requested@Resource@not@Configured", "Communication@Fail@or@Device@Power@Off", 'commFail']:
	    check_time_epoch = utility_module.get_epoch_time(entry.get('time')) - doc.get('age')
	    local_time_epoch = utility_module.get_epoch_time(doc.get('local_timestamp'))
	    # Advancing local_timestamp/sys_timestamp to next 5 mins time frame
	    #local_time_epoch = check_time_epoch + 300
            t = (
        	#uuid,
                doc.get('host'),
                doc.get('service'),
                #machine_name,
                #doc.get('site'),
                doc.get('ds'),
                str(entry.get('value')).replace("@"," "),
                str(entry.get('value')).replace("@"," "),
                str(entry.get('value')).replace("@"," "),
                str(entry.get('value')).replace("@"," "),
                #doc.get('meta').get('war'),
                #doc.get('meta').get('cric'),
                local_time_epoch,
                check_time_epoch,
		#doc.get('ip_address'),
		doc.get('severity'),
		#doc.get('age')
                )
            values_list.append(t)
            t = ()
    print values_list,"values_list"
    return values_list

def insert_data(table, data_values, **kwargs):
    """
    Function to insert data into mysql tables

    Args:
        table (str): Table name into which data to be inserted
	data_values: Values in the form of list of tuples

    Kwargs:
        kwargs (dict): Python dict to store connection variables
    """
    print data_values,"data_values"
    db = utility_module.mysql_conn(configs=kwargs.get('configs'))
    query = "INSERT INTO `%s` " % table
    query += """
            (device_id, service_name, 
            data_source, current_value, min_value, 
            max_value, avg_value, 
            sys_timestamp, check_timestamp,severity) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s ,%s,%s)
            """
    cursor = db.cursor()
    try:
        cursor.executemany(query, data_values)
	print query,data_values
    except mysql.connector.Error as err:
        raise mysql.connector.Error, err
    db.commit()
    cursor.close()


def get_machineid():
    uuid = None
    proc = subprocess.Popen(
        'sudo -S dmidecode | grep -i uuid',
        stdout=subprocess.PIPE,
        shell=True
    )
    cmd_output, err = proc.communicate()
    if not err:
        uuid = cmd_output.split(':')[1].strip()
    else:
        uuid = err

    return uuid



if __name__ == '__main__':
    main()
