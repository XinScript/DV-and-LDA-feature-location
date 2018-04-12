import re
import sys
import logging
from git import GitCommandError
from os import path, remove
from typed_ast import ast3, ast27
from collections import defaultdict
from Project import LocalGitProject, GitProject
import Util
from Error import *

logging.basicConfig(format='%(asctime)s : %(levelname)s : ' +
                    '%(name)s : %(funcName)s : %(message)s')

class GoldsetGenerator():
    def __init__(self, project):
        if not isinstance(project, GitProject):
            raise NotGitProjectError()
        else:
            self.project = project

            self.logger = logging.getLogger('.'.join(['pfl.goldset', self.project.name]))
            fh = logging.FileHandler(filename=path.join(project.path, 'log.txt'))
            fh.setLevel(logging.DEBUG)
            self.logger.addHandler(fh)

            if 'master' in self.project.repo.heads:
                if self.project.repo.active_branch != 'master':
                    self.project.repo.heads.master.checkout()
            else:
                remote = self.project.repo.remote()
                remote.fetch()
                self.project.repo.create_head('master', remote.refs.master)
                self.project.repo.heads.master.set_tracking_branch(remote.refs.master)
                self.project.repo.heads.master.checkout()
                # checkout to master.

    def generate(self):
        for version in self.project.versions:
            self.generate_ids(version)
            self.generate_queries(version)
            self.generate_goldsets(version)

    def _find_package(self, commit, file_path):
        index = file_path.find('/')

        while index > -1:
            try:
                cmp_str = file_path[:index]
                r = self.project.repo.git.show(
                    ':'.join([commit.hexsha, cmp_str + '/__init__.py']))
                # find package_name by detect if __init__.py exist

                if r:
                    return cmp_str.split('/')[-1]
            except GitCommandError:
                pass

            finally:
                index = file_path.find('/', index + 1)
    def extract_goldset_from_commit(self, commit):
        class_set = set()
        method_set = set()
        if len(commit.parents):
            prev_commit = commit.parents[-1]
            diffs = self.project.repo.git.diff(prev_commit, commit, '--diff-filter=AM').strip().split('diff --git ')[1:]
            for diff in diffs:
                m = diff.split('@@')
                if len(m) > 1:
                    try:
                        file_path = m[0].strip().split('\n')[0].split(' ')[1].split('b/')[1]
                        if file_path.endswith('.py'):
                            changes = [x.strip().split(' ')[1] for i, x in enumerate(m) if i % 2]
                            src_path = ':'.join([commit.hexsha, file_path])
                            content = self.project.repo.git.show(src_path)
                            nodes = None

                            try:
                                nodes = ast27.parse(content).body
                                ast = ast27
                            except Exception:
                                self.logger.warning(
                                    'Fail to parse {src} with Py2.7 AST.'.format(src=src_path))
                                nodes = ast3.parse(content).body
                                ast = ast3
                            finally:
                                if nodes:
                                    for change in changes:
                                        t = change.split(',')
                                        if len(t) > 1:
                                            start_line, count = int(t[0]), int(t[1])
                                            end_line = start_line + count - 1
                                            actual_start_line = start_line + 3 if start_line > 1 else start_line
                                            actual_end_line = end_line - 3 if content.count('\n') != end_line else end_line
                                            start_i = Util.obj_binary_search(
                                                nodes, 'lineno', actual_start_line)
                                            end_i = Util.obj_binary_search(
                                                nodes, 'lineno', actual_end_line)

                                            for node in nodes[start_i:end_i + 1]:
                                                if node.__class__ == ast.FunctionDef:

                                                    method_set.add('.'.join([file_path[:-3],node.name]))

                                                elif node.__class__ == ast.ClassDef:
                                                    class_set.add('.'.join([file_path[:-3], node.name]))
                                                    sub_nodes = node.body
                                                    sub_start_i = Util.obj_binary_search(
                                                        sub_nodes, 'lineno', actual_start_line)
                                                    sub_end_i = Util.obj_binary_search(
                                                        sub_nodes, 'lineno', actual_end_line)

                                                    for sub_node in sub_nodes[sub_start_i:sub_end_i + 1]:
                                                        if sub_node.__class__ == ast.FunctionDef:
                                                            method_set.add('.'.join([file_path[:-3],node.name, sub_node.name]))
                                
                                else:
                                    self.logger.warning('Fail to parse {src} with Py3/Py2.7 AST hence pass.'.format(src=src_path))
                
                    except Exception:
                        self.logger.warning('Error occurs while handling diff info:{0}'.format(m[0]))
        return class_set, method_set


