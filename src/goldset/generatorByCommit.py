'''

This module is the implementation of goldset generators against using "commit" as basic unit.

'''

from os import path, remove
from .generator import GoldsetGenerator
import logging
from common import CONFIG
from common import util


share_logger = util.get_logger('goldset')

class CommitGoldsetGenerator(GoldsetGenerator):
    def __init__(self, project):
        super().__init__(project)

    def generate_ids(self):

        commits = [commit.hexsha for commit in self.project.repo.iter_commits('{0}...{1}'.format(*self.project.release_interval))]

        for commit in commits:
            self._generate_single_id(commit)

        self.logger.info('commit ids generated.')

    def generate_queries(self):
        ids = self.project.load_ids()

        for idx in ids:
            commit = self.project.repo.commit(idx)
            self._generate_single_query(commit)

        self.logger.info('queries generated.')

    def generate_goldsets(self):

        ids = self.project.load_ids()

        for idx in ids:
            commit = self.project.repo.commit(idx)
            self._generate_single_goldset(commit)

    def generate_goldsets_directly(self,ref_type='LATEST_COMMIT'):
        share_logger.info('{}'.format(self.project.name))
        
        if ref_type == 'LATEST_TAG':
            if self.project.repo.tags:
                start_commit = self.project.repo.tags[-1].commit
                self.logger.info('use latest tag {tag} as start ref.'.format(tag=start_commit.name))
            else:    
                start_commit = self.project.repo.head.commit
                self.logger.info('No tags found thus use last commit {id} as start ref.'.format(id=start_commit.hexsha))
        else:
            start_commit = self.project.repo.head.commit
            self.logger.info('use last commit {id} as start ref.'.format(id=start_commit.hexsha))

        share_logger.info('ref:{}'.format(start_commit.hexsha))
        commit = start_commit
        goldset_count = 0
        commit_count = 0
        while commit.parents:
            idx = self._generate_single_goldset(commit)
            commit_count+=1
            if idx:
                goldset_count += 1
                self._generate_single_id(commit)
                self._generate_single_query(commit)
                if goldset_count == self.project.goldset_num:
                    self.logger.info('{} goldsets have been generated.'.format(goldset_count))
                    share_logger.info('goldset:{}'.format(goldset_count))
                    share_logger.info('commit visited:{}\n'.format(commit_count))
                    return
            commit = self.project.repo.commit(commit.hexsha + '~1')

        self.logger.info('run through all commits but got only {} goldsets.'.format(goldset_count))
        share_logger.info('goldset:{}'.format(goldset_count))
        share_logger.info('commit visited:{}\n'.format(commit_count))
