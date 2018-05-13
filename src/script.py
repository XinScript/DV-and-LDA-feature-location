import os
from common import CONFIG
from common.project import CommitGitProject
from corpus.corpora import GitCorpus

# repos_dir = os.path.join(CONFIG.BASE_PATH, 'sources', 'python')


# def get_length(filter_list):
#     git_project_paths = []
#     c = 0
#     for dirname, dirnames, _ in os.walk(repos_dir):
#         if '.git' in dirnames:
#             git_project_paths.append(dirname)
#             c += 1
#     for dirname in git_project_paths:
#         name = dirname.split('/')[-1]
#         project = CommitGitProject(name, dirname, 50)
#         corpus = GitCorpus(project)
#         [_ for _ in corpus.gen()]
#         with open('length.txt','a+') as f:
#             f.write(':'.join([project.name,str(corpus.length)+'\n']))
