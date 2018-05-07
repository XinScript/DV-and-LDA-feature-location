from git import Repo
p = '../sources/python/miro'
repo = Repo(p)

commits = list(repo.head.commit.iter_parents())

print(repo.references)
print(len(commits))


parents = list(repo.tags[0].commit.iter_parents())
print(len(parents))


parents = list(repo.tags[-1].commit.iter_parents())
print(len(parents))
