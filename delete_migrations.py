import os
import sys

def find_migrations_folders():
    """
    Locate all 'migrations' folders inside Django apps.
    
    Returns:
        A list of paths to migrations folders.
    """
    project_path = os.getcwd()  # Get the current working directory
    migrations_folders = []

    # Walk through all directories in the project
    for root, dirs, files in os.walk(project_path):
        if 'migrations' in dirs:
            migrations_path = os.path.join(root, 'migrations')
            migrations_folders.append(migrations_path)

    return migrations_folders

def delete_migration_files():
    """
    Delete all migration files except __init__.py in each Django app's 'migrations' folder.
    """
    migrations_folders = find_migrations_folders()

    if not migrations_folders:
        print("No migrations folders found in the project.")
        return
    
    print("The following migrations folders were found:")
    for folder in migrations_folders:
        print(f"- {folder}")

    confirm = input("Are you sure you want to delete all migration files? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("Operation cancelled.")
        return

    deleted_count = 0

    for migrations_path in migrations_folders:
        for filename in os.listdir(migrations_path):
            if filename == '__init__.py':
                continue  # Keep __init__.py

            file_path = os.path.join(migrations_path, filename)

            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                    print(f"Deleted: {file_path}")
                    deleted_count += 1
                elif os.path.isdir(file_path):  # In case of subdirectories inside migrations
                    import shutil
                    shutil.rmtree(file_path)
                    print(f"Deleted folder: {file_path}")
                    deleted_count += 1
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")

    print(f"\n✅ Total migration files deleted: {deleted_count}")

if __name__ == "__main__":
    delete_migration_files()
