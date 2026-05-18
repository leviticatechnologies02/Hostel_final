import os

# ✅ 🔴 PASTE YOUR PROJECT PATH HERE
PROJECT_PATH = r"D:\hostel-management-api-2"
# For Mac/Linux:
# PROJECT_PATH = "/home/user/projects/myproject"

# ✅ Files and folders to ignore
IGNORE = {
    ".git",
    ".gitignore",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".DS_Store"
}

OUTPUT_FILE = "backend.txt"


def should_ignore(path):
    parts = path.split(os.sep)
    return any(part in IGNORE for part in parts)


def is_empty(content):
    return not content.strip()


def export_project(root_dir, output_path):
    with open(output_path, "w", encoding="utf-8") as output_file:
        for root, dirs, files in os.walk(root_dir):
            # ✅ Remove ignored directories
            dirs[:] = [d for d in dirs if d not in IGNORE]

            for file in files:
                if file in IGNORE:
                    continue

                file_path = os.path.join(root, file)

                if should_ignore(file_path):
                    continue

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    # ✅ Skip empty files
                    if is_empty(content):
                        continue

                    relative_path = os.path.relpath(file_path, root_dir)

                    output_file.write("\n" + "=" * 60 + "\n")
                    output_file.write(f"FILE: {relative_path}\n")
                    output_file.write("=" * 60 + "\n")
                    output_file.write(content + "\n")

                except Exception:
                    # ✅ Skip binary or unreadable files
                    continue


if __name__ == "__main__":
    if not os.path.exists(PROJECT_PATH):
        print("❌ Invalid project path.")
    else:
        export_project(PROJECT_PATH, OUTPUT_FILE)
        print(f"✅ Project exported to {OUTPUT_FILE} (empty files skipped)")