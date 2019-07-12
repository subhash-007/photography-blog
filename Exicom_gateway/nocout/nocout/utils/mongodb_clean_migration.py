from nocout_site_name import *
import imp

config_module = imp.load_source('configparser', '/opt/omd/sites/%s/nocout/configparser.py' % nocout_site_name)

def main():
    mongo_conf = []
    configs = config_module.parse_config_obj()
    #print configs
    for section, options in configs.items():
        mongo_conf.append((options.get('site'),options.get('host'), int(options.get('port'))))

    mongodb_clean_script = configs.get(mongo_conf[0][0]).get('mongodb_clean').get('script')
    mongodb_script = __import__(mongodb_clean_script)
    #print mongo_conf ,configs.get(mongo_conf[0][0]).get('nosql_db')
    mongodb_script.main(mongo_conf=mongo_conf,
    nosql_db=configs.get(mongo_conf[0][0]).get('nosql_db'),
    )
if __name__ == '__main__':
    """
    main function for this file which is called in 5 minute interval.Every 5 min interval calculates the host configured on this poller
    and extracts data

    """
    try :
        main()
    except Exception, e:
        #pass
        print 'Exception: %s' % str(e)


