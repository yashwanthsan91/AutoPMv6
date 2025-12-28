
import utils
import sqlite3
import os

DB_FILE = "project_tracker.db"

def test_load():
    print("Testing utils.load_data()...")
    projects = utils.load_data()
    print(f"Loaded {len(projects)} projects.")
    
    for p in projects:
        print(f" - {p['name']} (ID: {p['id']})")
        print(f"   Gateways: {p.get('gateways')}")
        print(f"   Modules: {len(p.get('modules', []))}")
        for m in p.get('modules', []):
            print(f"     * {m['name']} (ID: {m['id']})")
            if m.get('sub_modules'):
                print(f"       Sub-modules: {len(m['sub_modules'])}")

def test_save():
    print("\nTesting utils.save_data()...")
    projects = utils.load_data()
    if not projects:
        print("No projects to save.")
        return

    # Modify something small
    projects[0]['name'] = projects[0]['name'] + " (Updated)"
    
    success = utils.save_data(projects)
    if success:
        print("Save successful.")
        
        # Verify persistence
        projects_new = utils.load_data()
        print(f"New Name: {projects_new[0]['name']}")
    else:
        print("Save failed.")

if __name__ == "__main__":
    if not os.path.exists(DB_FILE):
        print("DB file not found!")
    else:
        test_load()
        test_save()
