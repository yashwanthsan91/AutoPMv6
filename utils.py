import json
import os
import sqlite3
import pandas as pd
from datetime import datetime
import random
import shutil
import glob

DB_FILE = os.path.join(os.path.dirname(__file__), 'project_tracker.db')
BACKUP_DIR = os.path.join(os.path.dirname(__file__), 'backups')

def init_db():
    """Initializes the database tables."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Check if table exists, if not create
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS project_deliverables (
            id INTEGER PRIMARY KEY,
            project_id INTEGER,
            gateway_stage TEXT,
            deliverable_name TEXT,
            status TEXT DEFAULT 'Pending',
            evidence_link TEXT,
            remarks TEXT
        )
    """)
    conn.commit()
    conn.close()

# Initialize on module load (safe for app start)
init_db()

def load_data():
    """Loads projects from the SQLite database and reconstructs the nested dictionary."""
    if not os.path.exists(DB_FILE):
        return []

    projects = []
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row # Access columns by name
        cursor = conn.cursor()
        
        # 1. Fetch Projects
        cursor.execute("SELECT * FROM projects")
        projs_db = cursor.fetchall()
        
        for p_row in projs_db:
            p = {
                "id": p_row["id"],
                "name": p_row["name"],
                "type": p_row["type"],
                "gateways": {},
                "type": p_row["type"],
                "gateways": {},
                "modules": [],
                "deliverables": []
            }
            
            # Fetch Project Deliverables
            try:
                cursor.execute("SELECT * FROM project_deliverables WHERE project_id=?", (p["id"],))
                delivs = cursor.fetchall()
                for d in delivs:
                    p["deliverables"].append({
                        "id": d["id"],
                        "gateway_stage": d["gateway_stage"],
                        "deliverable_name": d["deliverable_name"],
                        "status": d["status"],
                        "evidence_link": d["evidence_link"],
                        "remarks": d["remarks"]
                    })
            except Exception as e:
                pass # Table might not exist yet if mid-migration
            
            # Fetch Project Gateways
            cursor.execute("SELECT * FROM gateways WHERE entity_type='project' AND entity_id=?", (p["id"],))
            p_gws = cursor.fetchall()
            for gw in p_gws:
                 p["gateways"][gw["gateway"]] = {
                    "p": gw["plan_date"],
                    "a": gw["actual_date"] if gw["actual_date"] else ""
                }
            
            # 2. Fetch Modules (Top Level)
            cursor.execute("SELECT * FROM modules WHERE project_id=? AND parent_module_id IS NULL", (p["id"],))
            mods_db = cursor.fetchall()
            
            for m_row in mods_db:
                m = {
                    "id": m_row["id"],
                    "name": m_row["name"],
                    "gateways": {},
                    "sub_modules": []
                }
                
                # Fetch Module Gateways
                cursor.execute("SELECT * FROM gateways WHERE entity_type='module' AND entity_id=?", (m["id"],))
                m_gws = cursor.fetchall()
                for gw in m_gws:
                    m["gateways"][gw["gateway"]] = {
                        "p": gw["plan_date"],
                        "a": gw["actual_date"],
                        "ecn": gw["ecn"]
                    }
                
                # 3. Fetch Sub-Modules
                cursor.execute("SELECT * FROM modules WHERE project_id=? AND parent_module_id=?", (p["id"], m["id"]))
                subs_db = cursor.fetchall()
                for s_row in subs_db:
                    s = {
                        "id": s_row["id"],
                        "name": s_row["name"],
                        "gateways": {}
                    }
                    # Fetch Sub-Module Gateways
                    cursor.execute("SELECT * FROM gateways WHERE entity_type='module' AND entity_id=?", (s["id"],))
                    s_gws = cursor.fetchall()
                    for gw in s_gws:
                        s["gateways"][gw["gateway"]] = {
                            "p": gw["plan_date"],
                            "a": gw["actual_date"],
                            "ecn": gw["ecn"]
                        }
                    m["sub_modules"].append(s)
                
                p["modules"].append(m)
            
            projects.append(p)
            
        conn.close()
        
        # Ensure Rollups are calculated on Load to guarantee consistency
        calculate_rollup(projects)
        
        return projects
    except Exception as e:
        print(f"Error loading data from DB: {e}")
        return []

