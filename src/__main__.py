import logging
import scipy
from goldset.bycommit import GoldsetGenerator,CommitGoldsetGenerator
from common.project import LocalGitProject
from common import util
from common.project import LocalGitProject, GitProject
from common import CONFIG
from models.doc2vec import WordSumModel,Doc2VecModel

logger = logging.getLogger('plt.main')

logger.setLevel(CONFIG.LOG_LEVEL)


def generate_data(self):

    generator = CommitGoldsetGenerator(self.project)

    generator.generate()

    logger.info('goldset data was successfully generated.')



def do_science(prefixa, a_ranks, prefixb, b_ranks):
    # Build a dictionary with each of the results for stats.


    x, y = util.measure(a_ranks,b_ranks)

    print(prefixa + ' mrr:', x)
    print(prefixb + ' mrr:', y)
    print('wilcoxon signedrank:', scipy.stats.wilcoxon(x, y))



if __name__ == '__main__':
    project = LocalGitProject('sage', 'by_commit', '../sources/sage', ('5.0', '5.1'), ['trac'])
    doc2vec_m = Doc2VecModel(project,'class')
    doc2vec_rank = doc2vec_m.get_ranks()
    wordsum_m = WordSumModel(project,'class')
    wordsum_rank = wordsum_m.get_ranks()
    do_science('doc2vec', doc2vec_rank, 'sum', wordsum_rank)

    # run(project, 'sum', 'class')
