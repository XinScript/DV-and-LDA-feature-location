import re
import sys
import logging
import util
from git import GitCommandError
from os import path, remove
from typed_ast import ast3, ast27
from collections import defaultdict
from project import GitProject
from error import NotGitProjectError

logging.basicConfig(format='%(asctime)s : %(levelname)s : ' +
                    '%(name)s : %(funcName)s : %(message)s')


class GoldsetGenerator():
    def __init__(self, project):
        if not isinstance(project, GitProject):
            raise NotGitProjectError()
        else:
            self.project = project

            self.logger = logging.getLogger(
                '.'.join(['pfl.goldset', self.project.name]))
            fh = logging.FileHandler(filename=path.join(project.path_dict['base'], 'log.txt'))
            fh.setLevel(logging.DEBUG)
            self.logger.addHandler(fh)

            if 'master' in self.project.repo.heads:
                if self.project.repo.active_branch != 'master':
                    self.project.repo.heads.master.checkout()
            else:
                remote = self.project.repo.remote()
                remote.fetch()
                self.project.repo.create_head('master', remote.refs.master)
                self.project.repo.heads.master.set_tracking_branch(
                    remote.refs.master)
                self.project.repo.heads.master.checkout()
                # checkout to master.

    def generate(self):
        self.generate_ids()
        self.generate_queries()
        self.generate_goldsets()

    def find_package(self, commit, file_path):
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
            diffs = self.project.repo.git.diff(
                prev_commit, commit, '--diff-filter=AM').strip().split('diff --git ')[1:]
            for diff in diffs:
                m = diff.split('@@')
                try:
                    if len(m) > 1:
                        file_path = m[0].strip().split(
                            '\n')[0].split(' ')[1].split('b/')[1]
                        if file_path.endswith('.py'):
                            changes = [x.strip().split(' ')[1]
                                       for i, x in enumerate(m) if i % 2]
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
                            if nodes:
                                for change in changes:
                                    t = change.split(',')
                                    if len(t) > 1:
                                        start_line, count = int(
                                            t[0]), int(t[1])
                                        end_line = start_line + count - 1
                                        actual_start_line = start_line + 3 if start_line > 1 else start_line
                                        actual_end_line = end_line - \
                                            3 if content.count(
                                                '\n') != end_line else end_line
                                        start_i = util.obj_binary_search(
                                            nodes, 'lineno', actual_start_line)
                                        end_i = util.obj_binary_search(
                                            nodes, 'lineno', actual_end_line)

                                        for node in nodes[start_i:end_i + 1]:
                                            if node.__class__ == ast.FunctionDef:

                                                method_set.add(
                                                    '.'.join([file_path[:-3], node.name]))

                                            elif node.__class__ == ast.ClassDef:
                                                class_set.add(
                                                    '.'.join([file_path[:-3], node.name]))
                                                sub_nodes = node.body
                                                sub_start_i = util.obj_binary_search(
                                                    sub_nodes, 'lineno', actual_start_line)
                                                sub_end_i = util.obj_binary_search(
                                                    sub_nodes, 'lineno', actual_end_line)

                                                for sub_node in sub_nodes[sub_start_i:sub_end_i + 1]:
                                                    if sub_node.__class__ == ast.FunctionDef:
                                                        method_set.add(
                                                            '.'.join([file_path[:-3], node.name, sub_node.name]))
                except IndexError as e:
                    self.logger.warning(
                        'Error occurs while handing diff:{}'.format(diff))
                    self.logger.warning(e)
                except SyntaxError as e:
                    self.logger.warning(
                        'Fail to parse {src} with Py3/Py2.7 AST hence pass.'.format(src=src_path))
        return class_set, method_set
