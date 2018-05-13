import logging
import scipy
import os
from goldset.bycommit import GoldsetGenerator, CommitGoldsetGenerator
from common.project import CommitGitProject
from common import CONFIG
from common import util
from models.model import WordSum, DV, Lda


repos_dir = os.path.join(CONFIG.BASE_PATH, 'sources', 'python')
plt_path = os.path.join(CONFIG.BASE_PATH, 'plt')

logger = util.get_logger('rank_stats')


def generate_directly(filter_list):
    git_project_paths = []
    c = 0
    for dirname, dirnames, _ in os.walk(repos_dir):
        if '.git' in dirnames:
            git_project_paths.append(dirname)
            c += 1
    for dirname in git_project_paths:
        name = dirname.split('/')[-1]
        if name in filter_list:
            project = CommitGitProject(name, dirname, 50)
            generator = CommitGoldsetGenerator(project)
            generator.generate_goldsets_directly()


def do_science(prefixa, a_ranks, prefixb, b_ranks):

    x, y = util.measure(a_ranks, b_ranks)

    print(prefixa + ' mrr:', x)
    print(prefixb + ' mrr:', y)
    print('wilcoxon signedrank:', scipy.stats.wilcoxon(x, y))

    


def stats():
    arr = []
    for dirname, _, filenames in os.walk(plt_path):
        if 'ids.txt' in filenames:
            id_path = os.path.join(dirname, 'ids.txt')
            name = dirname.split('/')[-3]
            with open(id_path) as f:
                content = f.read()
                info = '{}:{}'.format(name, content.count('\n'))
                arr.append(info)

    print('all:{0}'.format(len(arr)))
    for i in arr:
        print(i)

def get_python_project_names():
    repos_dir = os.path.join(CONFIG.BASE_PATH, 'sources', 'python')
    for path, dirnames, _ in os.walk(repos_dir):
        if path == repos_dir:
            return dirnames


if __name__ == '__main__':
    names = get_python_project_names()
    for name in names:
        src_path = os.path.join(repos_dir, name)
        project = CommitGitProject(name,src_path)
        lda_m = Lda(project,'file')
        lda_ranks = lda_m.get_ranks()
        doc2vec_m = DV(project,'file')
        doc2vec_rank = doc2vec_m.get_ranks()
        logger.info('finish rank generation for {}.'.format(name))
    
