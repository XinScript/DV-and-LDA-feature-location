'''

This demo gives an example how to use this framework to conduct your own expeirments.
Before starting, you need to make use
1) the code of subject system is downloaded into your disk and locates in the SOURCE_PATH defined in the config.py.
2) check the config.py and make it suits your case.


'''
from src.common.project import CommitGitProject,IssueGitProject
from src.goldset.generator import CommitGoldsetGenerator,IssueGoldsetGenerator
from src.models.model import Lda,DV
import src.common.config as config
import src.common.util as util

'''
for instance, I have a java project called "storm" and I want to apply the methodology on file level goldsets.
The workflow is as simple as follow, it might take a while though.
'''

project = CommitGitProject(name='sympy',lan='python',level='file')
# # new a project
gen = CommitGoldsetGenerator(project)
# # new a generator
gen.generate()
# # generate the goldsets
lda_model = Lda(project)
# # train the LDA model
dv_model = DV(project)
# # train the DV model
lda_ranks = lda_model.get_ranks()
dv_ranks = dv_model.get_ranks()
# # get the rank for the models(feature location)
print(util.calculate_mrr(lda_ranks))
print(util.calculate_mrr(dv_ranks))
# # print the mrr

