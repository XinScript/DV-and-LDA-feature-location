'''

This file is not the part of systems but the scripts for experiments implementation of the research,
including goldset generation, model training, rank generation, charts plotting, etc.

'''
import os
import csv
import seaborn as sb
import pandas as pd
import matplotlib.pyplot as plt
import shutil
from common import CONFIG
from common.project import CommitGitProject
from corpus.corpora import GitCorpus
from goldset.generatorByCommit import CommitGoldsetGenerator
from common import util
from collections import defaultdict
from models.model import WordSum, DV, Lda

lan = 'python'
repos_dir = os.path.join(CONFIG.BASE_PATH, 'sources', lan)
topic_num, goldset_level, iterations = '500', 'file', '30'
base_path = CONFIG.BASE_PATH
logger = util.get_logger('rank_stats')

if lan == 'python':
    compare_projects = ['gtg', 'web2py', 'heat', 'sympy', 'sage']
    file_ext = '.py'
elif lan == 'java':
    compare_projects = ['facebook-android-sdk', 'astrid', 'netty', 'hadoop-common', 'hibernate-orm']
    file_ext = '.java'
# plt_path = os.path.join(CONFIG.BASE_PATH, 'plt')+file_ext
plt_path = os.path.join(CONFIG.BASE_PATH, 'plt') + file_ext


git_project_paths = []
for dirname, dirnames, _ in os.walk(repos_dir):
    if '.git' in dirnames:
        git_project_paths.append(dirname)


def generate_directly(filter_list=[]):
    for dirname in git_project_paths:
        name = dirname.split('/')[-1]
        if filter_list:
            if name in filter_list:
                project = CommitGitProject(dirname, file_ext)
                generator = CommitGoldsetGenerator(project)
                generator.generate_goldsets_directly()
        else:
            project = CommitGitProject(dirname, file_ext)
            generator = CommitGoldsetGenerator(project)
            generator.generate_goldsets_directly()


def generate_models(topic_nums, iterations, filter_list=[], start_index=None):
    # flag = False
    for dirname in git_project_paths if not start_index else git_project_paths[start_index:]:
        if not filter_list or dirname.split('/')[-1] in filter_list:
            for n in topic_nums:
                for i in iterations:
                    project = CommitGitProject(dirname, file_ext)
                    lda_m = Lda(project, goldset_level, num_topics=n,iterations=i)
                    lda_ranks = lda_m.get_ranks()
                    doc2vec_m = DV(project, goldset_level, num_topics=n, iterations=i)
                    doc2vec_rank = doc2vec_m.get_ranks()
                    logger.info('finish rank generation for {}.'.format(project.name))

    # exit()


def write_size():
    with open(os.path.join(base_path, lan + '_project_size.txt'), 'w') as f:
        for dirname in git_project_paths:
            name = dirname.split('/')[-1]
            project = CommitGitProject(dirname, file_ext, 50)
            corpus = GitCorpus(project)
            [_ for _ in corpus.gen()]
            f.write(':'.join([project.name, str(corpus.length) + '\n']))


def read_size():
    length_path = os.path.join(base_path, lan + '_project_size.txt')
    with open(length_path, 'r') as f:
        return [x.strip().split(':')[1] for x in f]
def write_head_commit():
    with open(plt_path+'/goldset_generation_start_pointer.txt','w') as f:
        for p in git_project_paths:
            project = CommitGitProject(p,file_ext)
            f.write(project.name+':'+project.repo.head.commit.hexsha+'\n')


# ranks = read_ranks('sage','DV','50','file')
def write_mrr_info(num_topics, iterations):
    w_path = os.path.join(base_path, '.'.join([lan, goldset_level, topic_num, iterations, CONFIG.MRR_EXT]))
    with open(w_path, 'w') as w:
        writer = csv.writer(w)
        writer.writerow(['project', 'DV_MRR', 'LDA_MRR'])
        for path in git_project_paths:
            name = path.split('/')[-1]
            project = CommitGitProject(path, file_ext)
            lda_ranks = Lda(project, 'file').read_ranks()
            dv_ranks = DV(project, 'file').read_ranks()
            lda_mrr, dv_mrr = util.calculate_mrr(lda_ranks, dv_ranks)
            writer.writerow([name, dv_mrr, lda_mrr])


