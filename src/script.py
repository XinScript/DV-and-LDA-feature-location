import os
from common import CONFIG
from common.project import CommitGitProject
from corpus.corpora import GitCorpus
from goldset.bycommit import CommitGoldsetGenerator
from common import util
import csv
import seaborn as sb
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict

repos_dir = os.path.join(CONFIG.BASE_PATH, 'sources', 'python')
topic_num, goldset_level = '50', 'file'


git_project_paths = []
for dirname, dirnames, _ in os.walk(repos_dir):
    if '.git' in dirnames:
        git_project_paths.append(dirname)


def generate_directly(filter_list=[]):
    for dirname in git_project_paths:
        name = dirname.split('/')[-1]

        if filter_list:
            if name in filter_list:
                project = CommitGitProject(dirname, 50)
                generator = CommitGoldsetGenerator(project)
                generator.generate_goldsets_directly()
        else:
            project = CommitGitProject(dirname, 50)
            generator = CommitGoldsetGenerator(project)
            generator.generate_goldsets_directly()


def write_length():
    for dirname in git_project_paths:
        name = dirname.split('/')[-1]
        project = CommitGitProject(dirname, 50)
        corpus = GitCorpus(project)
        [_ for _ in corpus.gen()]
        with open('project_size.txt', 'a+') as f:
            f.write(':'.join([project.name, str(corpus.length) + '\n']))


def read_size():
    length_path = os.path.join(CONFIG.BASE_PATH, 'project_size.txt')
    with open(length_path, 'r') as f:
        return [x.strip().split(':')[1] for x in f]


def read_ranks(name, model_name, topic_num, goldset_level):
    ranks = defaultdict(list)
    full_path = os.path.join(CONFIG.BASE_PATH, 'plt', name, 'goldset_num_' + topic_num, '.'.join([model_name, goldset_level, CONFIG.RANK_EXT]))
    with open(full_path, 'r') as f:
        reader = csv.reader(f)
        next(reader)
        for qid, idx, dist, d_path in reader:
            ranks[qid].append((int(idx), float(dist), d_path))
    return ranks


# ranks = read_ranks('sage','DV','50','file')
def write_mrr_info():
    w_path = os.path.join(CONFIG.BASE_PATH, '.'.join([goldset_level, topic_num, CONFIG.MRR_EXT]))
    with open(w_path, 'w') as w:
        writer = csv.writer(w)
        writer.writerow(['project', 'DV_MRR', 'LDA_MRR'])
        for path in git_project_paths:
            name = path.split('/')[-1]
            lda_ranks = read_ranks(name, 'Lda', topic_num, goldset_level)
            dv_ranks = read_ranks(name, 'DV', topic_num, goldset_level)
            # lda_mrr = util.evaluate_mrr_with_frms(lda_ranks)
            # dv_mrr = util.evaluate_mrr_with_frms(dv_ranks)
            lda_mrr, dv_mrr = util.calculate_mrr(lda_ranks, dv_ranks)
            # dv_mrr = util.calculate_mrr(dv_ranks)
            writer.writerow([name, dv_mrr, lda_mrr])


def read_mrr():
    mrr_path = os.path.join(CONFIG.BASE_PATH, '.'.join([goldset_level, topic_num, CONFIG.MRR_EXT]))
    df = pd.read_csv(mrr_path)
    return df


def merge_size_with_rank():
    size = read_size()
    df = read_mrr()
    df['size'] = size
    return df

def plt_scatter():
    fname = os.path.join(CONFIG.BASE_PATH ,'scatter.png')
    df = merge_size_with_rank()
    # g = sb.pairplot(data=df,y_vars=['DV_MRR'],x_vars=['size'])
    plt.scatter(x=df['size'],y=df['DV_MRR'])
    # fname = os.path.join(CONFIG.BASE_PATH, 'lda_scatter.png')
    plt.scatter(x=df['size'], y=df['LDA_MRR'])
    plt.xlabel('size')
    plt.ylabel('MRR')
    plt.savefig(fname)
    plt.clf()
    plt.close()


