from GoldsetGenerator import GoldsetGenerator,CommitGoldsetGenerator
from Project import LocalGitProject,Project
from Corpora import GitCorpus,GeneralCorpus
import gensim
import pickle
import os
import Config

if __name__ == '__main__':
    src_path =  '../sources/sage'
    project = LocalGitProject('sage',src_path, [('5.0', '5.1')], ['trac'])
    parser = CommitGoldsetGenerator(project)
    parser.generate()
    project.save()

def run_doc2vec(name):
    project = Project.load(name)
    doc_corpus = GitCorpus(project,'5.1')
    
def create_query_corpus(project):
    for version in project.versions:
        paths = project.path_dict[version]
        base_path = paths['base']
        id2word_fname = os.path.join(base_path,Config.ID2WORD_EXT)
        corpus_fname = os.path.join(base_path,Config.CORPUS_EXT)
        pp = GeneralCorpus()
        id2word = gensim.corpora.Dictionary()
        paths['query']

    
    
    

    
