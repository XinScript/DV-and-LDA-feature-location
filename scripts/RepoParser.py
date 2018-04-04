from git import Repo, GitCommandError, GitCmdObjectDB
import re
import os
import shutil
from typed_ast import ast3,ast27

class RepoParser():
    def __init__(self, path, name,prev,current):
        self.repo = Repo(path, odbt=GitCmdObjectDB)
        self.package = None
        self.version = (prev,current)
        self.folders = self._create_folders(name)


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

    def _create_folders(self, name):
        data_path = os.path.join('../datas', name+'-'.join([str(i) for i in self.version]))
        os.makedirs(data_path) if not os.path.exists(data_path) else None

        query_path = os.path.join(data_path, 'queries')
        os.makedirs(query_path) if not os.path.exists(query_path) else None

        goldset_class_path = os.path.join(data_path, 'goldsets', 'class')
        os.makedirs(goldset_class_path) if not os.path.exists(
            goldset_class_path) else None

        goldset_method_path = os.path.join(data_path, 'goldsets', 'method')
        os.makedirs(goldset_method_path) if not os.path.exists(
            goldset_method_path) else None

        d = {}
        d['project'] = data_path
        d['query'] = query_path
        d['class'] = goldset_class_path
        d['method'] = goldset_method_path
        return d

    def generate_issueID_commitID_map(self,ITS):
        pattern = re.compile('{types} #(\d+)'.format(types='|'.join(ITS)))
        d = {}
        commits = self.repo.iter_commits(
            '{prev}...{current}'.format(prev=self.version[0], current=self.version[1]))
        file = os.path.join(self.folders['project'], 'Issue_Commit_Map.txt')
        os.remove(file) if os.path.exists(file) else None
        for commit in commits:
            m = pattern.search(commit.message.lower())
            if m:
                issueID = m.group(1)
                commitID = commit.hexsha
                if issueID in d:
                    d[issueID].append(commitID)
                else:
                    d[issueID] = [commitID]
        with open(file, 'a+') as f:
            for issueID, commitIDs in d.items():
                content = ' '.join([issueID, ' '.join(commitIDs), '\r\n'])
                f.write(content)
        print('map generated.')
        return d

    def generate_queries(self, id_dict):
        pattern = re.compile(r'\n')
        c = 0
        n = ''
        for issueID, commitIDs in id_dict.items():
            if len(commitIDs) > c:
                c = len(commitIDs)
                n = issueID
            for i, commitID in enumerate(commitIDs):
                commit = self.repo.commit(commitID)
                with open(os.path.join(self.folders['query'], 'description_{i}_{issueID}.txt'.format(issueID=issueID, i=i)), 'w') as f:
                    short = pattern.split(commit.message)[0]
                    long = commit.message
                    f.write('\r\n'.join([short, long]))
        print('queries generated.')
        # print('Issue with most commits:' + n)

    def generate(self,ITS):
        id_dict = self.generate_issueID_commitID_map(ITS)
        print(len(id_dict))
        self.generate_queries(id_dict)
        self.generate_goldsets(id_dict)

    def generate_goldsets(self, id_dict):
        for issueID, commitIDs in id_dict.items():
            class_dict,method_dict = {},{}
            for commitID in commitIDs:
                commit = self.repo.commit(commitID)
                try:
                    prev_commit = commit.parents[-1]
                except IndexError:
                    continue
                diffs = self.repo.git.diff(prev_commit, commit, '--diff-filter=AM').strip().split('diff --git ')[1:]
                # only care about new & modified files

                for diff in diffs:
                    
                    m = diff.split('@@')
                    if len(m) > 1:
                        try:
                            file_path = m[0].strip().split('\n')[0].split(' ')[1].split('b/')[1]
                        except IndexError:
                            continue

                        if not self.package:
                            self._find_package(commit, file_path)
                        if self.package and self.package in file_path and file_path.endswith('.py'):
                            changes = [x.strip().split(' ')[1] for i, x in enumerate(m) if i % 2]
                            c_d,m_d = self.extract_class_and_method(commit,file_path, changes)
                            package_path = '.'.join(file_path[file_path.find(self.package):][:-3].split('/'))
                            for c in c_d.keys():
                                c_name = '.'.join([package_path, c])
                                class_dict[c_name] = True
                            for m in m_d.keys():
                                m_name = '.'.join([package_path, m])
                                method_dict[m_name] = True
            if class_dict:
                with open(os.path.join(self.folders['class'],issueID+'.txt'),'a+') as f:
                    [f.write(c+'\n') for c in class_dict.keys()]
            if method_dict:
                with open(os.path.join(self.folders['method'],issueID+'.txt'),'a+') as f:
                    [f.write(m + '\n') for m in method_dict.keys()]

    def extract_class_and_method(self, commit,file_path, changes):
        content = self.repo.git.show(':'.join([commit.hexsha, file_path]))
        class_dict = {}
        method_dict = {}
        nodes = None
        try:
            nodes = ast27.parse(content).body
            ast = ast27
        except Exception:
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

                        start_i = self._range_search(nodes, 'lineno', actual_start_line)
                        end_i = self._range_search(nodes, 'lineno', actual_end_line)
                        for node in nodes[start_i:end_i+1]:
                            if node.__class__ == ast.FunctionDef:
                                
                                method_dict[node.name] = True
                                
                            elif node.__class__ == ast.ClassDef:
                                class_dict[node.name] = True
                                sub_nodes = node.body
                                sub_start_i = self._range_search(sub_nodes,'lineno',actual_start_line)
                                sub_end_i = self._range_search(sub_nodes,'lineno',actual_end_line)
                                for sub_node in sub_nodes[sub_start_i:sub_end_i+1]:
                                    if sub_node.__class__ == ast.FunctionDef:
                                        method_dict['.'.join([node.name,sub_node.name])] = True
            return class_dict,method_dict

    def _range_search(self, objs, field, target):
        if target > getattr(objs[-1], field):
        # if not objs or target > getattr(objs[-1], field):
            return len(objs)-1
        lo, hi = 0, len(objs) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if target < getattr(objs[mid], field):
                hi = mid - 1
            elif target > getattr(objs[mid], field):
                lo = mid + 1
            else:
                return mid
        return lo

    def _find_package(self, commit, file_path):
        
        index = file_path.find('/')
        while index > -1:
            try:
                cmp_str = file_path[:index]
                r = self.repo.git.show(':'.join([commit.hexsha, cmp_str + '/__init__.py']))
                # find package_name by
                if r:
                    self.package = cmp_str.split('/')[-1]
                    return

            except GitCommandError:
                index = file_path.find('/', index + 1)

p = RepoParser('../sources/sage', 'sage',5.0,5.5)
p.generate(['trac'])
