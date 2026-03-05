import os
import zipfile
import argparse
import sys
import shutil

# Mapping of file names in the ZIP to their destination paths relative to the project root
FILE_MAPPING = {
    "MASTER_PLAN.md": "brain/MASTER_PLAN.md",
    "SUCCESS_CRITERIA.md": "brain/SUCCESS_CRITERIA.md",
    "ENVIRONMENT_RULES.md": "brain/ENVIRONMENT_RULES.md",
    "CLAUDE.md": "CLAUDE.md",
    "GEMINI.md": "GEMINI.md",
    "env.example": ".env.example",
    "project-default.json": "system/profiles/project-default.json",
    "writer.md": "prompts/standard/writer.md",
    "inspector.md": "prompts/standard/inspector.md",
    "reviewer.md": "prompts/standard/reviewer.md"
}

DROP_ZONE = "tools/project_genesis/drop_zone"

def main():
    parser = argparse.ArgumentParser(description="Deploy AI-generated project files from a zip archive.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files without asking.")
    parser.add_argument("--dry-run", action="store_true", help="Validate the zip and show what would be done without writing any files.")
    args = parser.parse_args()

    # 1. Look for exactly one .zip file in drop_zone/
    if not os.path.exists(DROP_ZONE):
        print(f"Error: Drop zone directory '{DROP_ZONE}' not found.")
        sys.exit(1)

    zip_files = [f for f in os.listdir(DROP_ZONE) if f.lower().endswith(".zip")]

    if len(zip_files) == 0:
        print(f"Error: No .zip files found in {DROP_ZONE}/. Please drop your genesis_output.zip there.")
        sys.exit(1)
    
    if len(zip_files) > 1:
        print(f"Error: Multiple .zip files found in {DROP_ZONE}/. Please ensure there is only one.")
        sys.exit(1)

    zip_path = os.path.join(DROP_ZONE, zip_files[0])
    print(f"Found zip: {zip_path}")

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_contents = zip_ref.namelist()

            # 2. Validate the zip contains all 10 required files
            missing_files = []
            for required_file in FILE_MAPPING.keys():
                if required_file not in zip_contents:
                    missing_files.append(required_file)
            
            if missing_files:
                print("Error: The following required files are missing from the zip archive:")
                for f in missing_files:
                    print(f"  - {f}")
                sys.exit(1)

            print("Validation successful. All required files present.")

            # 4. Extract each file to its destination path
            for zip_file, dest_path in FILE_MAPPING.items():
                dest_dir = os.path.dirname(dest_path)
                
                if dest_dir and not os.path.exists(dest_dir) and not args.dry_run:
                    os.makedirs(dest_dir, exist_ok=True)

                if os.path.exists(dest_path) and not args.force and not args.dry_run:
                    print(f"Skipping {dest_path} (file already exists). Use --force to overwrite.")
                    continue

                if not args.dry_run:
                    # Extract to a temp file first then move to avoid issues with absolute paths in zip if any
                    with zip_ref.open(zip_file) as source, open(dest_path, "wb") as target:
                        shutil.copyfileobj(source, target)
                    print(f"✓ {zip_file} → {dest_path}")
                else:
                    print(f"Would extract: {zip_file} → {dest_path}")

    except zipfile.BadZipFile:
        print(f"Error: '{zip_path}' is not a valid zip file.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

    if args.dry_run:
        print("\nDry run completed. No files were written.")
    else:
        print("\nDeployment complete! Next steps:")
        print("1. Open .env and fill in your API keys (copy from .env.example if needed).")
        print("2. Run 'python main.py' to start your project.")

if __name__ == "__main__":
    main()
