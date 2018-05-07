import logging
import scipy
import os
from goldset.bycommit import GoldsetGenerator, CommitGoldsetGenerator
from common.project import CommitGitProject
from common import CONFIG
from common import util
from models.doc2vec import WordSumModel, Doc2VecModel

logger = logging.getLogger('plt.main')

src_path = os.path.join(CONFIG.BASE_PATH, 'sources', 'python')


logger.setLevel(CONFIG.LOG_LEVEL)


def generate_directly():
    git_project_paths = []
    c = 0
    for dirname, dirnames, _ in os.walk(src_path):
        if '.git' in dirnames:
            git_project_paths.append(dirname)
            c += 1
    for dirname in git_project_paths:
        name = dirname.split('/')[-1]
        logger.info('start goldset generation for {name}.\n'.format(name=name))
        project = CommitGitProject(name, dirname, 50)
        generator = CommitGoldsetGenerator(project)
        generator.generate_goldsets_directly()
    logger.info('goldset data was successfully generated.')


def do_science(prefixa, a_ranks, prefixb, b_ranks):

    x, y = util.measure(a_ranks, b_ranks)

    print(prefixa + ' mrr:', x)
    print(prefixb + ' mrr:', y)
    print('wilcoxon signedrank:', scipy.stats.wilcoxon(x, y))


def stats():
    plt_path = os.path.join(CONFIG.BASE_PATH, 'plt')
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


if __name__ == '__main__':
    generate_directly()
    # stats()

    # doc2vec_m = Doc2VecModel(project,'class')
    # doc2vec_rank = doc2vec_m.get_ranks()
    # wordsum_m = WordSumModel(project,'class')
    # wordsum_rank = wordsum_m.get_ranks()
    # do_science('doc2vec', doc2vec_rank, 'sum', wordsum_rank)
