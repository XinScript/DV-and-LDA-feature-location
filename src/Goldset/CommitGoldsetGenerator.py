from os import path,remove
from .GoldsetGenerator import GoldsetGenerator


class CommitGoldsetGenerator(GoldsetGenerator):
    def __init__(self, project):
        super().__init__(project)

    def generate_ids(self, version):

        path_dict = self.project.path_dict[version]

        map_path = path.join(path_dict['data'], 'ids.txt')

        remove(map_path) if path.exists(map_path) else None

        commits = [commit.hexsha for commit in self.project.repo.iter_commits('{0}...{1}'.format(*version))]

        with open(map_path, 'a+') as f:
            for idx in commits:
                content = ''.join([idx, '\n'])
                f.write(content)

        self.logger.info('commit ids generated.')

    def generate_queries(self, version):
        path_dict = self.project.path_dict[version]

        ids = self.project.load_ids(version)

        if not ids:
            self.logger.info(
                "You need to run 'generate_issueID_commitID_map' at first.")
            return

        for idx in ids:
            commit = self.project.repo.commit(idx)
            with open(path.join(path_dict['query'], '{idx}_description.txt'.format(idx=idx)), 'w') as f:
                f.write(''.join([commit.message, '\n']))

        self.logger.info('queries generated.')

    def generate_goldsets(self, version):

        path_dict = self.project.path_dict[version]

        ids = self.project.load_ids(version)

        if not ids:
            self.logger.info(
                "You need to run 'generate_issueID_commitID_map' at first.")
            return

        for idx in ids:
            commit = self.project.repo.commit(idx)
            c_set, m_set = self.extract_goldset_from_commit(commit)
            if c_set:
                with open(path.join(path_dict['class'], idx + '.txt'), 'a+') as f:
                    [f.write(c + '\n') for c in c_set]

            if m_set:
                with open(path.join(path_dict['method'], idx + '.txt'), 'a+') as f:
                    [f.write(m + '\n') for m in m_set]
