import logging
from os import path, makedirs
from git import Repo, GitCmdObjectDB
from collections import defaultdict

from . import CONFIG
from . import error

logger = logging.getLogger('plt.project')

logger.setLevel(CONFIG.LOG_LEVEL)


class Project(object):

    def __init__(self, name):
        self.name = name
        self.path = path.join(CONFIG.BASE_PATH, self.name)

class GitProject(Project):

    def __init__(self, name, gen_rule, release_interval, issue_keywords=[]):
        super().__init__(name)
        self.release_interval = tuple([str(x) for x in release_interval])
        self.issue_keywords = issue_keywords
        self.path_dict = self.load_dirs()
        self.gen_rule = gen_rule

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
            raise error.GitNotFoundError('It is not a git directory')

        else:
            super().__init__(name, kind, release_interval, issue_keywords)
            self.src_path = src_path
            self.repo = Repo(src_path, odbt=GitCmdObjectDB)
