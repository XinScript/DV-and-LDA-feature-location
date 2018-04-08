from os import path,listdir,makedirs
import Util
import logging
import Config
from Error import GitNotFoundException

class Project(object):
    def __init__(self,repo_path,issue_keywords=[]):
        if not path.exists(path.join(repo_path,'.git')):
            raise GitNotFoundException('The given repo path has no .git')
        else:
            self.issue_keywords = issue_keywords
            self.repo_path = repo_path
            self.name = [x for x in repo_path.split('/') if x][-1]
            self.versions = set()
            self.path = path.join(Config.BASE_PATH,self.name)
            makedirs(self.path) if not path.exists(self.path) else None
            # self.logger = logging.getLogger('pfl.{name}'.format(self.name))
            # fh = logging.FileHandler(filename=path.join(self.path,'debug.txt'))
            # fh.setLevel(logging.DEBUG)
            # self.logger.addHandler(fh)
            
    def add_versions(self,versions):
        if not all([x.__class__ == tuple for x in versions]):
            raise Exception('Must be a tuple array')
        else:
            self.versions.update(versions)

    # def load_project(self,project_path):
    #     if not path.exists(project_path):
    #         self.name = [x for x in project_path.split('/') if x][-1]
    #         self.version = set([tuple(x.split('-')) for x in [x for x in listdir(project_path) if path.isdir(path.join(project_path,x))]])

    



        

        
    # def load_issue2commit_map(self,)

