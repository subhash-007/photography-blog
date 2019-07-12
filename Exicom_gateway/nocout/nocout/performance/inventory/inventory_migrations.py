"""
inventory_migration.py

File contains code for migrating the mongodb data to mysql.This File is specific to Inventory services and only migrates the data for inventory
services.

Mysql has another table inventory status table which keeps the latest data for each device configured on that site.This file also migrates the mongodb data to mysql for this table too.

"""

from nocout_site_name import *
from logs_file_path import *
import imp
import os
file_name = os.path.basename(__file__)
file_name = file_name.replace(".py", "")

config_module = imp.load_source('configparser', '/omd/sites/%s/nocout/configparser.py' % nocout_site_name)

logging_module = imp.load_source('log', '/omd/sites/%s/nocout/log.py' % nocout_site_name)
logger = logging_module.logging_function('logsfiles%s' %logs_file_path,file_name)
def main():
    try:
	logger.info("**********start 'main' function**********")
        mongo_conf = []
        configs = config_module.parse_config_obj()
	logger.info('recieved configs file based on poller slave site name')
        for section, options in configs.items():
	    mongo_conf.append((options.get('site'),options.get('host'), options.get('port')))
	
        inventory_script = configs.get(mongo_conf[0][0]).get('inventory').get('script')
        inventory_migration_script = __import__(inventory_script)
	#print inventory_migration_script,"inventory_migration_script000000"
        inventory_migration_script.main(mongo_conf=mongo_conf,
        user=configs.get(mongo_conf[0][0]).get('user'),
        sql_passwd=configs.get(mongo_conf[0][0]).get('sql_passwd'),
        nosql_db=configs.get(mongo_conf[0][0]).get('nosql_db'),
        sql_port=configs.get(mongo_conf[0][0]).get('mysql_port'),
        sql_db=configs.get(mongo_conf[0][0]).get('sql_db'), table_name=configs.get(mongo_conf[0][0]).get('inventory').get('table_name'), ip=configs.get(mongo_conf[0][0]).get('ip')
        )
	logger.info("Data inserted into performance_performanceinventory table")
    except Exception,e:
	logger.exception("Error %s", str(e))
	


if __name__ == '__main__':
    main()
    logger.info("**********End 'Main' function*********")