def plot_line_charts_for_projects():
    for name in compare_projects:
        lda_mrrs, dv_mrrs = [], []
        for topic_num in [100, 200, 300, 400, 500]:
            lda_ranks = read_ranks(name, 'Lda', str(topic_num))
            dv_ranks = read_ranks(name, 'DV', str(topic_num))
            lda_mrr, dv_mrr = util.calculate_mrr(lda_ranks, dv_ranks)
            lda_mrrs.append(lda_mrr)
            dv_mrrs.append(dv_mrr)
        plt_line_chart(name, lda_mrrs, dv_mrrs)


def read_mrr():
    mrr_path = os.path.join(base_path, '.'.join([lan, goldset_level, topic_num, iterations, CONFIG.MRR_EXT]))
    df = pd.read_csv(mrr_path)
    return df


def plt_scatter():
    fname = os.path.join(base_path, 'plots', 'model_compare', lan + 'num_topics_%s_iter_%s_scatter.png' % (topic_num, iterations))
    size = read_size()
    df = read_mrr()
    df['size'] = size
    # g = sb.pairplot(data=df,y_vars=['DV_MRR'],x_vars=['size'])
    # fname = os.path.join(CONFIG.BASE_PATH, 'lda_scatter.png')
    plt.scatter(x=df['size'], y=df['LDA_MRR'], label='LDA')
    plt.scatter(x=df['size'], y=df['DV_MRR'], label='DV')
    plt.legend()
    plt.xlabel('Project Size')
    plt.ylabel('MRR')
    plt.savefig(fname)
    plt.clf()
    plt.close()


def plt_line_chart():
    for p in git_project_paths:
        name = p.split('/')[-1]
        if name in compare_projects:
            fname = os.path.join(base_path, 'plots', 'parameter_compare', '_'.join([lan, name, 'line_chart.png']))
            outter = []
            project = CommitGitProject(p,file_ext)
            for i in [100, 200, 300, 400, 500]:
                inner = []
                for j in [10, 30, 50, 80, 100]:
                    dv_ranks = DV(project,'file',i,j).read_ranks()
                    inner.append(util.evaluate_mrr_with_frms(dv_ranks))

                plt.plot([10, 30, 50, 80, 100], inner, label='DV_%d'%i)

            lda_mrrs = []
            project = CommitGitProject(p, file_ext)
            for j in [10, 30, 50, 80, 100]:
                lda_mrrs.append(util.evaluate_mrr_with_frms(Lda(project,'file',500,iterations=j).read_ranks()))
            plt.plot([10, 30, 50, 80, 100], lda_mrrs, label='LDA_500')
            # plt.show()
            plt.xlabel('Iterations')
            plt.ylabel('MRR')
            plt.title(project.name)
            plt.legend()
            plt.savefig(fname)
            plt.clf()
    # plt.close()


def plt_violin():
    

    corley_arr = [0.415566,0.229730,0.791096,0.151986,0.337100,0.203929]
    java_arr = []
    python_arr = []

    with open ('../java_project_size.txt') as java_f:
        java_size_arr = [int(x.split(':')[1]) for x in java_f.read().strip().split()]
    with open('../python_project_size.txt') as python_f:
        python_size_arr = [int(x.split(':')[1]) for x in python_f.read().strip().split()]

    repos_dir = os.path.join(CONFIG.BASE_PATH, 'sources', 'java')
    git_project_paths = []
    for dirname, dirnames, _ in os.walk(repos_dir):
        if '.git' in dirnames:
            git_project_paths.append(dirname)
    for i, p in enumerate(git_project_paths):
        project = CommitGitProject(p, '.java')
        d = project.load_goldsets('file')
        s = set()
        for v in d.values():
            s.update(v)
        x = len(s) / java_size_arr[i]
        if x>=1:
            print(project.name)
            print(java_size_arr[i])
        java_arr.append(x)
    java_arr = [x if x<=1 else 1 for x in java_arr]

    repos_dir = os.path.join(CONFIG.BASE_PATH, 'sources', 'python')
    git_project_paths = []
    for dirname, dirnames, _ in os.walk(repos_dir):
        if '.git' in dirnames:
            git_project_paths.append(dirname)
    # print(len(git_project_paths))
    for i, p in enumerate(git_project_paths):
        project = CommitGitProject(p, '.py')
        d = project.load_goldsets('file')
        s = set()
        for v in d.values():
            s.update(v)
        x = len(s) / python_size_arr[i]
        if x >=1 :
            print(project.name)
            print(python_size_arr[i])
        python_arr.append(x)
    python_arr = [x if x<=1 else 1 for x in python_arr]

    fig, axes = plt.subplots(nrows=1, ncols=3, figsize=(6, 6))
    # positions = [0.0,0.2,0.4,0.6,0.8,1.0]
    # axes[0].violinplot(java_arr,showmeans=True, showextrema=True, showmedians=True)
    axes[0].set_title('Java_50')
    # axes[0].set_ylim(0,1)
    # axes[1].violinplot(python_arr, showmeans=True, showextrema=True, showmedians=True)
    axes[1].set_title('Python_50')
    
    axes[2].set_title('Corley_6')
    # axes[2].set_ylim(0,1)

    # axes[0].set_ylim(0,1)
    # axes[1].set_ylim(0,1)
    # axes[2].set_ylim(0, 1)
    # sb.violinplot(data=[java_arr],ax=axes[0])
    # sb.violinplot(data=[python_arr],ax=axes[1])
    # sb.violinplot(data=[corley_arr],ax=axes[2])
    # # axes[2].violinplot(corley_arr, showmeans=True, showextrema=True, showmedians=True)
    # fig.suptitle("Violin Plots")
    # # plt.violinplot(java_arr)
    # # plt.violinplot(python_arr)
    # # plt.violinplot(corley_arr)
    # # plt.show()
    # fig.savefig(CONFIG.BASE_PATH+'/seaborn_violin.png')

    