class IssueGoldsetGenerator(GoldsetGenerator):
    def __init__(self, project):
        super().__init__(project)

    def generate_ids(self, version):

        path_dict = self.project.path_dict[version]

        map_path = path.join(path_dict['data'], 'ids.txt')

        remove(map_path) if path.exists(map_path) else None

        pattern = re.compile('{types} #(\d+)'.format(types='|'.join(self.project.issue_keywords)))

        d = defaultdict(list)

        commits = self.project.repo.iter_commits('{0}...{1}'.format(*version))

        for commit in commits:
            m = pattern.search(commit.message.lower())

            if m:
                d[m.group(1)].append(commit.hexsha)

        with open(map_path, 'a+') as f:
            for issueID, commitIDs in d.items():
                content = ' '.join([issueID, ' '.join(commitIDs), '\r\n'])
                f.write(content)

        self.logger.info('issueID commitID map generated.')

    def load_ids(self, version):
        path_dict = self.project.path_dict[version]

        d = defaultdict(list)

        for line in open(path.join(path_dict['data'], 'ids.txt')):
            m = line.split()
            issueID = m[0]
            d[issueID].extend(m[1:])

        self.logger.info('Sucessfully load the map')

        return d

    def generate_queries(self, version):

        path_dict = self.project.path_dict[version]

        idd = self.load_ids(version)

        if not idd:
            self.logger.info(
                "You need to run 'generate_issueID_commitID_map' at first.")
            return

        pattern = re.compile(r'\n')
        
        for issueID, commitIDs in idd.items():
            for i, commitID in enumerate(commitIDs):
                commit = self.project.repo.commit(commitID)
                with open(path.join(path_dict['query'], '{issueID}_description_{i}.txt'.format(issueID=issueID, i=i)), 'w') as f:
                    short = pattern.split(commit.message)[0]
                    long = commit.message
                    f.write('\r\n'.join([short, long]))

        self.logger.info('queries generated.')

    def generate_goldsets(self, version):

        path_dict = self.project.path_dict[version]

        idd = self.load_ids(version)

        if not idd:
            self.logger.info(
                "You need to run 'generate_issueID_commitID_map' at first.")
            return

        for issueID, commitIDs in idd.items():
            class_set, method_set = set(), set()
            for commitID in commitIDs:
                commit = self.project.repo.commit(commitID)
                c_set,m_set = self.extract_goldset_from_commit(commit)
                for c in c_set:
                    class_set.add(c)

                for m in m_set:
                    method_set.add(m)


            if class_set:
                with open(path.join(path_dict['class'], issueID + '.txt'), 'a+') as f:
                    [f.write(c + '\n') for c in class_set]

            if method_set:
                with open(path.join(path_dict['method'], issueID + '.txt'), 'a+') as f:
                    [f.write(m + '\n') for m in method_set]

        self.logger.info('goldset generated.')


class CommitGoldsetGenerator(GoldsetGenerator):
    def __init__(self,project):
        super().__init__(project)
    
    def generate_ids(self,version):

        path_dict = self.project.path_dict[version]

        map_path = path.join(path_dict['data'], 'ids.txt')

        remove(map_path) if path.exists(map_path) else None

        commits = [commit.hexsha for commit in self.project.repo.iter_commits('{0}...{1}'.format(*version))]

        with open(map_path, 'a+') as f:
            for idx in commits:
                content = ''.join([idx, '\n'])
                f.write(content)

        self.logger.info('commit ids generated.')
    
    def load_ids(self,version):
        path_dict = self.project.path_dict[version]

        ids = [idx for idx in open(path.join(path_dict['data'],'ids.txt'))]

        self.logger.info('Sucessfully load the ids')

        return ids
    
    def generate_queries(self,version):
        path_dict = self.project.path_dict[version]

        ids = self.load_ids(version)

        if not ids:
            self.logger.info(
                "You need to run 'generate_issueID_commitID_map' at first.")
            return

        for idx in ids:
            commit = self.project.repo.commit(idx)
            with open(path.join(path_dict['query'], '{idx}_description.txt'.format(idx=idx)), 'w') as f:
                f.write(''.join([commit.message,'\n']))

        self.logger.info('queries generated.')
    
    def generate_goldsets(self,version):

        path_dict = self.project.path_dict[version]

        ids = self.load_ids(version)

        if not ids:
            self.logger.info(
                "You need to run 'generate_issueID_commitID_map' at first.")
            return

        for idx in ids:
            commit = self.project.repo.commit(idx)
            c_set,m_set = self.extract_goldset_from_commit(commit)
            if c_set:
                with open(path.join(path_dict['class'], idx + '.txt'), 'a+') as f:
                    [f.write(c + '\n') for c in c_set]

            if m_set:
                with open(path.join(path_dict['method'], idx + '.txt'), 'a+') as f:
                    [f.write(m + '\n') for m in m_set]
            


