import os

ans = 0
for dirname,dirnames,filenames in os.walk('.'):
	for filename in filenames:
		if filename.endswith('.py'):
			full_path = os.path.join(dirname,filename)  
			print(full_path)
			with open(full_path) as f:
				ans+=len(f.read().strip().split())
print(ans)



