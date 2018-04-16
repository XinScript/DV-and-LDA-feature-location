import re
from os import path,remove
from collections import defaultdict
from .generator import GoldsetGenerator

class IssueGoldsetGenerator(GoldsetGenerator):
    def __init__(self, project):
        super().__init__(project)

    def generate_ids(self):

        map_path = path.join(self.project.path_dict['data'], 'ids.txt')

        remove(map_path) if path.exists(map_path) else None

        pattern = re.compile('{types} #(\d+)'.format(types='|'.join(self.project.issue_keywords)))

        d = defaultdict(list)

        commits = self.project.repo.iter_commits('{0}...{1}'.format(*self.project.release_interval))

        for commit in commits:
            m = pattern.search(commit.message.lower())

            if m:
                d[m.group(1)].append(commit.hexsha)

        with open(map_path, 'w') as f:
            for issueID, commitIDs in d.items():
                content = ' '.join([issueID, ' '.join(commitIDs), '\r\n'])
                f.write(content)

        self.logger.info('issueID commitID map generated.')

    def generate_queries(self):

        idd = self.project.load_ids()

        if not idd:
            self.logger.info(
                "You need to run 'generate_issueID_commitID_map' at first.")
            return

        pattern = re.compile(r'\n')

        for issueID, commitIDs in idd.items():
            for i, commitID in enumerate(commitIDs):
                commit = self.project.repo.commit(commitID)
                with open(path.join(self.project.path_dict['query'], '{issueID}_{i}.txt'.format(issueID=issueID, i=i)), 'w') as f:
                    short = pattern.split(commit.message)[0]
                    long = commit.message
                    f.write('\r\n'.join([short, long]))

        self.logger.info('queries generated.')

    def generate_goldsets(self):

        idd = self.project.load_ids()

        if not idd:
            self.logger.info(
                "You need to run 'generate_issueID_commitID_map' at first.")
            return

        for issueID, commitIDs in idd.items():
            class_set, method_set = set(), set()
            for commitID in commitIDs:
                commit = self.project.repo.commit(commitID)
                c_set, m_set = self.extract_goldset_from_commit(commit)
                for c in c_set:
                    class_set.add(c)

                for m in m_set:
                    method_set.add(m)

            if class_set:
                with open(path.join(self.project.path_dict['class'], issueID + '.txt'), 'a+') as f:
                    [f.write(c + '\n') for c in class_set]

            if method_set:
                with open(path.join(self.project.path_dict['method'], issueID + '.txt'), 'a+') as f:
                    [f.write(m + '\n') for m in method_set]

        self.logger.info('goldset generated.')
