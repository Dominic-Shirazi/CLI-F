import subprocess
import os

def run_git(args, cwd=None):
    """Helper to run git commands and return output."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd or os.getcwd(),
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Git error: {e.stderr}")
        return None

def init_repo():
    """Ensures the workspace is a git repo and has required .gitignore."""
    # 1. Initialize if not already
    if not os.path.exists(".git"):
        run_git(["init"])
        run_git(["add", "."])
        run_git(["commit", "-m", "Initial commit before V2 start"])

    # 2. Ensure .gitignore isolation for agent state
    gitignore_path = ".gitignore"
    required_ignores = [
        "workspace/gemini_output/reasoning.md",
        "workspace/current_task.md",
        ".test_folder/",
        "__pycache__/",
        "*.pyc",
        ".env"
    ]
    
    existing_ignores = []
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            existing_ignores = [line.strip() for line in f.readlines()]
            
    updated = False
    with open(gitignore_path, "a") as f:
        for ignore in required_ignores:
            if ignore not in existing_ignores:
                f.write(f"\n{ignore}")
                updated = True
    
    if updated:
        run_git(["add", ".gitignore"])
        run_git(["commit", "-m", "System: Updated .gitignore for V2 state isolation"])

def get_diff_stat():
    """Returns modified + new/untracked file summary for the inspector."""
    diff = run_git(["diff", "--stat"]) or ""
    # Use ls-files to get full paths of untracked files (git status --short only shows top-level dirs)
    untracked = run_git(["ls-files", "--others", "--exclude-standard"]) or ""
    new_files = [line.strip() for line in untracked.splitlines() if line.strip()]
    parts = []
    if diff:
        parts.append(diff)
    if new_files:
        parts.append("New untracked files:\n" + "\n".join(f"  {f}" for f in new_files))
    return "\n".join(parts) if parts else "No changes detected."

def get_full_diff():
    """Returns 'git diff' of uncommitted changes."""
    return run_git(["diff"]) or ""

def commit_step(step_name):
    """Stages all changes and commits them with the step name."""
    run_git(["add", "."])
    msg = f"V2 Step: {step_name}"
    run_git(["commit", "-m", msg])

def revert_uncommitted():
    """Reverts all uncommitted changes (git checkout . && git clean -fd)."""
    run_git(["checkout", "."])
    run_git(["clean", "-fd"])
