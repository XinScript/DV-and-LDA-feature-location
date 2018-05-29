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
from models.model import WordSum, DV, Lda
import shutil

lan = 'python'

repos_dir = os.path.join(CONFIG.BASE_PATH, 'sources', lan)
topic_num, goldset_level = '50', 'file'
base_path = CONFIG.BASE_PATH
logger = util.get_logger('rank_stats')

if lan == 'python':
    compare_projects = ['gtg', 'web2py', 'heat', 'sympy', 'sage']
    file_ext = '.py'
elif lan == 'java':
    compare_projects = ['facebook-android-sdk', 'astrid', 'netty', 'hadoop-common', 'hibernate-orm']
    file_ext = '.java'
# plt_path = os.path.join(CONFIG.BASE_PATH, 'plt')+file_ext
plt_path = os.path.join(CONFIG.BASE_PATH, 'plt')+file_ext



git_project_paths = []
for dirname, dirnames, _ in os.walk(repos_dir):
    if '.git' in dirnames:
        git_project_paths.append(dirname)


def generate_directly(filter_list=[]):
    for dirname in git_project_paths:
        name = dirname.split('/')[-1]
        if filter_list:
            if name in filter_list:
                project = CommitGitProject(dirname, file_ext, 50)
                generator = CommitGoldsetGenerator(project)
                generator.generate_goldsets_directly()
        else:
            project = CommitGitProject(dirname, file_ext, 50)
            generator = CommitGoldsetGenerator(project)
            generator.generate_goldsets_directly()


def generate_models(n, filter_list=[]):
    flag = False
    for dirname in git_project_paths:
        if filter_list:
            if dirname.split('/')[-1] in filter_list:
                for num_topics in n:
                    project = CommitGitProject(dirname, file_ext)
                    lda_m = Lda(project, 'file', num_topics=num_topics)
                    lda_ranks = lda_m.get_ranks()
                    doc2vec_m = DV(project, 'file', num_topics=num_topics)
                    doc2vec_rank = doc2vec_m.get_ranks()
                    logger.info('finish rank generation for {}.'.format(project.name))

        else:
            for num_topics in n:
                project = CommitGitProject(dirname, file_ext)
                lda_m = Lda(project, 'file',num_topics=num_topics)
                lda_ranks = lda_m.get_ranks()
                doc2vec_m = DV(project, 'file', num_topics=num_topics)
                doc2vec_rank = doc2vec_m.get_ranks()
                logger.info('finish rank generation for {}.'.format(project.name))
            # exit()


def write_size():
    for dirname in git_project_paths:
        name = dirname.split('/')[-1]
        project = CommitGitProject(dirname, file_ext, 50)
        corpus = GitCorpus(project)
        [_ for _ in corpus.gen()]
        with open(os.path.join(base_path, lan+'_project_size.txt'), 'a+') as f:
            f.write(':'.join([project.name, str(corpus.length) + '\n']))


def read_size():
    length_path = os.path.join(base_path, lan+'_project_size.txt')
    with open(length_path, 'r') as f:
        return [x.strip().split(':')[1] for x in f]


def read_ranks(name, model_name,topic_num):
    ranks = defaultdict(list)
    full_path = os.path.join(plt_path, name, 'goldset_num_50',model_name,topic_num, '.'.join([model_name, goldset_level, CONFIG.RANK_EXT]))
    with open(full_path, 'r') as f:
        reader = csv.reader(f)
        next(reader)
        for qid, idx, dist, d_path in reader:
            ranks[qid].append((int(idx), float(dist), d_path))
    return ranks


# ranks = read_ranks('sage','DV','50','file')
def write_mrr_info(num_topics):
    w_path = os.path.join(base_path, '.'.join([lan,goldset_level, topic_num, CONFIG.MRR_EXT]))
    with open(w_path, 'w') as w:
        writer = csv.writer(w)
        writer.writerow(['project', 'DV_MRR', 'LDA_MRR'])
        for path in git_project_paths:
            name = path.split('/')[-1]
            lda_ranks = read_ranks(name, 'Lda',num_topics)
            dv_ranks = read_ranks(name, 'DV',num_topics)
            # lda_mrr = util.evaluate_mrr_with_frms(lda_ranks)
            # dv_mrr = util.evaluate_mrr_with_frms(dv_ranks)
            lda_mrr, dv_mrr = util.calculate_mrr(lda_ranks, dv_ranks)
            # dv_mrr = util.calculate_mrr(dv_ranks)
            writer.writerow([name, dv_mrr, lda_mrr])

