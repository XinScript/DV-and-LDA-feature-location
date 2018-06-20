'''

This module is the abstract class of goldset generator.
Some common and meta methods are implemented.
For Python, it supports class,method and file level goldset generation.
For Java, it only supports File/class level.

'''
import re
import logging
import javalang
import logging
from shutil import rmtree
from javalang.parser import JavaParserError,JavaSyntaxError

from itertools import chain
from os import path
from collections import defaultdict
from typed_ast import ast3, ast27

from ..common.project import CommitGitProject,IssueGitProject
from ..common import util,config

logging.basicConfig(format='%(asctime)s : %(levelname)s : ' + '%(name)s : %(funcName)s : %(message)s')
share_logger = logging.getLogger('goldset.public')


class GoldsetGenerator():
    def __init__(self, project):
        if self.__class__ == GoldsetGenerator:
            raise NotImplementedError
        else:
            self.project = project
            self.logger = logging.getLogger('goldset.private')


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

    def _generate_single_goldset(self,commit):
        goldset_set = None
        if self.project.lan == 'PYTHON':
            if self.project.level == 'file':
                goldset_set = self._extract_goldset_from_commit_python_file_level(commit)
            elif self.project.level == 'class':
                goldset_set = self._extract_goldset_from_commit_python_class_level(commit)
            elif self.project.level == 'method':
                goldset_set = self._extract_goldset_from_commit_python_method_level(commit)
        elif self.project.lan == 'JAVA':
            if self.project.level == 'file':
                goldset_set = self._extract_goldset_from_commit_java_file_level(commit)
        
        if goldset_set:
            with open(path.join(self.project.path_dict[self.project.level], commit.hexsha + '.txt'), 'w') as f:
                [f.write(c + '\n') for c in goldset_set]
    
        return commit.hexsha if goldset_set else None
    def _generate_single_query(self,commit):
        with open(path.join(self.project.path_dict['query'], '{idx}.txt'.format(idx=commit.hexsha)), 'w') as f:
            f.write(commit.message)
    def _generate_single_id(self,commit):
        map_path = path.join(self.project.path_dict['data'], self.project.level+'_ids.txt')
        with open(map_path, 'a+') as f:
            content = ''.join([commit.hexsha, '\n'])
            f.write(content)

    def _extract_goldset_from_commit_python_method_level(self, commit):
        method_set = set()
        pattern = re.compile(r'\n@@(.+)@@\n')
        if commit.parents:
            prev_commit = self.project.repo.commit(commit.hexsha + '~1')
            diffs = prev_commit.diff(commit)
            diffs = chain(diffs.iter_change_type('A'), diffs.iter_change_type('M'))
            for diff in diffs:
                file_path = diff.b_path
                try:
                    if file_path.endswith('.py'):
                        src_path = ':'.join([commit.hexsha, file_path])
                        content = self.project.repo.git.show(src_path)
                        try:
                            nodes = ast27.parse(content).body
                            ast = ast27
                        except SyntaxError:
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
                                            sub_nodes = node.body
                                            for sub_node in sub_nodes:
                                                if sub_node.__class__ == ast.FunctionDef:
                                                    if not (actual_start_line > sub_node.body[-1].lineno or actual_end_line < sub_node.lineno):
                                                        method_set.add('.'.join([file_path[:-3], node.name, sub_node.name]))

                        elif diff.change_type == 'A':
                            for node in nodes:
                                if node.__class__ == ast.FunctionDef:
                                    method_set.add('.'.join([file_path[:-3], node.name]))
                                elif node.__class__ == ast.ClassDef:
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


        return method_set

    def _extract_goldset_from_commit_python_file_level(self, commit):
        file_set = set()
        
        if commit.parents:
            prev_commit = self.project.repo.commit(commit.hexsha + '~1')
            diffs = prev_commit.diff(commit)
            diffs = chain(diffs.iter_change_type('A'), diffs.iter_change_type('M'))
            for diff in diffs:
                file_path = diff.b_path
                try:
                    if file_path.endswith('.py'):
                        file_set.add(file_path[:-3])
                        
                except IndexError as e:
                    self.logger.warning('Error occurs while handing diff:{}'.format(diff))
                    self.logger.warning(e)

                except SyntaxError as e:
                    self.logger.warning('Fail to parse {src} with Py3/Py2.7 AST hence pass.'.format(src=src_path))

                except Exception as e:
                    self.logger.warning(e)

        return file_set

    def _extract_goldset_from_commit_python_class_level(self, commit):
        class_set = set()
        pattern = re.compile(r'\n@@(.+)@@\n')
        if commit.parents:
            prev_commit = self.project.repo.commit(commit.hexsha + '~1')
            diffs = prev_commit.diff(commit)
            diffs = chain(diffs.iter_change_type('A'), diffs.iter_change_type('M'))
            for diff in diffs:
                file_path = diff.b_path
                try:
                    if file_path.endswith('.py'):
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
                                        if node.__class__ == ast.ClassDef:
                                            class_set.add('.'.join([file_path[:-3], node.name]))

                        elif diff.change_type == 'A':
                            for node in nodes:
                                if node.__class__ == ast.ClassDef:
                                    class_set.add('.'.join([file_path[:-3], node.name]))

                except IndexError as e:
                    self.logger.warning('Error occurs while handing diff:{}'.format(diff))
                    self.logger.warning(e)

                except SyntaxError as e:
                    self.logger.warning('Fail to parse {src} with Py3/Py2.7 AST hence pass.'.format(src=src_path))

                except Exception as e:
                    self.logger.warning(e)

        return class_set

    def _extract_goldset_from_commit_java_file_level(self, commit):
        goldset_set = set()
        pattern = re.compile(r'\n@@(.+)@@\n')
        if commit.parents:
            prev_commit = self.project.repo.commit(commit.hexsha + '~1')
            diffs = prev_commit.diff(commit)
            diffs = chain(diffs.iter_change_type('A'), diffs.iter_change_type('M'))
            for diff in diffs:
                file_path = diff.b_path
                try:
                    if file_path.endswith('.java'):
                        src_path = ':'.join([commit.hexsha, file_path])
                        content = self.project.repo.git.show(src_path)
                        try:
                            tree = javalang.parse.parse(content)
                        except Exception as e:
                            continue
                        nodes = [node for _,node in tree.filter(javalang.tree.ClassDeclaration)]
                        if nodes:
                            goldset_set.add(file_path[:-5])
                        

                except IndexError as e:
                    self.logger.warning('Error occurs while handing diff:{}'.format(diff))
                    self.logger.warning(e)

                except Exception as e:
                    raise e

        return goldset_set


