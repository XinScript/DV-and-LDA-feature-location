from git import Repo, GitCommandError, GitCmdObjectDB
import re
from os import path,remove
from typed_ast import ast3,ast27
import Util
import sys
from collections import defaultdict
import logging
from Project import Project

logging.basicConfig(format='%(asctime)s : %(levelname)s : ' +
                    '%(name)s : %(funcName)s : %(message)s')



class GoldsetGenerator():
    def __init__(self, project):
        self.project = project
        self.repo = Repo(project.repo_path, odbt=GitCmdObjectDB)
        self.logger = logging.getLogger('.'.join(['pfl.goldset',self.project.name]))
        fh = logging.FileHandler(filename=path.join(project.path,'log.txt'))
        fh.setLevel(logging.DEBUG)
        self.logger.addHandler(fh)

        if 'master' in self.repo.heads:
            if self.repo.active_branch != 'master':
                self.repo.heads.master.checkout()
        else:
            remote = self.repo.remote()
            remote.fetch()
            self.repo.create_head('master', remote.refs.master)
            self.repo.heads.master.set_tracking_branch(remote.refs.master)
            self.repo.heads.master.checkout()
            # checkout to master.
    def generate(self):
        for version in self.project.versions:
            paths = Util.make_dirs(path.join(self.project.path,'-'.join(version)))
            self.generate_issue2commit_map(paths,version)
            self.generate_queries(paths)
            self.generate_goldsets(paths)


    def generate_issue2commit_map(self,paths,version):
        pattern = re.compile('{types} #(\d+)'.format(types='|'.join(self.project.issue_keywords)))
        d = defaultdict(list)
        commits = self.repo.iter_commits('{0}...{1}'.format(*version))
        for commit in commits:
            m = pattern.search(commit.message.lower())
            if m:
                d[m.group(1)].append(commit.hexsha)
        remove(paths['map']) if path.exists(paths['map']) else None
        with open(paths['map'], 'a+') as f:
            for issueID, commitIDs in d.items():
                content = ' '.join([issueID, ' '.join(commitIDs), '\r\n'])
                f.write(content)
        self.logger.info('issueID commitID map generated.')

    def load_idd(self,fpath):
        d = defaultdict(list)
        for line in open(fpath):
                m = line.split()
                issueID = m[0]
                d[issueID].extend(m[1:])
        self.logger.info('Sucessfully load the map')
        return d

    def generate_queries(self,paths):
        idd = self.load_idd(paths['map'])
        if not idd:
            self.logger.info("You need to run 'generate_issueID_commitID_map' at first.")
            return
        pattern = re.compile(r'\n')
        for issueID, commitIDs in idd.items():
            for i, commitID in enumerate(commitIDs):
                commit = self.repo.commit(commitID)
                with open(path.join(paths['query'], '{issueID}_description_{i}.txt'.format(issueID=issueID, i=i)), 'w') as f:
                    short = pattern.split(commit.message)[0]
                    long = commit.message
                    f.write('\r\n'.join([short, long]))
        self.logger.info('queries generated.')

    def generate_goldsets(self,paths):
        idd = self.load_idd(paths['map'])
        if not idd:
            self.logger.info("You need to run 'generate_issueID_commitID_map' at first.")
            return
        for issueID, commitIDs in idd.items():
            class_set,method_set = set(),set()
            for commitID in commitIDs:
                commit = self.repo.commit(commitID)
                try:
                    prev_commit = commit.parents[-1]
                except IndexError:
                    self.logger.warning('Commit {0} has not parent commit.'.format(commitID))
                    continue
                diffs = self.repo.git.diff(prev_commit, commit, '--diff-filter=AM').strip().split('diff --git ')[1:]
                # only care about new & modified files

                for diff in diffs:
                    m = diff.split('@@')
                    if len(m) > 1:
                        try:
                            file_path = m[0].strip().split('\n')[0].split(' ')[1].split('b/')[1]
                            if file_path.endswith('.py'):
                                package = self._find_package(commit, file_path)
                                if package:
                                    changes = [x.strip().split(' ')[1] for i, x in enumerate(m) if i % 2]
                                    c_set,m_set = self.extract_class_and_method(commit,file_path, changes)
                                    package_path = '.'.join(file_path[file_path.find(package):][:-3].split('/'))
                                    for c in c_set:
                                        c_name = '.'.join([package_path, c])
                                        class_set.add(c_name)
                                    for m in m_set:
                                        m_name = '.'.join([package_path, m])
                                        method_set.add(m_name)
                        except Exception:
                            self.logger.warning('Error occurs while handling diff info:{0}'.format(m[0]))
            if class_set:
                with open(path.join(paths['class'],issueID+'.txt'),'a+') as f:
                    [f.write(c+'\n') for c in class_set]
            if method_set:
                with open(path.join(paths['method'],issueID+'.txt'),'a+') as f:
                    [f.write(m + '\n') for m in method_set]
        self.logger.info('goldset generated.')

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
            self.logger.warning('Fail to parse {src} with Py2.7 AST.'.format(src=src_path))
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
                self.logger.warning('Fail to parse {src} with Py3/Py2.7 AST hence pass.'.format(src=src_path))
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
                pass
            finally:
                index = file_path.find('/', index + 1)
                

if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) < 3:
        print('Command Format:file_path prev current issue_keywords(optional)') 
    else:
        project = Project(args[0],['trac'])
        project.add_versions([('5.0','5.1'),('5.1','5.2')])
        parser = GoldsetGenerator(project)
        parser.generate()


