import ConfigParser
from configobj import ConfigObj
import os
from nocout_site_name import *


# Not at use, as of now
def parse_config():
    file_path = os.path.dirname(os.path.abspath(__file__))
    path = [path for path in file_path.split('/')]

    if len(path) <= 4 or 'sites' not in path:
        raise Exception, "Place the file in appropriate omd site"
    else:
        site = path[path.index('sites') + 1]
    
    p = ConfigParser.ConfigParser()
    p.read('/opt/omd/sites/%s/nocout/config.ini' % site)

    config = {}
    for section in p.sections():
        config[section] = {}
        for option  in p.options(section):
            config[section][option] = p.get(section, option)

    return config


def parse_config_obj(historical_conf=False):
    if historical_conf:
            conf_file = get_config_file(historical_conf=True)
    else:
	    conf_file = get_config_file()
    config = ConfigObj('nocout/conf.d/%s' % conf_file)
    return config


def get_config_file(conf_file=None, historical_conf=False):
	"""
	Reads the appropriate config.ini file from conf.d/,
	based on poller slave site name
	"""

	config_file_list = os.listdir('/omd/sites/%s/nocout/conf.d' % nocout_site_name)
	if historical_conf:
	        conf_file = filter(lambda x: 'historical' in x and x[11:-4] in nocout_site_name, config_file_list)
	else:
	        conf_file = filter(lambda x: 'historical' not in x and x[:-4] in nocout_site_name, config_file_list)

        return conf_file[0] if conf_file else None


if __name__ == '__main__':
    c =  parse_config_obj()

