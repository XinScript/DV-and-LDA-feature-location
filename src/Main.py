from GoldsetGenerator import GoldsetGenerator
from Project import LocalGitProject
import pickle
import os

if __name__ == '__main__':
    src_path =  '../sources/sage'
    project = LocalGitProject('sage',src_path, [('5.0', '5.1')], ['trac'])
    parser = GoldsetGenerator(project)
    # print(project.path_dict)
    parser.generate()
    project.save()