def save_data(projects):
    """Saves projects to the SQLite database (Full Sync)."""
    try:
        # Pre-calculation Rollup
        calculate_rollup(projects)

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Transaction: Delete All -> Insert All
        # This ensures we match the in-memory state exactly
        cursor.execute("DELETE FROM gateways")
        cursor.execute("DELETE FROM modules")
        cursor.execute("DELETE FROM gateways")
        cursor.execute("DELETE FROM modules")
        cursor.execute("DELETE FROM projects")
        cursor.execute("DELETE FROM project_deliverables")
        
        for p in projects:
            cursor.execute("INSERT INTO projects (id, name, type) VALUES (?, ?, ?)", 
                           (p['id'], p['name'], p.get('type', '')))
            
            # Project Gateways
            for gw, data in p.get('gateways', {}).items():
                if isinstance(data, dict):
                     cursor.execute("INSERT INTO gateways (entity_type, entity_id, gateway, plan_date, actual_date) VALUES (?, ?, ?, ?, ?)",
                                   ('project', p['id'], gw, data.get('p', ''), data.get('a', '')))
                else: 
                     # Fallback for old structure if any runtime obj somehow missed rollup
                     cursor.execute("INSERT INTO gateways (entity_type, entity_id, gateway, plan_date) VALUES (?, ?, ?, ?)",
                                   ('project', p['id'], gw, data))
            
            if 'modules' in p:
                for m in p['modules']:
                    cursor.execute("INSERT INTO modules (id, project_id, name) VALUES (?, ?, ?)",
                                   (m['id'], p['id'], m['name']))
                    
                    # Module Gateways
                    for gw, data in m.get('gateways', {}).items():
                        if isinstance(data, dict):
                            cursor.execute("INSERT INTO gateways (entity_type, entity_id, gateway, plan_date, actual_date, ecn) VALUES (?, ?, ?, ?, ?, ?)",
                                           ('module', m['id'], gw, data.get('p', ''), data.get('a', ''), data.get('ecn', '')))
                    
                    if 'sub_modules' in m:
                        for s in m['sub_modules']:
                            cursor.execute("INSERT INTO modules (id, project_id, name, parent_module_id) VALUES (?, ?, ?, ?)",
                                           (s['id'], p['id'], s['name'], m['id']))
                            
                            for gw, data in s.get('gateways', {}).items():
                                if isinstance(data, dict):
                                    cursor.execute("INSERT INTO gateways (entity_type, entity_id, gateway, plan_date, actual_date, ecn) VALUES (?, ?, ?, ?, ?, ?)",
                                                   ('module', s['id'], gw, data.get('p', ''), data.get('a', ''), data.get('ecn', '')))
            
            # Project Deliverables
            if 'deliverables' in p:
                for d in p['deliverables']:
                    cursor.execute("""
                        INSERT INTO project_deliverables (id, project_id, gateway_stage, deliverable_name, status, evidence_link, remarks)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (d.get('id'), p['id'], d.get('gateway_stage'), d.get('deliverable_name'), d.get('status', 'Pending'), d.get('evidence_link', ''), d.get('remarks', '')))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving data to DB: {e}")
    except Exception as e:
        print(f"Error saving data to DB: {e}")
        return False

def backup_database():
    """
    Creates a timestamped backup of the database and maintains only the 30 most recent backups.
    """
    if not os.path.exists(DB_FILE):
        return "No DB found"
        
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    backup_filename = f"backup_{timestamp}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    try:
        shutil.copy2(DB_FILE, backup_path)
        print(f"Backup created: {backup_filename}")
        
        # Housekeeping: Keep only last 30
        backups = sorted(glob.glob(os.path.join(BACKUP_DIR, "backup_*.db")), key=os.path.getmtime)
        while len(backups) > 30:
            oldest = backups.pop(0)
            os.remove(oldest)
            print(f"Deleted old backup: {oldest}")
            
        return True
    except Exception as e:
        print(f"Backup failed: {e}")
        return False

def get_status(plan, actual):
    """
    Calculates status based on Plan vs Actual dates.
    Returns: 'green', 'yellow', 'red', 'grey'
    Logic:
    - No plan or no actual: grey (Pending)
    - Actual <= Plan: green (On Track)
    - Actual > Plan by <= 30 days: yellow (At Risk)
    - Actual > Plan by > 30 days: red (Critical)
    """
    if not plan or not actual:
        return 'grey'
    
    try:
        p_date = datetime.strptime(plan, "%Y-%m-%d")
        a_date = datetime.strptime(actual, "%Y-%m-%d")
        
        diff = (a_date - p_date).days
        
        if diff <= 0:
            return 'green'
        elif diff <= 30:
            return 'yellow'
        else:
            return 'red'
    except ValueError:
        return 'grey'

def calculate_dashboard_stats(projects):
    """Calculates summary statistics for the dashboard."""
    total_projects = len(projects)
    
    green = 0
    yellow = 0
    red = 0
    
    for p in projects:
        # User Logic: D4 > D3 > D2 > D1.
        # "Identify the module released last... update respective projects"
        # CORRECTED Strategy:
        # 1. Find the *Latest Gateway* (highest D-level) that has ANY actual data (Max Actual).
        # 2. The Project Status is SOLELY determined by that one gateway's status.
        #    Historical delays (e.g. D2 was late, but we are now at D3) are ignored for the Top-Level Status Card.
        
        p_status = 'green'
        
        p_status = 'green'
        
        gw_keys = ['D0', 'D1', 'D2', 'D3', 'D4']
        
        # Find the latest gateway that has been "released" (has actuals)
        latest_released_gw = None
        latest_actual = None
        latest_plan = None
        
        for gw in gw_keys:
            # Data is now guaranteed to be dict by load_data/rollup
            gw_data = p['gateways'].get(gw, {})
            plan = gw_data.get('p')
            actual = gw_data.get('a')
            
            if actual:
                latest_released_gw = gw
                latest_actual = actual
                latest_plan = plan
        
        # If we found a latest released gateway, use its status
        if latest_released_gw and latest_plan:
            p_status = get_status(latest_plan, latest_actual)
            if p_status == 'grey': p_status = 'green'

        if p_status == 'green': green += 1
        elif p_status == 'yellow': yellow += 1
        elif p_status == 'red': red += 1

    return {
        "total": total_projects,
        "active": total_projects,
        "green": green,
        "yellow": yellow,
        "red": red
    }

def calculate_rollup(projects):
    """
    Performs Bottom-Up Date Rollup:
    1. Module Actual = Max(Sub-Module Actuals)
    2. Project Actual = Max(Module Actuals)
    Updates 'projects' in-place.
    """
    for p in projects:
        # 1. Rollup Sub-Modules to Modules
        if 'modules' in p:
            for m in p['modules']:
                 # Only if sub-modules exist
                if m.get('sub_modules'):
                    for gw in ['D0', 'D1', 'D2', 'D3', 'D4']:
                        max_date = None
                        for s in m['sub_modules']:
                            s_act = s['gateways'].get(gw, {}).get('a')
                            if s_act:
                                if max_date is None or s_act > max_date:
                                    max_date = s_act
                        
                        # Update Module Actual if valid max found
                        if max_date:
                            if gw not in m['gateways']: m['gateways'][gw] = {'p':'', 'a':'', 'ecn':''}
                            m['gateways'][gw]['a'] = max_date
                        else:
                            # If sub-modules exist but have no actuals, current Module Actual should be cleared
                            # This enforces strict rollup
                            if gw in m['gateways']:
                                m['gateways'][gw]['a'] = ""
        
        # 2. Rollup Modules to Project
        if 'modules' in p:
            for gw in ['D0', 'D1', 'D2', 'D3', 'D4']:
                max_date = None
                for m in p['modules']:
                    m_act = m['gateways'].get(gw, {}).get('a')
                    if m_act:
                        if max_date is None or m_act > max_date:
                            max_date = m_act
                
                # Update Project Actual
                if max_date:
                    if gw not in p['gateways']: 
                        p['gateways'][gw] = {'p':'', 'a':''}
                    # Ensure p['gateways'][gw] is dict (handled by load_data now)
                    if isinstance(p['gateways'][gw], str): # Handle legacy if not loaded via new load_data yet
                         p['gateways'][gw] = {'p': p['gateways'][gw], 'a': ''}
                    
                    p['gateways'][gw]['a'] = max_date
                else:
                    # If modules exist but all are empty, clear Project Actual
                    if gw in p['gateways'] and isinstance(p['gateways'][gw], dict):
                        p['gateways'][gw]['a'] = ""

def prepare_gantt_data(projects):
    """Prepares data for Plotly Gantt chart."""
    df_data = []
    
    for p in projects:
        # Project Level Bar (Overall duration D0 -> D4)
        p_start = p['gateways'].get('D0', {}).get('p')
        p_end = p['gateways'].get('D4', {}).get('p')
        
        if p_start and p_end:
             df_data.append({
                "Task": p['name'],
                "Start": p_start,
                "Finish": p_end,
                "Resource": "Project Plan",
                "Type": "Project",
                "Status": "Plan",
                "Project": p['name']
            })

        # Module Level Bars
        # We can visualize module gateways as milestones or phases
        # For simplicity in V3 1st pass, let's show gateways as points or small bars
        if p.get('modules'):
            for m in p['modules']:
                 # Create a "Task" for each module
                 # To visualize statuses, we might need a different approach than simple Gantt
                 # Let's try to map "Active Phase"
                 pass
                 
    # For a Release Matrix view (Month-wise), we might want a simple timeline
    # returning plain list for now, will implement Plotly logic in app.py directly or here
    return df_data

def get_matrix_data(projects):
    """
    Returns a structured list for the Release Matrix view using Plotly Timeline or similar.
    We wan to see: Project -> Module -> [Gateway Dots on Timeline]
    """

def calculate_project_readiness(project_id):
    """
    Calculates the detailed validation readiness score for a project.
    
    Formula:
    1. Identify Active Stages based on Gateway Actual Dates.
       Default: ['D0']
       If d1_actual exists -> add 'D1', etc.
       
    2. Filter deliverables:
       WHERE project_id = ? AND gateway_stage IN (active_stages)
       
    3. Score:
       (Count(Completed + NA) / Total_Applicable) * 100
       
    Returns: (score_float, summary_string)
    """
    score = 0.0
    summary = "0/0 Items"
    
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. Identify Active Gateways
        # Fetch gateway actuals for this project
        cursor.execute("SELECT gateway, actual_date FROM gateways WHERE entity_type='project' AND entity_id=?", (project_id,))
        rows = cursor.fetchall()
        
        active_stages = ['D0'] # Default start
        
        # Check actual dates
        # Map: D0->D0, D1->D1 ...
        # If D0 actual exists, it's already in (set logic handles dupes or simply checks)
        # Actually logic is: if actual exists for a stage, that stage's deliverables are applicable.
        
        # Create map of existing actuals
        actuals_map = {row['gateway']: row['actual_date'] for row in rows if row['actual_date']}
        
        for gw in ['D0', 'D1', 'D2', 'D3', 'D4']:
            if gw in actuals_map and actuals_map[gw]:
                if gw not in active_stages:
                    active_stages.append(gw)
                    
        # 2. Filter Deliverables
        if not active_stages:
             active_stages = ['D0']
             
        # Build query safely
        placeholders = ','.join(['?'] * len(active_stages))
        query = f"SELECT status FROM project_deliverables WHERE project_id=? AND gateway_stage IN ({placeholders})"
        params = [project_id] + active_stages
        
        cursor.execute(query, params)
        delivs = cursor.fetchall()
        
        total_items = len(delivs)
        achieved_items = 0
        
        for d in delivs:
            if d['status'] in ['Completed', 'NA', 'N/A']: # Handle variation just in case
                achieved_items += 1
                
        if total_items > 0:
            score = (achieved_items / total_items) * 100
        else:
            score = 0.0
            
        summary = f"{achieved_items}/{total_items} Items"
        
        conn.close()
        return score, summary
        
    except Exception as e:
        print(f"Error calculating readiness: {e}")
        return 0.0, "Error"

def populate_deliverables(project_id, project_type):
    """
    Generates a list of deliverables based on the Master Checklist CSV.
    """
    csv_path = os.path.join(os.path.dirname(__file__), 'master_gateway_checklist.csv')
    if not os.path.exists(csv_path):
        return []

    try:
        df = pd.read_csv(csv_path)
        # Filter based on type
        # Column names expected: Gateway, Delivarables, Major, Minor
        
        # Normalize column names to be safe
        df.columns = df.columns.str.strip()
        
        filtered_df = pd.DataFrame()
        
        if project_type == 'Major':
            filtered_df = df[df['Major'].str.upper() == 'YES']
        elif project_type == 'Minor':
            filtered_df = df[df['Minor'].str.upper() == 'YES']
        else:
            # Default or Carryover? Maybe assumes same as Minor or None?
            # User instructions "If Major... If Minor...".
            # Let's assume defaulting to all or none? "Carryover" usually has minimal.
            # Returning empty for other types for now unless user specifies.
            return []
            
        deliverables = []
        for _, row in filtered_df.iterrows():
            deliverables.append({
                "id": int(datetime.now().timestamp() * 1000) + random.randint(0, 9999),
                "gateway_stage": row.get('Gateway', ''),
                "deliverable_name": row.get('Delivarables', ''), # Using user's spelling
                "status": "Pending",
                "evidence_link": "",
                "remarks": ""
            })
            
        return deliverables
            
    except Exception as e:
        print(f"Error populating deliverables: {e}")
        return []

def projects_to_csv(projects):
    """Converts the nested project list into a flattened CSV string."""
    flat_data = []
    
    for p in projects:
        # Base project data
        base_row = {
            "Project ID": p['id'],
            "Project Name": p['name'],
            "Type": p.get('type', ''),
            "P_D0": p['gateways'].get('D0', {}).get('p', ''),
            "P_D1": p['gateways'].get('D1', {}).get('p', ''),
            "P_D2": p['gateways'].get('D2', {}).get('p', ''),
            "P_D3": p['gateways'].get('D3', {}).get('p', ''),
            "P_D4": p['gateways'].get('D4', {}).get('p', '')
        }
        
        # 1. Project Level Row? Or just Module Rows?
        # Usually users want 1 row per module.
        # If no modules, add 1 row for project.
        
        if not p.get('modules'):
            flat_data.append(base_row)
        else:
            for m in p['modules']:
                row = base_row.copy()
                row.update({
                    "Module ID": m['id'],
                    "Module Name": m['name'],
                    "Parent Module": "" # For sub-modules
                })
                
                # Module Gateways
                for gw in ['D0', 'D1', 'D2', 'D3', 'D4']:
                    g_data = m['gateways'].get(gw, {})
                    row[f"{gw}_Act"] = g_data.get('a', '')
                    row[f"{gw}_ECN"] = g_data.get('ecn', '')
                    
                flat_data.append(row)
                
                # Sub-modules
                if m.get('sub_modules'):
                    for s in m['sub_modules']:
                        s_row = base_row.copy()
                        s_row.update({
                            "Module ID": s['id'],
                            "Module Name": s['name'],
                            "Parent Module": m['name']
                        })
                        for gw in ['D0', 'D1', 'D2', 'D3', 'D4']:
                            sg_data = s['gateways'].get(gw, {})
                            s_row[f"{gw}_Act"] = sg_data.get('a', '')
                            s_row[f"{gw}_ECN"] = sg_data.get('ecn', '')
                        flat_data.append(s_row)

    if not flat_data:
        return ""
        
    df = pd.DataFrame(flat_data)
    # Reorder columns for logical flow if needed, but dict order is usually preserved in Py3.7+
    # Ensure key columns come first
    cols = ["Project Name", "Type", "Module Name", "Parent Module"] + \
           [c for c in df.columns if c not in ["Project ID", "Project Name", "Type", "Module ID", "Module Name", "Parent Module"]]
    
    # Handle missing columns if data is empty
    existing_cols = [c for c in cols if c in df.columns]
    
    return df[existing_cols].to_csv(index=False)
    return df[existing_cols].to_csv(index=False)

def projects_to_excel(projects):
    """Converts the nested project list into an Excel byte stream."""
    import io
    flat_data = []
    
    for p in projects:
        base_row = {
            "Project ID": p['id'],
            "Project Name": p['name'],
            "Type": p.get('type', ''),
            "P_D0": p['gateways'].get('D0', {}).get('p', ''),
            "P_D1": p['gateways'].get('D1', {}).get('p', ''),
            "P_D2": p['gateways'].get('D2', {}).get('p', ''),
            "P_D3": p['gateways'].get('D3', {}).get('p', ''),
            "P_D4": p['gateways'].get('D4', {}).get('p', '')
        }
        
        if not p.get('modules'):
            flat_data.append(base_row)
        else:
            for m in p['modules']:
                row = base_row.copy()
                row.update({
                    "Module ID": m['id'],
                    "Module Name": m['name'],
                    "Parent Module": ""
                })
                for gw in ['D0', 'D1', 'D2', 'D3', 'D4']:
                    g_data = m['gateways'].get(gw, {})
                    row[f"{gw}_Act"] = g_data.get('a', '')
                    row[f"{gw}_ECN"] = g_data.get('ecn', '')
                flat_data.append(row)
                
                if m.get('sub_modules'):
                    for s in m['sub_modules']:
                        s_row = base_row.copy()
                        s_row.update({
                            "Module ID": s['id'],
                            "Module Name": s['name'],
                            "Parent Module": m['name']
                        })
                        for gw in ['D0', 'D1', 'D2', 'D3', 'D4']:
                            sg_data = s['gateways'].get(gw, {})
                            s_row[f"{gw}_Act"] = sg_data.get('a', '')
                            s_row[f"{gw}_ECN"] = sg_data.get('ecn', '')
                        flat_data.append(s_row)

    output = io.BytesIO()
    if flat_data:
        df = pd.DataFrame(flat_data)
        cols = ["Project Name", "Type", "Module Name", "Parent Module"] + \
               [c for c in df.columns if c not in ["Project ID", "Project Name", "Type", "Module ID", "Module Name", "Parent Module"]]
        existing_cols = [c for c in cols if c in df.columns]
        
        # Write to Excel buffer
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df[existing_cols].to_excel(writer, index=False, sheet_name='Status Report')
    else:
        # Create empty excel
        pd.DataFrame().to_excel(output, index=False)
        
    output.seek(0)
    return output

def get_csv_template_data():
    """Returns a CSV string with headers for the upload template."""
    headers = [
        "Project Name", "Type", 
        "Module Name", "Parent Module",
        "P_D0", "P_D1", "P_D2", "P_D3", "P_D4",
        "D0_Act", "D0_ECN",
        "D1_Act", "D1_ECN",
        "D2_Act", "D2_ECN",
        "D3_Act", "D3_ECN",
        "D4_Act", "D4_ECN"
    ]
    return ",".join(headers)

def process_csv_upload(csv_file, current_projects):
    """
    Parses an uploaded CSV file and updates the projects list.
    Merges new data with existing projects/modules.
    """
    try:
        df = pd.read_csv(csv_file)
        
        # Standardize column names (optional, but good for robustness)
        df.columns = df.columns.str.strip()
        
        # Helper to safely get value
        def get_val(row, col):
            val = row.get(col)
            if pd.isna(val) or val == "":
                return ""
            return str(val).strip()

        # Index existing projects for quick lookup
        proj_map = {p['name']: p for p in current_projects}
        
        for _, row in df.iterrows():
            p_name = get_val(row, "Project Name")
            if not p_name: continue # Skip empty rows
            
            p_type = get_val(row, "Type")
            
            # --- Project Handling ---
            if p_name not in proj_map:
                new_p = {
                    "id": int(datetime.now().timestamp() * 1000) + random.randint(0, 999),
                    "name": p_name,
                    "type": p_type if p_type else "New",
                    "gateways": {},
                    "modules": []
                }
                current_projects.append(new_p)
                proj_map[p_name] = new_p
            
            p = proj_map[p_name]
            # Update Project Type if provided
            if p_type: p['type'] = p_type
            
            # Update Project Gateways (Plan only usually at project level from CSV, but we can support both)
            # Actually, per schema, P_D0... are typically Plan dates.
            for gw in ['D0', 'D1', 'D2', 'D3', 'D4']:
                p_date = get_val(row, f"P_{gw}")
                if p_date:
                    if gw not in p['gateways'] or not isinstance(p['gateways'][gw], dict):
                         p['gateways'][gw] = {'p': p_date, 'a': ''}
                    else:
                         p['gateways'][gw]['p'] = p_date

            # --- Module Handling ---
            m_name = get_val(row, "Module Name")
            if m_name:
                parent_m_name = get_val(row, "Parent Module")
                
                # Find or Create Module
                # Hierarchy: Project -> Module -> SubModule
                
                target_module = None
                is_sub = False
                
                # Check if this is a sub-module
                if parent_m_name:
                    # Find parent first
                    parent = next((m for m in p['modules'] if m['name'] == parent_m_name), None)
                    if parent:
                        if 'sub_modules' not in parent: parent['sub_modules'] = []
                        
                        target_module = next((s for s in parent['sub_modules'] if s['name'] == m_name), None)
                        if not target_module:
                            target_module = {
                                "id": int(datetime.now().timestamp() * 1000) + random.randint(0, 999),
                                "name": m_name,
                                "gateways": {}
                            }
                            parent['sub_modules'].append(target_module)
                            is_sub = True
                    else:
                        # Fallback: Treat as root module if parent not found? Or Create Parent?
                        # For simplicity, treat as root and log warning? or just create root.
                        # Let's create as root for now to avoid data loss.
                        pass 

                if not target_module and not is_sub:
                     # Search top-level modules
                    target_module = next((m for m in p['modules'] if m['name'] == m_name), None)
                    if not target_module:
                        target_module = {
                            "id": int(datetime.now().timestamp() * 1000) + random.randint(0, 999),
                            "name": m_name,
                            "gateways": {},
                            "sub_modules": []
                        }
                        p['modules'].append(target_module)
                
                # --- Update Module Gateways ---
                if target_module:
                    for gw in ['D0', 'D1', 'D2', 'D3', 'D4']:
                        # Ensure Gateway dict exists
                        if gw not in target_module['gateways']: target_module['gateways'][gw] = {}
                        
                        p_d = get_val(row, f"P_{gw}") # Plan might come from row, but typically Project Plan is project level.
                        # If user puts different plans for modules, we could support it, but data structure usually links module plan to project plan?
                        # Actually earlier structure has 'p' in module gateways too.
                        
                        act_d = get_val(row, f"{gw}_Act")
                        ecn = get_val(row, f"{gw}_ECN")
                        
                        if p_d: target_module['gateways'][gw]['p'] = p_d
                        if act_d: target_module['gateways'][gw]['a'] = act_d
                        if ecn: target_module['gateways'][gw]['ecn'] = ecn

        return current_projects, "Success"
        
    except Exception as e:
        return current_projects, f"Error processing CSV: {str(e)}"

