from os import path, makedirs
import Util
import Config
import Error
from git import Repo, GitCmdObjectDB
import pickle
from collections import defaultdict
import logging

logger = logging.getLogger('plt.project')

logger.setLevel(Config.LOG_LEVEL)


class Project(object):

    def __init__(self, name):
        self.name = name
        self.path = path.join(Config.BASE_PATH, self.name)

    def save(self):
        with open(path.join(self.path, Config.PROJECT_EXT), 'wb') as f:
            pickle.dump(self, f)

    @staticmethod
    def load(name):
        with open(path.join(Config.BASE_PATH, name, Config.PROJECT_EXT), 'rb') as f:
            return pickle.load(f)


class GitProject(Project):

    def __init__(self, name, gen_rule, release_interval, issue_keywords=[]):
        super().__init__(name)
        self.release_interval = tuple([str(x) for x in release_interval])
        self.issue_keywords = issue_keywords
        self.path_dict = self.load_dirs()
        self.gen_rule = gen_rule

    def save(self):
        with open(path.join(self.path_dict['base'], Config.PROJECT_EXT), 'wb') as f:
            pickle.dump(self, f)

    @staticmethod
    def load(name, release_interval):
        with open(path.join(Config.BASE_PATH, name, '-'.join([str(x) for x in release_interval]), Config.PROJECT_EXT), 'rb') as f:
            return pickle.load(f)

    def load_dirs(self):

        version_path = path.join(self.path, '-'.join(self.release_interval))

        data_path = path.join(version_path, 'data')

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
        d['base'] = version_path
        return d

    def load_ids(self):
        fname = path.join(self.path_dict['data'], 'ids.txt')
        if self.gen_rule == 'by_commit':
            with open(fname) as f:
                return [idx.strip() for idx in f]
        elif self.gen_rule == 'by_issue':
            with open(fname) as f:
                return {issue_id: commit_ids for issue_id, *commit_ids in [line.strip().split() for line in f]}
        else:
            pass

    def load_goldsets(self,level):
        if level not in ['class','method']:
            logger.info('{} while loading goldset:level has to be one of "method" or "class"'.format(self.name))
        else:            
            d = defaultdict(set)

            ids = self.load_ids()

            for idx in ids:
                fname = path.join(path.join(self.path_dict[level]), idx + '.txt')
                if path.exists(fname):
                    with open(fname) as f:
                        for line in f:
                            d[idx].add(line.strip().split('.')[0]+'.py')
            return d


class LocalGitProject(GitProject):
    def __init__(self, name, kind, src_path, release_interval, issue_keywords):
        if not path.exists(src_path):
            raise FileNotFoundError('Directory not exists.')

        elif not path.exists(path.join(src_path, '.git')):
            raise Error.GitNotFoundError('It is not a git directory')

        else:
            super().__init__(name, kind, release_interval, issue_keywords)
            self.src_path = src_path
            self.repo = Repo(src_path, odbt=GitCmdObjectDB)
