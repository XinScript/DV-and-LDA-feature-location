import os
import Util
import Config
from Error import GitNotFoundError,NotGitProjectError
from git import Repo, GitCmdObjectDB
import pickle


class Project(object):

    def save(self):
        with open(os.path.join(self.path,Config.PROJECT_EXT),'wb') as f:
            pickle.dump(self,f)

    @staticmethod
    def load(name):
        with open(os.path.join(Config.BASE_PATH, name, Config.PROJECT_EXT)) as f:
            return pickle.load(f)

    def __init__(self, name):
        self.name = name
        self.path = os.path.join(Config.BASE_PATH, self.name)

class GitProject(Project):
    def __init__(self, name, versions, issue_keywords=[]):

        super().__init__(name)
        self.versions = set(versions)
        self.issue_keywords = issue_keywords
        self.path_dict = Util.build_dirs(self)


class LocalGitProject(GitProject):
    def __init__(self, name, src_path, versions, issue_keywords):
        super().__init__(name, versions, issue_keywords)
        if not os.path.exists(src_path):
            raise FileNotFoundError('Directory not exists.')

        elif not os.path.exists(os.path.join(src_path, '.git')):
            raise GitNotFoundError('It is not a git directory')

        else:
            self.repo = Repo(src_path, odbt=GitCmdObjectDB)
            self.src_path = src_path

    # def add_versions(self,versions):
    #     if not all([x.__class__ == tuple for x in versions]):
    #         raise TypeError('Must be a tuple array')
    #     else:
    #         self.versions.update(versions)

    # def load_project(self,project_path):
    #     if not path.exists(project_path):
    #         self.name = [x for x in project_path.split('/') if x][-1]
    #         self.version = set([tuple(x.split('-')) for x in [x for x in listdir(project_path) if path.isdir(path.join(project_path,x))]])

    # def load_issue2commit_map(self,)