class CommitGoldsetGenerator(GoldsetGenerator):

    def __init__(self, project):
        if project.__class__  == CommitGitProject:
            super().__init__(project)
        else:
            raise TypeError('You shoud pass a "CommitGitProject" to this class of generation.')

    def generate(self):
        rmtree(self.project.path_dict['data'])
        self.project.load_dirs()
        share_logger.info('{}'.format(self.project.name))
        start_commit = self.project.ref
        self.logger.info('use last commit {id} as start ref.'.format(id=start_commit.hexsha))

        share_logger.info('ref:{}'.format(start_commit.hexsha))
        commit = start_commit
        goldset_count = 0
        commit_count = 0
        while commit.parents:
            idx = self._generate_single_goldset(commit)
            commit_count += 1
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


class IssueGoldsetGenerator(GoldsetGenerator):
    def __init__(self, project):
        if project.__class__ == IssueGitProject:
            super().__init__(project)
        else:
            raise TypeError('You shoud pass a "IssueGitProject" to this class of generation.')

    def generate(self):
        rmtree(self.project.path_dict['data'])
        self.project.load_dirs()
        pattern = re.compile('{types} #(\d+)'.format(types='|'.join(self.project.issue_keywords)))
        d = defaultdict(list)

        commits = self.project.repo.iter_commits('{0}...{1}'.format(*self.project.by_release))

        for commit in commits:
            m = pattern.search(commit.message.lower())
            if m:
                idx = self._generate_single_goldset(commit)
                if idx:
                    self._generate_single_id(commit)
                    self._generate_single_query(commit)
