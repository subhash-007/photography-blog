#!/usr/bin/python
import logging
from datetime import datetime
import ConfigParser
import os
log_config_file = os.path.dirname(os.path.abspath(__file__))

def logging_function(logs_file_path,file_name):
    '''
	create a 'log_config.ini' file, this file set debug and error value 'True' or 'False'
	call 'setup_custom_logger_info' and 'setup_custom_logger_error' function 
	and return logger_info and logger_error
    '''
    configParser = ConfigParser.ConfigParser() #fetch log_config.ini file with object(configParser)
    configParser.read('%s/log_config.ini' % log_config_file)
    logging_set_to_debug = configParser.get('set', 'debug') # get 'set = debug' from  log_config.ini file
    logging_set_to_error = configParser.get('set', 'error') # get 'set = error' from  log_config.ini file
    
   
    if logging_set_to_debug == 'True' and logging_set_to_error == 'False':
        
        
        logger_info = setup_custom_logger_info(logs_file_path,file_name) # call setup_custom_logger_info function  and return logger_info
        return logger_info
        
    elif logging_set_to_error == 'True' and logging_set_to_debug == 'False':
       
        logger_error= setup_custom_logger_error(logs_file_path,file_name) #call setup_custom_logger_error function and return logger_error
        return logger_error
    elif logging_set_to_debug == 'True' and logging_set_to_error == 'True':
        logger_info = setup_custom_logger_info(logs_file_path,file_name) #call setup_custom_logger_info function and return logger_info
        return logger_info
    else:
        return disable_custom_logger() # if debug and error value 'False' then call this function
def setup_custom_logger_info(logs_file_path,file_name):
    '''
        In 'setup_custom_logger_info' function pass two parameter 'logs_file_path','file_name'
        logsfiles created path 'logs_file_path' and file_name which current filename(eg :- rrd_migration)
        this function, use 'getLogger' function which Return a logger with the specified 'logs_file_path'
	    and use 'logging.FileHandler' function which function create a logfile 
	    'logging.Formatter'function ,logs create spacific formate 
	    and set level 'DEBUG'
    '''
    
    configParser = ConfigParser.ConfigParser()
    configParser.read('%s/log_config.ini' % log_config_file)
    logging_set_to_format = configParser.get('formatter_simple', 'format') # get log format from  log_config.ini file 
    formatter_string = logging_set_to_format.replace('#','%') #replace '#' to '%' in logging_set_to_format
    logger = logging.getLogger(logs_file_path)
    file_handler = logging.FileHandler(os.path.join(logs_file_path, file_name + datetime.now().strftime("_%d_%m_%Y.log")))#log files create location
    formatter = logging.Formatter(formatter_string)
    file_handler.setFormatter(formatter)
    logger.setLevel(logging.DEBUG) # set level type 'DEBUG'
    logger.addHandler(file_handler)
    return logger
    
    
    
def setup_custom_logger_error(logs_file_path,file_name):
    '''
        In 'setup_custom_logger_info' function pass two parameter 'logs_file_path','file_name  
        logsfiles created path 'logs_file_path' and file_name which current filename(eg :- rrd_migration)
        this function, use 'getLogger' function which Return a logger with the specified 'logs_file_path'
        and use 'logging.FileHandler' function which function create a logfile 
       'logging.Formatter'function ,logs create spacific formate 
        and set level 'EFFOR'
    '''
    configParser = ConfigParser.ConfigParser()
    configParser.read('%s/log_config.ini' % log_config_file)
    logging_set_to_format = configParser.get('formatter_simple', 'format') # get log format from  log_config.ini file 
    formatter_string = logging_set_to_format.replace('#','%') #replace '#' to '%' in logging_set_to_format
    logger = logging.getLogger(logs_file_path)
    file_handler = logging.FileHandler(os.path.join(logs_file_path, file_name + datetime.now().strftime("_error_%d_%m_%Y.log")))#log files create location
    formatter = logging.Formatter(formatter_string)
    file_handler.setFormatter(formatter)
    logger.setLevel(logging.ERROR) # set level type 'ERROR' 
    logger.addHandler(file_handler)
    return logger

def disable_custom_logger():
    """
    In 'disable_custom_logger' function call,when log_config.ini file set debug and error value 'False' 
    
    """    
    logger = logging.getLogger() #create logger object
    logger.disabled = True #set logger is disable 
    return logger
       
