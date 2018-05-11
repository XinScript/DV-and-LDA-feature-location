import logging
from os import path, makedirs
from git import Repo, GitCmdObjectDB
from collections import defaultdict

from . import CONFIG
from . import error


class Project(object):
    def __init__(self, name):
        self.name = name
        self.path = path.join(CONFIG.BASE_PATH, 'plt', self.name)


class GitProject(Project):

    def __init__(self, name, src_path):
        if not path.exists(src_path):
            raise FileNotFoundError(src_path)

        elif not path.exists(path.join(src_path, '.git')):
            raise error.GitNotFoundError('It is not a git directory')

        else:
            super().__init__(name)
            self.src_path = src_path
            self.repo = Repo(src_path, odbt=GitCmdObjectDB)
            self.path_dict = self.load_dirs()

    def load_goldsets(self, level):
        if level not in ['class', 'method','file']:
            raise NotImplementedError
        else:
            d = defaultdict(set)

            ids = self.load_ids()

            if level == 'file':
                for idx in ids:
                    fname = path.join(path.join(self.path_dict['class']), idx + '.txt')
                    if path.exists(fname):
                        with open(fname) as f:
                            for line in f:
                                d[idx].add(line.strip().split('.')[0] + '.py')
                    
                    fname = path.join(path.join(self.path_dict['method']), idx + '.txt')
                    if path.exists(fname):
                        with open(fname) as f:
                            for line in f:
                                d[idx].add(line.strip().split('.')[0] + '.py')

            else:             
                for idx in ids:
                    fname = path.join(path.join(self.path_dict[level]), idx + '.txt')
                    if path.exists(fname):
                        with open(fname) as f:
                            for line in f:
                                d[idx].add(line.strip().split('.')[0] + '.py')
            return d


class IssuGitProject(GitProject):

    def __init__(self, name, src_path, by_release, issue_keywords):
        super().__init__(name, src_path)
        self.by_release = tuple([str(x) for x in by_release])
        self.issue_keywords = issue_keywords
        self.ref = self.repo.commit(by_release[1])

    def load_dirs(self):

        base_path = path.join(self.path, '-'.join(self.by_release))

        data_path = path.join(base_path, 'data')

        query_path = path.join(data_path, 'queries')
        makedirs(query_path) if not path.exists(query_path) else None

        goldset_class_path = path.join(data_path, 'goldsets', 'class')
        makedirs(goldset_class_path) if not path.exists(
            goldset_class_path) else None

        goldset_method_path = path.join(data_path, 'goldsets', 'method')
        makedirs(goldset_method_path) if not path.exists(
            goldset_method_path) else None

        d = {}
        d['query'] = query_path
        d['class'] = goldset_class_path
        d['method'] = goldset_method_path
        d['data'] = data_path
        d['base'] = base_path
        return d

    def load_ids(self):
        fname = path.join(self.path_dict['data'], 'ids.txt')
        with open(fname) as f:
            return {issue_id: commit_ids for issue_id, *commit_ids in [line.strip().split() for line in f]}


class CommitGitProject(GitProject):
    def __init__(self, name, src_path, goldset_num=50):
        self.goldset_num = goldset_num
        super().__init__(name, src_path)
        self.ref = self.repo.head.commit

    def load_dirs(self):

        base_path = path.join(self.path, 'goldset_num_' + str(self.goldset_num))

        data_path = path.join(base_path, 'data')

        query_path = path.join(data_path, 'queries')
        makedirs(query_path) if not path.exists(query_path) else None

        goldset_class_path = path.join(data_path, 'goldsets', 'class')
        makedirs(goldset_class_path) if not path.exists(
            goldset_class_path) else None

        goldset_method_path = path.join(data_path, 'goldsets', 'method')
        makedirs(goldset_method_path) if not path.exists(
            goldset_method_path) else None

        d = {}
        d['query'] = query_path
        d['class'] = goldset_class_path
        d['method'] = goldset_method_path
        d['data'] = data_path
        d['base'] = base_path
        return d

    def load_ids(self):
        fname = path.join(self.path_dict['data'], 'ids.txt')
        with open(fname) as f:
            return [idx.strip() for idx in f]
