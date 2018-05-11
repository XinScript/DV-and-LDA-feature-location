import re
import sys
import logging
from itertools import chain
from git import GitCommandError
from os import path, remove
from typed_ast import ast3, ast27
from collections import defaultdict
from common.project import GitProject
from common.error import NotGitProjectError
from common import util,CONFIG



logging.basicConfig(format='%(asctime)s : %(levelname)s : ' + '%(name)s : %(funcName)s : %(message)s')


class GoldsetGenerator():
    def __init__(self, project):
        if not isinstance(project, GitProject):
            raise NotGitProjectError
        else:
            self.project = project
            self.logger = util.get_logger('goldset_generation',project)

            if 'master' in self.project.repo.heads:
                self.project.repo.heads.master.checkout('-f')
            else:
                remote = self.project.repo.remote()
                remote.fetch()
                try:
                    self.project.repo.create_head('master', remote.refs.master)
                    self.project.repo.heads.master.set_tracking_branch(
                        remote.refs.master)
                    self.project.repo.heads.master.checkout()
                except AttributeError:
                    self.logger.info('cannot find master in local or remote repo thus just use current branch.')

                # checkout to master.

    def generate(self):
        self.generate_ids()
        self.generate_queries()
        self.generate_goldsets()

    def _generate_single_goldset(self,commit):
        c_set, m_set = self._extract_goldset_from_commit(commit)
        if c_set:
            with open(path.join(self.project.path_dict['class'], commit.hexsha + '.txt'), 'w') as f:
                [f.write(c + '\n') for c in c_set]

        if m_set:
            with open(path.join(self.project.path_dict['method'], commit.hexsha + '.txt'), 'w') as f:
                [f.write(m + '\n') for m in m_set]
    
        return commit.hexsha if c_set or m_set else None
    
    def _generate_single_query(self,commit):
        with open(path.join(self.project.path_dict['query'], '{idx}.txt'.format(idx=commit.hexsha)), 'w') as f:
            f.write(commit.message)
    
    def _generate_single_id(self,commit):
        map_path = path.join(self.project.path_dict['data'], 'ids.txt')
        with open(map_path, 'a+') as f:
            content = ''.join([commit.hexsha, '\n'])
            f.write(content)


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

    def _extract_goldset_from_commit(self, commit):
        class_set = set()
        method_set = set()
        pattern = re.compile(r'\n@@(.+)@@\n')
        if commit.parents:
            prev_commit = self.project.repo.commit(commit.hexsha + '~1')
            diffs = prev_commit.diff(commit)
            diffs = chain(diffs.iter_change_type('A'), diffs.iter_change_type('M'))
            for diff in diffs:
                file_path = diff.b_path
                try:
                    if util.is_py_file(file_path):
                        src_path = ':'.join([commit.hexsha, file_path])
                        content = self.project.repo.git.show(src_path)
                        try:
                            nodes = ast27.parse(content).body
                            ast = ast27
                        except SyntaxError:
                            # self.logger.warning('Fail to parse {src} with Py2.7 AST.'.format(src=src_path))
                            nodes = ast3.parse(content).body
                            ast = ast3
                            
                        if diff.change_type == 'M':
                            diff_info = self.project.repo.git.diff(diff.a_blob, diff.b_blob)
                            changes = pattern.findall(diff_info)
                            for change in changes:
                                t = change.strip().split('+')[1].split(',')
                                if len(t) == 1:
                                    continue
                                else:
                                    start_line, count = [int(x) for x in t]
                                    end_line = start_line + count - 1
                                    actual_start_line = start_line + 3 if start_line > 1 else start_line
                                    actual_end_line = end_line - 3 if content.count('\n') != end_line else end_line

                                    for node in nodes:
                                        if node.__class__ == ast.FunctionDef:
                                            if not (actual_start_line > node.body[-1].lineno or actual_end_line < node.lineno):
                                                method_set.add('.'.join([file_path[:-3], node.name]))

                                        elif node.__class__ == ast.ClassDef:
                                            flag = False
                                            sub_nodes = node.body
                                            for sub_node in sub_nodes:
                                                if sub_node.__class__ == ast.FunctionDef:
                                                    if not (actual_start_line > sub_node.body[-1].lineno or actual_end_line < sub_node.lineno):
                                                        method_set.add('.'.join([file_path[:-3], node.name, sub_node.name]))
                                                        flag = True
                                                else:
                                                    if actual_start_line <= sub_node.lineno <= actual_end_line:
                                                        flag = True
                                            if flag:
                                                class_set.add('.'.join([file_path[:-3], node.name]))

                        elif diff.change_type == 'A':
                            for node in nodes:
                                if node.__class__ == ast.FunctionDef:
                                    method_set.add('.'.join([file_path[:-3], node.name]))
                                elif node.__class__ == ast.ClassDef:
                                    class_set.add('.'.join([file_path[:-3], node.name]))
                                    sub_nodes = node.body
                                    for sub_node in sub_nodes:
                                        if sub_node.__class__ == ast.FunctionDef:
                                            method_set.add('.'.join([file_path[:-3], node.name, sub_node.name]))

                except IndexError as e:
                    self.logger.warning('Error occurs while handing diff:{}'.format(diff))
                    self.logger.warning(e)

                except SyntaxError as e:
                    self.logger.warning('Fail to parse {src} with Py3/Py2.7 AST hence pass.'.format(src=src_path))

                except Exception as e:
                    self.logger.warning(e)


        return class_set, method_set