def plot_line_charts_for_projects():
    for name in compare_projects:
        lda_mrrs,dv_mrrs = [],[]
        for topic_num in [100,200,300,400,500]:
            lda_ranks = read_ranks(name,'Lda',str(topic_num))
            dv_ranks = read_ranks(name,'DV',str(topic_num))
            lda_mrr, dv_mrr = util.calculate_mrr(lda_ranks, dv_ranks)
            lda_mrrs.append(lda_mrr)
            dv_mrrs.append(dv_mrr)
        plt_line_chart(name,lda_mrrs,dv_mrrs)
    

def read_mrr():
    mrr_path = os.path.join(base_path, '.'.join([lan,goldset_level, topic_num, CONFIG.MRR_EXT]))
    df = pd.read_csv(mrr_path)
    return df


def merge_size_with_rank():
    size = read_size()
    df = read_mrr()
    df['size'] = size
    return df


def plt_scatter():
    fname = os.path.join(base_path, 'plots', 'model_compare', lan+'_scatter.png')
    df = merge_size_with_rank()
    # g = sb.pairplot(data=df,y_vars=['DV_MRR'],x_vars=['size'])
    # fname = os.path.join(CONFIG.BASE_PATH, 'lda_scatter.png')
    plt.scatter(x=df['size'], y=df['LDA_MRR'],label='LDA')
    plt.scatter(x=df['size'], y=df['DV_MRR'],label='DV')
    plt.legend()
    plt.xlabel('Project Size')
    plt.ylabel('MRR')
    plt.savefig(fname)
    plt.clf()
    plt.close()

def plt_line_chart(name,lda_mrrs,dv_mrrs):
    fname = os.path.join(base_path, 'plots', 'parameter_compare', '_'.join([lan,name,'line_chart.png']))
    plt.xlabel('Topic numbers')
    plt.ylabel('MRR')
    plt.plot([100,200,300,400,500],lda_mrrs,label='LDA')
    plt.plot([100,200,300,400,500],dv_mrrs,label='DV')
    # plt.show()
    plt.legend()
    plt.savefig(fname)
    plt.clf()
    # plt.close()


def move():
    for p in git_project_paths[0:1]:
        project = CommitGitProject(p, '.py')
        start_path = project.path_dict['base']
        lda_file_names = ['Lda.code.model.gz', 'Lda.code.model.gz.expElogbeta.npz', 'Lda.code.model.id2word.gz', 'Lda.code.model.state.gz', 'Lda.file.rank.csv']
        dv_file_names = ['DV.code.model.gz', 'DV.file.rank.csv']
        lda_target_path = os.path.join(project.path_dict['base'], 'Lda', '500')
        dv_target_path = os.path.join(project.path_dict['base'], 'DV', '500')
        if not os.path.exists(dv_target_path):
            os.makedirs(dv_target_path)
        if not os.path.exists(lda_target_path):
            os.makedirs(lda_target_path)
        for name in lda_file_names:
            if os.path.exists(start_path + '/' + name):
                shutil.move(start_path + '/' + name, lda_target_path + '/' + name)
        for name in dv_file_names:
            if os.path.exists(start_path + '/' + name):
                shutil.move(start_path + '/' + name, dv_target_path + '/' + name)
def remove():
    for p in git_project_paths:
        project = CommitGitProject(p, file_ext)
        # if project.name not in ['facebook-android-sdk', 'astrid', 'netty', 'hadoop-common', 'hibernate-orm']:
        if project.name in ['gtg', 'web2py', 'heat', 'sympy', 'sage']:
            for n in [400,300,200,100]:
                path = os.path.join(project.path_dict['base'], 'Lda', str(n))
                if os.path.exists(path):
                    shutil.rmtree(path)
                path = os.path.join(project.path_dict['base'], 'DV', str(n))
                if os.path.exists(path):
                    shutil.rmtree(path)


# parameter_compare()

# generate_directly(['grails-core'])


# generate_models([400,300,200,100],['gtg', 'web2py', 'heat', 'sympy', 'sage'])

# remove()
# move()
# write_size()
# write_mrr_info('500')
# plt_scatter()
# plot_line_charts_for_projects()
# lan='python'
plt_scatter()
plot_line_charts_for_projects()
