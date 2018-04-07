from git import Repo, GitCommandError, GitCmdObjectDB
import re
from os import path,remove
from typed_ast import ast3,ast27
import Util
import sys
from collections import defaultdict
import logging
# import click

logging.basicConfig(format='%(asctime)s : %(levelname)s : ' +
                    '%(name)s : %(funcName)s : %(message)s')
logger = logging.getLogger('pfl.main')


class RepoParser():
    def __init__(self, repo_path, prev,current,*issue_keyword):
        self.repo = Repo(repo_path, odbt=GitCmdObjectDB)
        self._package = None
        self.issue_keyword = issue_keyword
        self.version = (prev,current)
        self.folders = Util.create_folders([x for x in repo_path.split('/') if x][-1] + '_'+ '-'.join([prev,current]))
        self._id_dict = None
        fh = logging.FileHandler(filename=path.join(self.folders['data'],'logs.txt'))
        fh.setLevel(logging.WARNING)
        logger.addHandler(fh)

        if 'master' in self.repo.heads:
            if self.repo.active_branch != 'master':
                self.repo.heads.master.checkout()
        else:
            remote = self.repo.remote()
            remote.fetch()
            self.repo.create_head('master', remote.refs.master)
            self.repo.heads.master.set_tracking_branch(remote.refs.master)
            self.repo.heads.master.checkout()
            self.parent_module_dir = None
            # checkout to master.

    def generate_issueID_commitID_map(self,prev = None,current=None):
        version = (prev,current) if prev and current else self.version
        pattern = re.compile('{types} #(\d+)'.format(types='|'.join(self.issue_keyword)))
        d = defaultdict(list)
        commits = self.repo.iter_commits(
            '{prev}...{current}'.format(prev=version[0], current=version[1]))
        file = path.join(self.folders['data'], 'Issue_Commit_Map.txt')
        remove(file) if path.exists(file) else None
        for commit in commits:
            m = pattern.search(commit.message.lower())
            if m:
                issueID = m.group(1)
                commitID = commit.hexsha
                d[issueID].append(commitID)
        with open(file, 'a+') as f:
            for issueID, commitIDs in d.items():
                content = ' '.join([issueID, ' '.join(commitIDs), '\r\n'])
                f.write(content)
        logger.info('issueID commitID map generated.')
        self._id_dict = d

    def generate_queries(self):
        if not self._id_dict:
            logger.info("You need to run 'generate_issueID_commitID_map' at first.")
            return
        pattern = re.compile(r'\n')
        for issueID, commitIDs in self._id_dict.items():
            for i, commitID in enumerate(commitIDs):
                commit = self.repo.commit(commitID)
                with open(path.join(self.folders['query'], '{issueID}_description_{i}.txt'.format(issueID=issueID, i=i)), 'w') as f:
                    short = pattern.split(commit.message)[0]
                    long = commit.message
                    f.write('\r\n'.join([short, long]))
        logger.info('queries generated.')



    def generate_goldsets(self):
        if not self._id_dict:
            logger.info("You need to run 'generate_issueID_commitID_map' at first.")
            return
        for issueID, commitIDs in self._id_dict.items():
            class_set,method_set = set(),set()
            for commitID in commitIDs:
                commit = self.repo.commit(commitID)
                try:
                    prev_commit = commit.parents[-1]
                except IndexError:
                    logger.warning('Commit {0} has not parent commit.'.format(commitID))
                    continue
                diffs = self.repo.git.diff(prev_commit, commit, '--diff-filter=AM').strip().split('diff --git ')[1:]
                # only care about new & modified files

                for diff in diffs:
                    m = diff.split('@@')
                    if len(m) > 1:
                        try:
                            file_path = m[0].strip().split('\n')[0].split(' ')[1].split('b/')[1]
                        except IndexError:
                            logger.warning('Diff extraction warning:{0}'.format(m[0]))
                        if not self._package:
                            self._package = self._find_package(commit, file_path)
                        if self._package and self._package in file_path and file_path.endswith('.py'):
                            changes = [x.strip().split(' ')[1] for i, x in enumerate(m) if i % 2]
                            c_set,m_set = self.extract_class_and_method(commit,file_path, changes)
                            package_path = '.'.join(file_path[file_path.find(self._package):][:-3].split('/'))
                            for c in c_set:
                                c_name = '.'.join([package_path, c])
                                class_set.add(c_name)
                            for m in m_set:
                                m_name = '.'.join([package_path, m])
                                method_set.add(m_name)
            if class_set:
                with open(path.join(self.folders['class'],issueID+'.txt'),'a+') as f:
                    [f.write(c+'\n') for c in class_set]
            if method_set:
                with open(path.join(self.folders['method'],issueID+'.txt'),'a+') as f:
                    [f.write(m + '\n') for m in method_set]
        logger.info('goldset generated.')

    def extract_class_and_method(self, commit,file_path, changes):
        src_path = ':'.join([commit.hexsha, file_path])
        content = self.repo.git.show(src_path)
        class_set = set()
        method_set = set()
        nodes = None
        try:
            nodes = ast27.parse(content).body
            ast = ast27
        except Exception:
            logger.warning('Fail to parse {src} with Py2.7 AST.'.format(src=src_path))
            nodes = ast3.parse(content).body
            ast = ast3
        finally:
            if nodes:
                for change in changes:
                    t = change.split(',')
                    if len(t) > 1:
                        start_line, count = int(t[0]),int(t[1])
                        end_line = start_line + count - 1
                        actual_start_line = start_line + 3 if start_line > 1 else start_line
                        actual_end_line = end_line - 3 if content.count('\n') != end_line else end_line

                        start_i = Util.obj_binary_search(nodes, 'lineno', actual_start_line)
                        end_i = Util.obj_binary_search(nodes, 'lineno', actual_end_line)
                        
                        for node in nodes[start_i:end_i+1]:
                            if node.__class__ == ast.FunctionDef:
                                
                                method_set.add(node.name)
                                
                            elif node.__class__ == ast.ClassDef:
                                class_set.add(node.name)
                                sub_nodes = node.body
                                sub_start_i = Util.obj_binary_search(sub_nodes,'lineno',actual_start_line)
                                sub_end_i = Util.obj_binary_search(sub_nodes,'lineno',actual_end_line)
                                for sub_node in sub_nodes[sub_start_i:sub_end_i+1]:
                                    if sub_node.__class__ == ast.FunctionDef:
                                        method_set.add('.'.join([node.name,sub_node.name]))
            else:
                logger.warning('Fail to parse {src} with Py3/Py2.7 AST hence pass.'.format(src=src_path))
            return class_set,method_set

    def _find_package(self, commit, file_path):
        index = file_path.find('/')
        while index > -1:
            try:
                cmp_str = file_path[:index]
                r = self.repo.git.show(':'.join([commit.hexsha, cmp_str + '/__init__.py']))
                # find package_name by detect if __init__.py exist
                if r:
                    return cmp_str.split('/')[-1]

            except GitCommandError:
                index = file_path.find('/', index + 1)

if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) < 3:
        logger.info('Command Format:file_path prev current issue_keywords(optional)') 
    else:
        parser = RepoParser(*args)
        parser.generate_issueID_commitID_map()
        parser.generate_queries()
        parser.generate_goldsets()


