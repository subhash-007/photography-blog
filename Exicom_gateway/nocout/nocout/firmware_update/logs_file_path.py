#!/usr/bin/python
import os

path_logs_file = os.path.dirname(os.path.abspath(__file__))
paths = [path for path in path_logs_file.split('/nocout')]
file_path = paths[1]
logs_file_path = file_path +'/'