def remove_data():
    for dirname,dirnames,filenames in os.walk(plt_path):
        for i in filenames:
            if i.endswith('txt') or i.endswith('gz'):
                os.remove(dirname + '/' + i)
        # a = os.path.join(base_path, 'DV')
        # if os.path.exists(a):
        #     shutil.rmtree(a)
        # a = os.path.join(base_path, 'Lda')
        # if os.path.exists(a):
        #     shutil.rmtree(a)


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
        if project.name not in ['facebook-android-sdk', 'astrid', 'netty', 'hadoop-common', 'hibernate-orm']:
            # if project.name in ['gtg', 'web2py', 'heat', 'sympy', 'sage']:
            for n in [400, 300, 200, 100]:
                path = os.path.join(project.path_dict['base'], 'Lda', str(n))
                if os.path.exists(path):
                    shutil.rmtree(path)
                path = os.path.join(project.path_dict['base'], 'DV', str(n))
                if os.path.exists(path):
                    shutil.rmtree(path)


def mrr_compare(topic_nums, iterations, filter_list=[]):
    ans = []
    for dirname in git_project_paths:
        if not filter_list or dirname.split('/')[-1] in filter_list:
            s = []
            for n in topic_nums:
                for i in iterations:
                    project = CommitGitProject(dirname, file_ext)
                    # lda_m = Lda(project, goldset_level, num_topics=n,iterations=i)
                    # lda_ranks = lda_m.get_ranks()
                    doc2vec_m = DV(project, goldset_level, num_topics=n, iterations=i)
                    doc2vec_rank = doc2vec_m.get_ranks()
                    s.append(util.evaluate_mrr_with_frms(doc2vec_rank))
            ans.append(max(s))
    print(ans)

def plot_displot():
    sb.distplot([int(x) for x in read_size()],kde=False)
    # sb.distplot([1, 2], kde=False)
    
    plt.xlabel('project size (number of files)')
    plt.ylabel('number of projects')
    # plt.show()
    plt.savefig(base_path+'/{}_project_size_distribution.png'.format(lan))
    # plt.clf()

def write_project_description():
    sizes = read_size()
    with open(plt_path+'/goldset_generation_start_pointer.txt') as f:
        commit_refs = [x.split(':') for x in f.read().strip().split()]
    with open(base_path+'/%s_ref_commit_size.csv'%lan,'w') as w:
        for i,p in enumerate(commit_refs):
            w.write(','.join([p[0],sizes[i],p[1]])+'\n')



# plot_displot()
# plt_violin()


# parameter_compare()

# generate_directly(['grails-core'])

# print(len(read_size()))
# plt_scatter()
# plot_line_charts_for_projects()

# print(len([x for x in read_size() if int(x)>100]))
# generate_models([500], [30])
# generate_models([500], [10,30,50,80,100], compare_projects)
# write_mrr_info('500','30')
# plt_scatter()
# plot_line_charts_for_projects()
# plt_line_chart()
# write_size()
# plot_displot()
# write_project_description()
remove_data()