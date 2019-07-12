"""
device_availability_migration.py

File contains code for migrating the mongodb data to mysql.This File is specific to Inventory services and only migrates the data for inventory
services.

Mysql has another table inventory status table which keeps the latest data for each device configured on that site.This file also migrates the mongodb data to mysql for this table too.

"""

from nocout_site_name import *
import imp

config_module = imp.load_source('configparser', '/omd/sites/%s/nocout/configparser.py' % nocout_site_name)


def main():
    mongo_conf = []
    configs = config_module.parse_config_obj()
    for section, options in configs.items():
	mongo_conf.append((options.get('site'),options.get('host'), options.get('port')))
	
    device_availability_script = configs.get(mongo_conf[0][0]).get('device_availability').get('script')
    device_availability_migration_script = __import__(device_availability_script)
    device_availability_migration_script.main(mongo_conf=mongo_conf,
    user=configs.get(mongo_conf[0][0]).get('user'),
    sql_passwd=configs.get(mongo_conf[0][0]).get('sql_passwd'),
    nosql_db=configs.get(mongo_conf[0][0]).get('nosql_db'),
    sql_port=configs.get(mongo_conf[0][0]).get('mysql_port'),
    sql_db=configs.get(mongo_conf[0][0]).get('sql_db'), table_name=configs.get(mongo_conf[0][0]).get('device_availability').get('table_name'), ip=configs.get(mongo_conf[0][0]).get('ip')
    )
	


if __name__ == '__main__':
    main()

