import sys
sys.path.append('.')
from system.git_ops import init_repo, get_diff_stat, commit_step

print("Initializing repo...")
init_repo()
print("Repo initialized.")

with open("test.txt", "w") as f:
    f.write("Testing git_ops")

stat = get_diff_stat()
print(f"Diff stat: {stat}")

commit_step("Initial Test")
print("Commit complete.")

# Cleanup test file
import os
os.remove("test.txt")
