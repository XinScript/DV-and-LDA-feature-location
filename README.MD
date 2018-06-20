# Explore The Use of Machine Learning for Feature Location Techniques
The project is about investigation into the effectiveness of the use of machine learning techniques for feature location.
The project is still ongoing.

## WorkFlow
### 1.Goldset Generation
In order to evaluate the performance of the models, validation is neccessary. Goldset is a map between git commit message and changed information (e.g. function and class). It is retrieved from git logs by analyzing the difference versions of the codes. In this project, a certain amount of open-source projects is used for generating goldsets.

### 2.Model Training
By using the whole code base as corpora, topic modeling algorithms like Doucment Vectors and LDA are applied to generate models that used for feature location.

### 3.Rank
With trained models, the similarities between a query and source files are computed hence rank is obtained.
This process is exactly the same precedure of feature locaiton.

## Evaluation
### Metric
In this project **Mean Reciprocal Rank** (MRR) is used as metric.
### Variables
Investigation into factors that might affect effectiveness of FLTs( different algorithms, parameters of the algorithm, different programming languages, etc.)

## Conclusions
It turns out that LDA performs much better than DV in terms feature location at the level of file.
More details regarding the results and how to reproduce the same approach is available in the appendix. 
        	
## Modules
- Generator - different types of goldset generators
- Common - common modules such as git project information management, configuration
- Corpora - handle the source codes which is eventually used for learning   
- Model - Various topic modeling models that give out a rank list according to natural language queries


