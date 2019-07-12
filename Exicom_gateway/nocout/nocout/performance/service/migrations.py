"""
This file is the main file for migrating the mongodb data to mysql data for ping services and other services.It reads all configuration required for connecting the db from config.ini

File also migrates the mongodb data for the latest enrty for each devices to mysql data .so in mysql status tables store the latest data entry 
for each device
"""

from nocout_site_name import *
from logs_file_path import *
import os
import imp
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
	
        network_script = configs.get(mongo_conf[0][0]).get('network').get('script')
	print network_script
        network_migration_script = __import__(network_script)
	try :
        	network_migration_script.main(mongo_conf=mongo_conf,
        		user=configs.get(mongo_conf[0][0]).get('user'),
        		sql_passwd=configs.get(mongo_conf[0][0]).get('sql_passwd'),
        		nosql_db=configs.get(mongo_conf[0][0]).get('nosql_db'),
        		sql_port=configs.get(mongo_conf[0][0]).get('mysql_port'),
        		sql_db=configs.get(mongo_conf[0][0]).get('sql_db'), table_name=configs.get(mongo_conf[0][0]).get('network').get('table_name'), ip=configs.get(mongo_conf[0][0]).get('ip')
        ) 
	except Exception,e:
		print e
	
        service_script = configs.get(mongo_conf[0][0]).get('service').get('script')
	print service_script
        service_migration_script = __import__(service_script)
        service_migration_script.main(mongo_conf=mongo_conf,
        user=configs.get(mongo_conf[0][0]).get('user'),
        sql_passwd=configs.get(mongo_conf[0][0]).get('sql_passwd'),
        nosql_db=configs.get(mongo_conf[0][0]).get('nosql_db'),
        sql_port=configs.get(mongo_conf[0][0]).get('mysql_port'),
        sql_db=configs.get(mongo_conf[0][0]).get('sql_db'), table_name=configs.get(mongo_conf[0][0]).get('service').get('table_name'), ip=configs.get(mongo_conf[0][0]).get('ip')
        )
    except Exception,e:
	logger.exception("Error %s", str(e))

	
if __name__ == '__main__':
    main()
    logger.info("**********End 'Main' function*********")

