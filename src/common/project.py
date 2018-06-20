'''

This module is responsible for recording inforamtion of the subject software systems.
The instances of the class will be passed to other modules.

'''
import logging
from os import path, makedirs
from git import Repo, GitCmdObjectDB
from collections import defaultdict

from . import config
from . import error
from . import util

class GitProject():

    def __init__(self,name,lan,level = 'file'):
        if self.__class__ == GitProject:
            raise NotImplementedError
        else:
            self.lan = lan.upper()
            self.src_path = src_path = path.join(config.SOURCE_PATH,name)
            if not path.exists(src_path):
                raise FileNotFoundError(src_path)
            if not path.exists(path.join(src_path, '.git')):
                raise error.GitNotFoundError('It is not a git directory')
            self.name = name
            self.path = path.join(config.BASE_PATH, 'plt.'+lan, self.name)
            self.repo = Repo(src_path, odbt=GitCmdObjectDB)
            self.level = level.lower()
            if level not in ['class', 'method', 'file']:
                raise NotImplementedError('Only support method,class or file level.')
            self.path_dict = self.load_dirs()
    
    def load_goldsets(self):
            d = defaultdict(set)

            ids = self.load_ids()

            for idx in ids:
                fname = path.join(path.join(self.path_dict[self.level]), idx + '.txt')
                if path.exists(fname):
                    with open(fname) as f:
                        for line in f:
                            if self.level == 'file':
                                item = line.strip()
                            else:
                                item = line.strip().split('.')[0]
                            d[idx].add(item + util.LAN_EXT[self.lan])
            return d


class IssueGitProject(GitProject):

    def __init__(self,name, lan,level,by_release, issue_keywords):
        super().__init__(name,lan,level)
        self.by_release = tuple([str(x) for x in by_release])
        self.issue_keywords = issue_keywords
        self.ref = self.repo.commit(by_release[1])

    def load_dirs(self):

        base_path = path.join(self.path, '-'.join(self.by_release))

        data_path = path.join(base_path, 'data')

        query_path = path.join(data_path, 'queries')
        makedirs(query_path) if not path.exists(query_path) else None

        goldset_path = path.join(data_path, 'goldsets', self.level)
        makedirs(goldset_path) if not path.exists(goldset_path) else None

        d = {}
        d['query'] = query_path
        d[self.level] = goldset_path
        d['data'] = data_path
        d['base'] = base_path
        return d

    def load_ids(self):
        fname = path.join(self.path_dict['data'], self.level+'_ids.txt')
        with open(fname) as f:
            return {issue_id: commit_ids for issue_id, *commit_ids in [line.strip().split() for line in f]}


class CommitGitProject(GitProject):
    def __init__(self,name,lan,level,goldset_num=50,ref=None):
        self.goldset_num = goldset_num
        super().__init__(name,lan,level)
        self.ref = self.repo.head.commit if not ref else ref

    def load_dirs(self):

        base_path = path.join(self.path, 'goldset_num_' + str(self.goldset_num))

        data_path = path.join(base_path, 'data')

        query_path = path.join(data_path, 'queries')
        makedirs(query_path) if not path.exists(query_path) else None

        goldset_path = path.join(data_path, 'goldsets', self.level)
        makedirs(goldset_path) if not path.exists(goldset_path) else None

        d = {}
        d['query'] = query_path
        d[self.level] = goldset_path
        d['data'] = data_path
        d['base'] = base_path
        return d

    def load_ids(self):
        fname = path.join(self.path_dict['data'], self.level+'_ids.txt')
        with open(fname) as f:
            return [idx.strip() for idx in f]
