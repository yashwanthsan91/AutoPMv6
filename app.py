import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import utils
import utils_ai

# --- Configuration ---
st.set_page_config(
    page_title="Automotive Project Development Tracker",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="collapsed" # Hide sidebar by default
)

# --- Automatic Backup on Startup ---
@st.cache_resource
def run_backup_on_startup():
    utils.backup_database()
    return True

run_backup_on_startup()

# Custom CSS
# Custom CSS - Slate & Steel Theme
def apply_custom_styling():
    st.markdown("""
    <style>
        /* Global Font & Background */
        .main .block-container { padding-top: 2rem; }
        html, body, [class*="css"] {
            font-size: 18px; /* Increased Base Font */
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        /* Headers */
        h1, h2, h3 { 
            color: #003366 !important; /* Navy Blue */
            font-weight: 700 !important;
        }

        /* Card Styling for Containers/Expanders/Forms */
        div[data-testid="stExpander"], div[data-testid="stForm"], .dash-card {
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #e0e0e0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            margin-bottom: 20px;
        }
        
        /* Input Fields - Larger & Easier to click */
        .stTextInput input, .stSelectbox div[data-baseweb="select"] > div, .stNumberInput input, .stDateInput input {
            height: 50px; /* Taller inputs */
            font-size: 1.1rem;
        }
        
        /* Buttons */
        .stButton button {
            height: 50px;
            font-weight: 600;
            border-radius: 8px;
        }

        /* Scrollbar styling */
        ::-webkit-scrollbar { width: 10px; }
        ::-webkit-scrollbar-track { background: #f1f1f1; }
        ::-webkit-scrollbar-thumb { background: #888; }
        ::-webkit-scrollbar-thumb:hover { background: #555; }

    </style>
    """, unsafe_allow_html=True)

apply_custom_styling()

# --- Data Loading ---
projects = utils.load_data()


# --- App Header (Centered with Logo) ---
h_col1, h_col2, h_col3 = st.columns([1, 6, 1])
with h_col1:
    st.image("logo.png", width=100) # Logo at top left

with h_col2:
    st.markdown("<h1 style='text-align: center; margin-bottom: 30px;'>Automotive Project Development Tracker v6</h1>", unsafe_allow_html=True)



# --- Session State for Navigation ---
if 'view' not in st.session_state:
    st.session_state.view = "Dashboard"

def set_view(view_name):
    st.session_state.view = view_name

# --- Top Navigation Tiles ---
st.markdown("""
<style>
    div.stButton > button {
        width: 100%;
        height: 60px;
div.stButton > button:first-child {
    width: 100%;
    height: 3em; 
    font-weight: bold;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

nav_c1, nav_c2, nav_c3 = st.columns(3)

with nav_c1:
    if st.button("📊 Dashboard", type="primary" if st.session_state.view == "Dashboard" else "secondary"):
        set_view("Dashboard")
        st.rerun()

with nav_c2:
    if st.button("🏗️ Detailed Project View", type="primary" if st.session_state.view == "Detailed Project View" else "secondary"):
        set_view("Detailed Project View")
        st.rerun()

with nav_c3:
    if st.button("📋 Deliverables", type="primary" if st.session_state.view == "Deliverables Tracker" else "secondary"):
        set_view("Deliverables Tracker")
        st.rerun()


st.divider()

# --- Sidebar Disabled (User Request) ---
# Filters moved to main dashboard area
# Sidebar block removed effectively by not creating st.sidebar elements if not needed.
# Or we can keep it for "Advanced Settings" later, but for now user requested removal.


# --- Default Selection for First Load ---
all_types = sorted(list(set([p.get('type', 'Unknown') for p in projects])))
if 'selected_types' not in st.session_state:
    st.session_state.selected_types = all_types

# --- Filtering Logic (Placeholder, will be updated in Dashboard view) ---
# We initialize filtered_projects here but it will depend on the widget in Dashboard
# To make it accessible globally we might need to render the filter first or use session state.
# For now, we will render the filter inside the Dashboard view and update the list there.
# But other views need it too. So we should probably render the filter at the top OF THE DASHBOARD view only?
# Or TOP of ALL views? User said "Remove filters from left pane and add it to right side above the bar chart".
# This implies it's specific to the dashboard layout.
# However, "Release Matrix" also used 'filtered_projects'.
# We should probably put the filter in a common area if it affects all, BUT user instructions were specific to Dashboard placement.
# Let's assume Filter applies globally but is CONTROLED from the Dashboard (or we duplicate it/move it to top).
# For simplicity and compliance: I will put the filter control IN THE DASHBOARD VIEW as requested.
# For other views, I will either default to ALL or show a small filter expander.
# ACTUALLY, sticking to instructions: "add it to ... above the bar chart".
# So I will define filtered_projects based on session state, and update session state in Dashboard.

filtered_projects = [p for p in projects if p.get('type') in st.session_state.selected_types]
                
# --- Modals (Defined at top level to avoid NameError) ---
@st.dialog("➕ Create New Project")
def modal_create_project():
    with st.form("add_project_form"):
        new_name = st.text_input("Project Name")
        new_type = st.selectbox("Type", ["Major", "Minor", "Carryover"])
        c1, c2 = st.columns(2)
        d0_date = c1.date_input("D0 Start Date")
        num_modules = c2.number_input("Initial Modules", min_value=0, max_value=20, value=1)
        
        submitted = st.form_submit_button("Create Project")
        
        if submitted and new_name:
            new_id = int(datetime.now().timestamp())
            new_proj = {
                "id": new_id,
                "name": new_name,
                "type": new_type,
                "gateways": { 
                    "D0": { "p": str(d0_date), "a": "" }, 
                    "D1": { "p": "", "a": "" }, 
                    "D2": { "p": "", "a": "" }, 
                    "D3": { "p": "", "a": "" }, 
                    "D4": { "p": "", "a": "" } 
                },
                "modules": []
            }
            
            for i in range(num_modules):
                mod_id = new_id + i + 1
                project_gw_defaults = { "p": "", "a": "", "ecn": "" }
                # Set D0 Plan for module same as project start
                d0_gw = project_gw_defaults.copy()
                d0_gw['p'] = str(d0_date)
                
                new_proj['modules'].append({
                    "id": mod_id,
                    "name": f"Module {i+1}",
                    "gateways": { 
                        "D0": d0_gw, "D1": project_gw_defaults.copy(), 
                        "D2": project_gw_defaults.copy(), "D3": project_gw_defaults.copy(), 
                        "D4": project_gw_defaults.copy() 
                    }
                })
            
            # --- Dynamic Scope Population ---
            new_proj['deliverables'] = utils.populate_deliverables(new_id, new_type)
            
            projects.append(new_proj)
            if utils.save_data(projects):
                st.success(f"Project '{new_name}' created!")
                st.rerun()
            else:
                st.error("Failed to save.")

@st.dialog("📂 Upload Bulk Data (CSV)")
def modal_upload_csv():
    st.info("Upload a CSV file to bulk update projects. Data will be merged.")
    
    # Template Download
    template_csv = utils.get_csv_template_data()
    st.download_button(
        label="Download CSV Template",
        data=template_csv,
        file_name="bulk_upload_template.csv",
        mime="text/csv"
    )
    
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    
    if uploaded_file is not None:
        if st.button("Process Upload"):
            updated_projects, msg = utils.process_csv_upload(uploaded_file, projects)
            if msg == "Success":
                if utils.save_data(updated_projects):
                    st.success("Data uploaded and merged successfully!")
                    st.rerun()
                else:
                    st.error("Failed to save merged data.")
            else:
                st.error(msg)

# --- Main Content ---

if st.session_state.view == "Dashboard":


    # Custom styling for Cards
    st.markdown("""
    <style>
        .dash-card {
            background-color: #262730; /* Dark card background */
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
            position: relative;
            overflow: hidden;
            height: 140px;
            border: 1px solid #3f3f46;
        }
        .dash-card::before {
            content: "";
            position: absolute;
            top: -20px;
            right: -20px;
            width: 80px;
            height: 80px;
            border-radius: 50%;
            opacity: 0.1; /* Lower opacity for dark mode */
        }
        .card-blue::before { background-color: #60a5fa; }
        .card-green::before { background-color: #34d399; }
        .card-yellow::before { background-color: #fbbf24; }
        .card-red::before { background-color: #f87171; }
        
        .card-label { font-size: 0.8rem; font-weight: bold; text-transform: uppercase; margin-bottom: 5px; display: flex; align-items: center; gap: 5px; color: #e5e7eb; }
        .card-value { font-size: 2.5rem; font-weight: 800; color: #f9fafb; line-height: 1; }
        .card-sub { font-size: 0.8rem; color: #9ca3af; margin-top: 5px; }
        
        /* Status Badge CSS (Modern Pastel) */
        .status-badge {
            padding: 4px 12px;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 700; /* Bold */
            display: inline-block;
            margin-bottom: 2px;
            border: 1px solid transparent; /* No border needed for pastel usually */
        }
        /* Pastel Colors */
        .bg-green { background-color: #E6F4EA; color: #137333; } /* On Track */
        .bg-yellow { background-color: #FEF7E0; color: #B06000; } /* At Risk - Darker Orange text for contrast */
        .bg-red { background-color: #FCE8E6; color: #C5221F; } /* Critical */
        .bg-grey { background-color: #F3F4F6; color: #4B5563; } /* Pending */
        
        .plan-date { font-size: 0.7rem; color: #6b7280; margin-top: 2px; display: block; }
        
        /* Table Border Styling for Gateway Status */
        .gateway-table-cell {
            border: 1px solid #f3f4f6; /* Very subtle border */
            padding: 8px;
            text-align: center;
            background-color: #ffffff; 
            color: #1f2937;
            border-radius: 4px; /* Soft edges */
        }
        .gateway-table-header {
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 8px;
            font-weight: bold;
            color: #111827; 
            text-transform: uppercase;
            font-size: 0.85rem;
            letter-spacing: 0.05em;
            text-align: center;
        }
        
        /* Vibrant AI Expander Styling */
        div[data-testid="stExpander"] details summary p {
            font-size: 1.2rem;
            font-weight: 700;
            color: #4f46e5; /* Indigo */
        }
        
    </style>
    """, unsafe_allow_html=True)
    
    # Calculate Stats
    stats = utils.calculate_dashboard_stats(filtered_projects)
    # Calculate Adherence Rate (Gateways On Track / Total Released Gateways)
    # User Request: Denominator = Total Gateways released. Numerator = Gateways released on track.
    
    total_released_gateways = 0
    on_track_gateways = 0
    
    for p in filtered_projects:
        if 'modules' in p:
            for m in p['modules']:
                for gw in ['D0','D1','D2','D3','D4']:
                    # Use Project Plan for comparison (Consistent with Detailed View Status)
                    p_date = p['gateways'].get(gw, {}).get('p')
                    # Module Actual
                    a_date = m['gateways'].get(gw, {}).get('a')
                    
                    if a_date:
                        total_released_gateways += 1
                        # Numerator: Released on or before plan date.
                        # Strictly requires Plan Date to exist and Actual <= Plan.
                        if p_date and a_date <= p_date:
                            on_track_gateways += 1
                        
    # Avoid Divide by Zero
    if total_released_gateways > 0:
        adherence_rate = (on_track_gateways / total_released_gateways * 100)
    else:
        adherence_rate = 0

    # --- Top Header (Title + Controls) ---
    head_c1, head_c2 = st.columns([0.7, 0.3])
    
    with head_c1:
        st.title("Dashboard Overview")
        st.caption("Real-time status of all active programs")
        
    with head_c2:
        # Controls Stacked Vertically
        # Filter
        valid_defaults = [t for t in st.session_state.selected_types if t in all_types]
        new_selection = st.multiselect("Filter Project Type", all_types, default=valid_defaults, key="dash_filter_types", label_visibility="collapsed", placeholder="Select Filters...")
        if new_selection != st.session_state.selected_types:
            st.session_state.selected_types = new_selection
            st.rerun()

        # Download Button
        excel_data = utils.projects_to_excel(filtered_projects)
        file_name_date = datetime.now().strftime("%d-%m-%Y")
        st.download_button(
             label="📥 Download Report",
             data=excel_data,
             file_name=f"Project_Status_{file_name_date}.xlsx",
             mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
             key="dash_download_xlsx",
             use_container_width=True
        )

    # --- AI Assistant (Collapsed by Default) ---
    with st.expander("✨ AI Status Report Generator", expanded=False):
        st.info("Select a project below to generate an executive summary based on real-time data.")
        
        ai_c1, ai_c2 = st.columns([1, 1])
        with ai_c1:
            ai_proj_names = [p['name'] for p in projects]
            selected_ai_proj = st.selectbox("Select Project for AI Report", ai_proj_names, key="dash_ai_proj_sel")
        
        with ai_c2:
            st.write("") # Spacer
            st.write("")
            gen_btn = st.button("Generate Report", key="dash_gen_ai_btn", type="primary")
            
        if gen_btn:
            # Find Project
            proj_data = next((p for p in projects if p['name'] == selected_ai_proj), None)
            
            if proj_data:
                with st.spinner("Analyzing project data..."):
                    # 1. Gather Status Data
                    readiness_score, _ = utils.calculate_project_readiness(proj_data['id'])
                    status_info = {
                        "type": proj_data.get('type', 'Unknown'),
                        "readiness": int(readiness_score)
                    }
                    
                    # 2. Gather Delays
                    delay_list = []
                    if 'modules' in proj_data:
                        for m in proj_data['modules']:
                            for gw in ['D0','D1','D2','D3','D4']:
                                p_d = proj_data['gateways'].get(gw, {}).get('p')
                                a_d = m['gateways'].get(gw, {}).get('a')
                                if p_d and a_d:
                                    try:
                                        pd_dt = datetime.strptime(p_d, "%Y-%m-%d")
                                        ad_dt = datetime.strptime(a_d, "%Y-%m-%d")
                                        days = (ad_dt - pd_dt).days
                                        if days > 0:
                                            delay_list.append({
                                                "module": m['name'],
                                                "gateway": gw,
                                                "days": days
                                            })
                                    except: pass
                    
                    # 3. Call AI Engine
                    ai_summary = utils_ai.generate_project_summary(selected_ai_proj, status_info, delay_list)
                    
                    # 4. Display Result
                    st.markdown("#### 📝 Executive Summary")
                    st.text_area("Copy this text:", value=ai_summary, height=200)
                    st.success("Report Generated!")
            else:
                st.error("Project data not found.")

    # 1. Overview Cards
    st.markdown("### 🚀 Project Health Overview")
    
    # Adjusted columns for Gauge
    k1, k2, k3, k4, k5 = st.columns([1, 1, 1, 1, 2])
    
    with k1:
        st.markdown(f"""
        <div class="dash-card">
            <div class="card-label">TOTAL PROJECTS</div>
            <div class="card-value">{stats['total']}</div>
            <div class="card-sub">{stats['active']} Active</div>
        </div>
        """, unsafe_allow_html=True)
        
    with k2:
        st.markdown(f"""
        <div class="dash-card card-green">
            <div class="card-label" style="color: #10b981;">● ON TRACK</div>
            <div class="card-value">{stats['green']}</div>
            <div class="card-sub">No Delays</div>
        </div>
        """, unsafe_allow_html=True)

    with k3:
        st.markdown(f"""
        <div class="dash-card card-yellow">
            <div class="card-label" style="color: #f59e0b;">● AT RISK</div>
            <div class="card-value">{stats['yellow']}</div>
            <div class="card-sub">1-30 Days Delay</div>
        </div>
        """, unsafe_allow_html=True)
        
    with k4:
        # Changed CRITICAL to DELAY
        st.markdown(f"""
        <div class="dash-card card-red">
            <div class="card-label" style="color: #ef4444;">● DELAY</div>
            <div class="card-value">{stats['red']}</div>
            <div class="card-sub">> 30 Days Delay</div>
        </div>
        """, unsafe_allow_html=True)

    with k5:
        # Gauge Chart
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = adherence_rate,
            title = {'text': "Module Adherence %", 'font': {'size': 14}}, # Title inside chart
            gauge = {
                'axis': {'range': [None, 100]},
                'bar': {'color': "#3b82f6"},
                'steps': [
                    {'range': [0, 50], 'color': "#7f1d1d"}, # Dark Red
                    {'range': [50, 80], 'color': "#78350f"}, # Dark Yellow
                    {'range': [80, 100], 'color': "#064e3b"}], # Dark Green
                'threshold': {
                    'line': {'color': "#fca5a5", 'width': 4},
                    'thickness': 0.75,
                    'value': 90}}))
        # Zero margins to fit inside the "tile" height and align with CSS cards
        # Increased height slightly to 160 to fill the space better if needed, or stick to 140
        # CSS cards are 140px. Let's maximize chart usage. 
        # t=30 is needed for title.
        # Updated bgcolor to match dark card, font white for contrast
        fig_gauge.update_layout(height=150, margin=dict(l=20,r=20,t=40,b=20), paper_bgcolor="#262730", font={'color': "white"})
        st.plotly_chart(fig_gauge, use_container_width=True)
        st.caption(f"Metrics: {on_track_gateways} On Track Gws / {total_released_gateways} Total Gateways Released")


    # --- CSS for Table Layout ---
    st.markdown("""
    <style>
        .gateway-table-cell {
            padding: 8px;
            text-align: center;
            background-color: #ffffff; 
            color: #1f2937;
            border-radius: 0px; 
            margin-bottom: 5px;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
        }
        .gateway-table-header {
            font-weight: bold;
            color: #111827; 
            text-transform: uppercase;
            font-size: 0.8rem;
            letter-spacing: 0.05em;
            text-align: center;
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 8px;
            margin-bottom: 10px;
            /* Vertical Grid Line for Header */
            border-right: 1px solid #e5e7eb;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        /* Row Item Styling equivalent to cell for non-badge items */
        .row-item {
            text-align: center;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            border-right: 1px solid #e5e7eb; /* Vertical Grid Line */
            padding: 0 5px;
        }
        
        .row-container {
             background-color: white; 
             border-bottom: 1px solid #f3f4f6; 
             padding-top: 10px; 
             padding-bottom: 10px;
        }

        /* Inline Stacked Bar */
        .stacked-bar-container {
            width: 100%;
            height: 16px;
            background-color: #e5e7eb;
            border-radius: 8px;
            overflow: hidden;
            display: flex;
            margin-top: 4px;
        }
        .bar-seg { height: 100%; }
        .bar-green { background-color: #10b981; }
        .bar-yellow { background-color: #f59e0b; }
        .bar-red { background-color: #ef4444; }
    </style>
    """, unsafe_allow_html=True)
    
    # --- Custom Table Header ---
    st.subheader("Project Gateway Status")
    
    # 9 Columns: Project, Type, Readiness, Modules(Graph), D0, D1, D2, D3, D4
    cols = st.columns([1.5, 0.8, 1, 2.5, 1, 1, 1, 1, 1])
    headers = ["PROJECT", "TYPE", "DELIVERABLES", "MODULES RELEASED", "D0", "D1", "D2", "D3", "D4"]
    for i, h in enumerate(headers):
        # Last column needs no right border if we want to be strict, but consistent border is fine
        border_style = "" if i == len(headers)-1 else ""
        cols[i].markdown(f"<div class='gateway-table-header' style='{border_style}'>{h}</div>", unsafe_allow_html=True)
        
    st.write("") # Spacer
    
    for p in filtered_projects:
        # Layout
        r_cols = st.columns([1.5, 0.8, 1, 2.5, 1, 1, 1, 1, 1])
        
        # 1. Project Name
        r_cols[0].markdown(f"<div class='row-item'><b>{p['name']}</b></div>", unsafe_allow_html=True)
        
        # 2. Type
        r_cols[1].markdown(f"<div class='row-item'><span style='padding:2px 8px; border-radius:4px; font-size:0.8em; border: 1px solid #3f3f46; color: #9ca3af;'>{p['type']}</span></div>", unsafe_allow_html=True)
        
        # 3. Readiness (Text Color Coded)
        if p['type'] == 'Carryover':
            r_score = 100
        else:
            score_val, _ = utils.calculate_project_readiness(p['id'])
            r_score = int(score_val)
            
        r_color = "#10b981"
        if r_score < 75: r_color = "#ef4444"
        elif r_score < 90: r_color = "#f59e0b"
        
        r_cols[2].markdown(f"<div class='row-item'><span style='color: {r_color}; font-weight: bold;'>{r_score}%</span></div>", unsafe_allow_html=True)
        
        # 4. Modules Released (Inline Stacked Bar)
        # Calculate status counts
        c_green = 0
        c_yellow = 0
        c_red = 0
        total_m = 0
        
        if 'modules' in p:
            for m in p['modules']:
                 # Check each gateway for this module
                 for gw in ['D0','D1','D2','D3','D4']:
                     p_d = p['gateways'].get(gw, {}).get('p')
                     a_d = m['gateways'].get(gw, {}).get('a')
                     
                     if p_d and a_d:
                         total_m += 1 # Count this gateway event
                         
                         try:
                             pd_dt = datetime.strptime(p_d, "%Y-%m-%d")
                             ad_dt = datetime.strptime(a_d, "%Y-%m-%d")
                             delay_days = (ad_dt - pd_dt).days
                             
                             if delay_days <= 0:
                                 c_green += 1
                             elif delay_days <= 30:
                                 c_yellow += 1
                             else:
                                 c_red += 1
                         except:
                             pass
        
        # Generate Bar HTML
        if total_m > 0:
            pct_g = (c_green / total_m) * 100
            pct_y = (c_yellow / total_m) * 100
            pct_r = (c_red / total_m) * 100
            
            bar_html = f"""
            <div class='row-item' style='flex-direction:column; padding: 5px 10px;'>
                <div style="width: 100%; display:flex; justify-content:space-between; font-size:0.75rem; margin-bottom:2px; font-weight:bold;">
                    <span style="color:#ef4444;">{c_red} Delay</span>
                    <span style="color:#f59e0b;">{c_yellow} Risk</span>
                    <span style="color:#10b981;">{c_green} OnTrack</span>
                </div>
                <div class="stacked-bar-container">
                    <div class="bar-seg bar-red" style="width: {pct_r}%;"></div>
                    <div class="bar-seg bar-yellow" style="width: {pct_y}%;"></div>
                    <div class="bar-seg bar-green" style="width: {pct_g}%;"></div>
                </div>
            </div>
            """
            r_cols[3].markdown(bar_html, unsafe_allow_html=True)
        else:
            r_cols[3].markdown("<div class='row-item'><span style='color:#9ca3af; font-size:0.8em;'>No Releases</span></div>", unsafe_allow_html=True)

        # 5-9. Gateways (Badges with Plan)
        gws = ['D0', 'D1', 'D2', 'D3', 'D4']
        for i, gw in enumerate(gws):
            plan = p['gateways'].get(gw, {}).get('p')
            actual = p['gateways'].get(gw, {}).get('a')
            
            status = "grey"
            if actual:
                status = utils.get_status(plan, actual)
            
            def fmt(d):
                if not d: return "Pending"
                try: return datetime.strptime(d, "%Y-%m-%d").strftime("%b-%y")
                except: return d
            
            badge_txt = fmt(actual) if actual else "Pending"
            plan_txt = f"Plan: {fmt(plan)}" if plan else ""
            
            bg_class = f"bg-{status}"
            
            # Use 'gateway-table-cell' for the grid look on date cols
            html = f"""
            <div class="gateway-table-cell">
                <span class="status-badge {bg_class}">{badge_txt}</span>
                <span class="plan-date">{plan_txt}</span>
            </div>
            """
            r_cols[4+i].markdown(html, unsafe_allow_html=True)
            
        st.markdown("<div style='border-bottom: 1px solid #f3f4f6; margin-top: 0px; margin-bottom: 0px;'></div>", unsafe_allow_html=True)

    # --- Gantt Chart Integration ---
    st.markdown("### Project Gantt Chart")
    
    gantt_rows = []
    milestone_data = [] # Store milestones: Task, Date, Label, Color
    task_order = []  # To enforce Y-axis ordering (Project -> Modules -> Next Project)

    for p in filtered_projects:
        # Project Label
        p_label = f"🅿️ {p['name']}"
        task_order.append(p_label)

        # Project Plan Range (D0 to D4)
        if p['gateways'].get('D0', {}).get('p') and p['gateways'].get('D4', {}).get('p'):
             gantt_rows.append({
                "Task": p_label,
                "Start": p['gateways']['D0']['p'],
                "Finish": p['gateways']['D4']['p'],
                "Resource": "Plan",
                "Description": f"Type: {p.get('type')}"
            })
             # Collect Milestones
             for gw in ['D0', 'D1', 'D2', 'D3', 'D4']:
                 d = p['gateways'].get(gw, {}).get('p')
                 if d:
                     milestone_data.append({
                         "Task": p_label, "Date": d, "Gateway": gw, "Type": "Plan", "Color": "#1e3a8a" # darker blue
                     })
             
        # Module Actuals
        if 'modules' in p:
            for m in p['modules']:
                unique_suffix = "\u200B" * (p['id'] % 100) 
                m_display = f"   └─ {m['name']}{unique_suffix}"
                task_order.append(m_display)
                # Segmented Actuals Logic
                # Use pairs of gateways (Start -> End)
                gws_ordered = ['D0', 'D1', 'D2', 'D3', 'D4']
                
                # Get all actual dates for this module
                m_acts = {}
                for gw in gws_ordered:
                    val = m['gateways'].get(gw, {}).get('a')
                    if val: m_acts[gw] = val

                # Iterate pairs
                for i in range(len(gws_ordered) - 1):
                    start_gw = gws_ordered[i]
                    end_gw = gws_ordered[i+1]
                    
                    if start_gw in m_acts and end_gw in m_acts:
                         s_date = m_acts[start_gw]
                         e_date = m_acts[end_gw]
                         p_target = p['gateways'].get(end_gw, {}).get('p')
                         status = utils.get_status(p_target, e_date)
                         
                         color = "#1e3a8a" # Default Blue
                         if status == 'yellow': color = "#d97706" # Amber
                         elif status == 'red': color = "#b91c1c" # Red
                         
                         # Add Segment Bar
                         gantt_rows.append({
                            "Task": m_display,
                            "Start": s_date,
                            "Finish": e_date,
                            "Resource": "Actual (On Track)" if color == "#1e3a8a" else ("Actual (At Risk)" if color == "#d97706" else "Actual (Delay)"),
                            "Description": f"{start_gw} -> {end_gw}",
                            "Color": color
                         })
                         
                # Collect Milestones
                for gw in ['D0', 'D1', 'D2', 'D3', 'D4']:
                    d = m['gateways'].get(gw, {}).get('a')
                    if d:
                        milestone_data.append({
                            "Task": m_display, "Date": d, "Gateway": gw, "Type": "Actual", "Color": "#5b21b6" # darker purple
                        })

    # Render Chart
    if gantt_rows:
        df_gantt = pd.DataFrame(gantt_rows)
        
        fig_gantt = px.timeline(df_gantt, x_start="Start", x_end="Finish", y="Task", color="Resource", 
                                color_discrete_map={
                                    "Plan": "#93c5fd", # Light Blue
                                    "Actual (On Track)": "#10b981", # Green
                                    "Actual (At Risk)": "#f59e0b", # Amber
                                    "Actual (Delay)": "#ff0000" # Bright Red
                                },
                                category_orders={"Task": task_order},
                                hover_data=["Description"])
        
        # Add Milestones (Scatter)
        if milestone_data:
            df_ms = pd.DataFrame(milestone_data)
            # Add trace for Plan Milestones
            ms_plan = df_ms[df_ms['Type'] == 'Plan']
            if not ms_plan.empty:
                fig_gantt.add_trace(go.Scatter(
                    x=ms_plan['Date'], y=ms_plan['Task'], mode='markers+text',
                    name='Plan Gateway', text=ms_plan['Gateway'],
                    textposition="middle center", textfont=dict(color='white'),
                    marker=dict(symbol='diamond', size=28, color='#2563eb', line=dict(color='white', width=1)),
                    hoverinfo='text', hovertext=ms_plan.apply(lambda r: f"{r['Gateway']}: {r['Date']}", axis=1)
                ))
            
            # Add trace for Actual Milestones
            ms_act = df_ms[df_ms['Type'] == 'Actual']
            if not ms_act.empty:
                fig_gantt.add_trace(go.Scatter(
                    x=ms_act['Date'], y=ms_act['Task'], mode='markers+text',
                    name='Actual Gateway', text=ms_act['Gateway'],
                    textposition="middle center", textfont=dict(color='white'),
                    marker=dict(symbol='diamond', size=28, color='#7c3aed', line=dict(color='white', width=1)),
                    hoverinfo='text', hovertext=ms_act.apply(lambda r: f"{r['Gateway']}: {r['Date']}", axis=1)
                ))

        # Enforce the custom order on Y-axis
        fig_gantt.update_layout(yaxis={'categoryorder':'array', 'categoryarray': task_order})
        fig_gantt.update_yaxes(autorange="reversed") 
        fig_gantt.update_layout(
            height=600 + (len(projects) * 30), # Dynamic Height
            xaxis=dict(
                title="Timeline",
                showgrid=True,
                gridwidth=1,
                gridcolor='#666666', 
                griddash='dot', 
                dtick="M1", 
                tickformat="%b %Y",
                tickangle=-45
            ),
            plot_bgcolor="white"
        )
        
        st.plotly_chart(fig_gantt, use_container_width=True)
    else:
        st.info("No timeline data available.")

elif st.session_state.view == "Detailed Project View":
    # --- Header (Title + Inline Actions) ---
    ph1, ph2 = st.columns([3, 1])
    with ph1:
        st.title("Project Details")
    with ph2:
        # Actions Stacked
        if st.button("➕ Create New Project", use_container_width=True):
             modal_create_project()
        if st.button("📂 Upload Bulk Data", use_container_width=True):
             modal_upload_csv()



        

    



    
    st.divider()

    st.divider()

    # --- Header Row (Matches Image) ---
    h1, h2, h3, h4, h5, h6, h7 = st.columns([2, 0.8, 1, 1, 1, 1, 1])
    h1.markdown("**COMPONENT NAME**")
    h2.markdown("**TYPE**")
    h3.markdown("**D0 (CONCEPT)**")
    h4.markdown("**D1 (PROTO)**")
    h5.markdown("**D2 (PILOT)**")
    h6.markdown("**D3 (LAUNCH)**")
    h7.markdown("**D4 (CLOSE)**")
    st.divider()

    # --- Project Rows (Tree Structure) ---
    # Helper for Dates
    def parse_date(d_str):
        if not d_str: return None
        try: return datetime.strptime(d_str, "%Y-%m-%d").date()
        except: return None

    for p in filtered_projects:
        # Project level expander (Mockup shows Project A with dropdown caret)
        with st.expander(f"**{p['name']}**", expanded=True):
            
            # --- Project Level Inputs (Row 1) ---
            pc1, pc2, pc3, pc4, pc5, pc6, pc7 = st.columns([2, 0.8, 1, 1, 1, 1, 1])
            
            # Project Name + Actions
            with pc1:
                # Flattened nesting: [Name | Add | Del]
                pnc1, pnc2, pnc3 = st.columns([3, 2, 0.6])
                with pnc1:
                    st.markdown(f"<h2 style='color:#4f46e5; margin:0; padding:0;'>{p['name']}</h2>", unsafe_allow_html=True)
                with pnc2:
                    st.write("") 
                    if st.button("➕ Add Modules", key=f"add_mod_top_{p['id']}", type="primary", use_container_width=True):
                        if 'modules' not in p: p['modules'] = []
                        new_mod_id = int(datetime.now().timestamp() * 1000)
                        defaults = { "p": "", "a": "", "ecn": "" }
                        p['modules'].append({
                            "id": new_mod_id, "name": "New Module",
                            "gateways": { "D0": defaults.copy(), "D1": defaults.copy(), "D2": defaults.copy(), "D3": defaults.copy(), "D4": defaults.copy() }
                        })
                        utils.save_data(projects)
                        st.rerun()
                with pnc3:
                    st.write("")
                    if st.button("🗑️", key=f"del_proj_{p['id']}", help="Delete Project"): # Project Delete
                        projects.remove(p)
                        utils.save_data(projects)
                        st.rerun()


            # Type Dropdown
            with pc2:
                curr_type = p.get('type')
                new_type_sel = st.selectbox("Type", ["Major", "Minor", "Carryover"], index=["Major", "Minor", "Carryover"].index(curr_type) if curr_type in ["Major", "Minor", "Carryover"] else 0, key=f"p_type_{p['id']}", label_visibility="collapsed")
                if new_type_sel != curr_type:
                    p['type'] = new_type_sel
                    utils.save_data(projects)
            
            # Plan Dates
            gw_cols = [pc3, pc4, pc5, pc6, pc7]
            gws = ['D0', 'D1', 'D2', 'D3', 'D4']
            
            # Helper for status colors
            s_cols_hex = { "green": "#10b981", "yellow": "#f59e0b", "red": "#ef4444", "grey": "#e5e7eb" }

            for i, gw in enumerate(gws):
                curr_p = p['gateways'][gw].get('p')
                pd_val = parse_date(curr_p)
                
                with gw_cols[i]:
                    # 1. Plan Input
                    new_pd = st.date_input("Plan", value=pd_val, key=f"pp_{p['id']}_{gw}", label_visibility="collapsed")
                    if str(new_pd) != curr_p and new_pd:
                        p['gateways'][gw]['p'] = str(new_pd)
                        utils.save_data(projects)
                    
                    st.write("") # Spacer

                    # 2. Project Actual Calculation (Rollup)
                    # Iterate modules to find max actual date for this gateway
                    proj_a_str = ""
                    if 'modules' in p and p['modules']:
                        m_dates = []
                        for m in p['modules']:
                            # Ensure we use the latest specific entry from module
                            ma = m['gateways'].get(gw, {}).get('a')
                            if ma:
                                try: m_dates.append(datetime.strptime(ma, "%Y-%m-%d").date())
                                except: pass
                        if m_dates:
                            proj_a_str = str(max(m_dates))
                    
                    # Update Project Data if changed
                    if p['gateways'][gw].get('a') != proj_a_str:
                        p['gateways'][gw]['a'] = proj_a_str
                        utils.save_data(projects)
                    
                    # 3. Project Actual Card (Render)
                    # Status based on Project Plan vs Project Actual
                    proj_status = utils.get_status(curr_p, proj_a_str) if curr_p else "grey"
                    if not proj_a_str: proj_status = "grey" # Default if no actuals yet

                    p_curr_col = s_cols_hex.get(proj_status, "#e5e7eb")
                    
                    # Interactive Card (Read Only primarily, but shows date)
                    with st.container(border=True):
                         # Top Color Bar
                         st.markdown(f"<div style='height: 5px; background-color: {p_curr_col}; margin: -15px -15px 10px -15px; border-radius: 4px 4px 0 0;'></div>", unsafe_allow_html=True)
                         
                         # Label
                         st.markdown(f"<div style='font-size:0.75em; font-weight:800; color:{p_curr_col if proj_status != 'grey' else '#6b7280'};'>ACT (Proj)</div>", unsafe_allow_html=True)
                         
                         # Date Display (Disabled/Read-Only logic)
                         pa_val = parse_date(proj_a_str)
                         st.date_input("Act", value=pa_val, key=f"p_act_{p['id']}_{gw}", label_visibility="collapsed", disabled=True)

            st.write("") 

            # --- Module Rows ---
            if 'modules' in p:
                for m_idx, m in enumerate(p['modules']):
                    mc1, mc2, mc3, mc4, mc5, mc6, mc7 = st.columns([2, 0.8, 1, 1, 1, 1, 1])
                    
                    with mc1: # Name + Sub Button
                        st.markdown(f"<div style='font-weight:600; color:#1e3a8a; margin-left: 10px; margin-top:20px;'>↳ {m['name']}</div>", unsafe_allow_html=True)
                        if st.button("➕ Sub", key=f"add_sub_btn_{m['id']}", help="Add Sub-module"):
                            if 'sub_modules' not in m: m['sub_modules'] = []
                            new_sub_id = int(datetime.now().timestamp() * 1000)
                            defaults = { "p": "", "a": "", "ecn": "" }
                            m['sub_modules'].append({
                                "id": new_sub_id, "name": "New Part",
                                "gateways": { "D0": defaults.copy(), "D1": defaults.copy(), "D2": defaults.copy(), "D3": defaults.copy(), "D4": defaults.copy() }
                            })
                            utils.save_data(projects)
                            st.rerun()
                    
                    with mc2: # Module Delete
                        st.write("")
                        st.write("")
                        if st.button("🗑️", key=f"del_mod_{m['id']}", help="Delete Module"):
                            p['modules'].pop(m_idx)
                            utils.save_data(projects)
                            st.rerun()

                    # Gateways
                    mod_cols = [mc3, mc4, mc5, mc6, mc7]
                    has_subs = bool(m.get('sub_modules'))
                    
                    for i, gw in enumerate(gws):
                        gw_data = m['gateways'].get(gw, {})
                        p_date = p['gateways'].get(gw, {}).get('p')
                        a_date = gw_data.get('a')
                        
                        # Rollup Logic
                        if has_subs:
                            sub_dates = []
                            for s in m['sub_modules']:
                                s_a = s['gateways'].get(gw, {}).get('a')
                                if s_a:
                                    try: sub_dates.append(datetime.strptime(s_a, "%Y-%m-%d").date())
                                    except: pass
                            if sub_dates:
                                max_date = max(sub_dates)
                                a_date = str(max_date)
                                if m['gateways'][gw].get('a') != a_date:
                                    m['gateways'][gw]['a'] = a_date
                                    utils.save_data(projects)
                        
                        status = utils.get_status(p_date, a_date)
                        
                        # Status Colors definition
                        s_cols_hex = { "green": "#10b981", "yellow": "#f59e0b", "red": "#ef4444", "grey": "#e5e7eb" }
                        curr_col = s_cols_hex.get(status, "#e5e7eb")

                        with mod_cols[i]:
                            # Container with Custom Status Bar
                            with st.container(border=True):
                                # Top Color Bar
                                st.markdown(f"<div style='height: 5px; background-color: {curr_col}; margin: -15px -15px 10px -15px; border-radius: 4px 4px 0 0;'></div>", unsafe_allow_html=True)
                                
                                # Label
                                st.markdown(f"<div style='font-size:0.75em; font-weight:800; color: {curr_col if status != 'grey' else '#6b7280'};'>ACT (Mod)</div>", unsafe_allow_html=True)
                                
                                act_val = parse_date(a_date)
                                new_act = st.date_input("Act", value=act_val, key=f"m_{m['id']}_{gw}_a", label_visibility="collapsed", disabled=has_subs)
                                if not has_subs:
                                    if str(new_act) != str(a_date) if a_date else (new_act is not None):
                                        m['gateways'][gw]['a'] = str(new_act) if new_act else ""
                                        utils.save_data(projects)
                                
                                st.markdown(f"<div style='font-size:0.7em; font-weight:bold; margin-top:4px;'>ECN</div>", unsafe_allow_html=True)
                                ecn_val = gw_data.get('ecn', "")
                                new_ecn = st.text_input("ECN", value=ecn_val, key=f"m_{m['id']}_{gw}_ecn", label_visibility="collapsed")
                                if new_ecn != ecn_val:
                                    m['gateways'][gw]['ecn'] = new_ecn
                                    utils.save_data(projects)

                    # Sub-modules
                    if has_subs:
                        for s_idx, s in enumerate(m['sub_modules']):
                            sc1, sc2, sc3, sc4, sc5, sc6, sc7 = st.columns([2, 0.8, 1, 1, 1, 1, 1])
                            with sc1:
                                st.markdown(f"<div style='color:#64748b; margin-left: 25px; font-size:0.9em;'>↳ {s['name']}</div>", unsafe_allow_html=True)
                                new_s_name = st.text_input("Edit", value=s['name'], key=f"s_name_{s['id']}", label_visibility="collapsed")
                                if new_s_name != s['name']:
                                    s['name'] = new_s_name
                                    utils.save_data(projects)
                            
                            with sc2: # Sub Delete
                                if st.button("🗑️", key=f"del_sub_{s['id']}"):
                                    m['sub_modules'].pop(s_idx)
                                    utils.save_data(projects)
                                    st.rerun()

                            sub_cols = [sc3, sc4, sc5, sc6, sc7]
                            for i, gw in enumerate(gws):
                                sgw_data = s['gateways'].get(gw, {})
                                p_date = p['gateways'].get(gw, {}).get('p')
                                sa_date = sgw_data.get('a')
                                s_status = utils.get_status(p_date, sa_date)
                                
                                with sub_cols[i]:
                                    s_curr_col = s_cols_hex.get(s_status, "#e5e7eb")
                                    with st.container(border=True):
                                         # Top Color Bar
                                         st.markdown(f"<div style='height: 5px; background-color: {s_curr_col}; margin: -15px -15px 10px -15px; border-radius: 4px 4px 0 0;'></div>", unsafe_allow_html=True)
                                         
                                         # Label
                                         st.markdown(f"<div style='font-size:0.7em; font-weight:800; color:{s_curr_col if s_status != 'grey' else '#6b7280'};'>ACT (Sub)</div>", unsafe_allow_html=True)
                                         
                                         s_act_val = parse_date(sa_date)
                                         s_new_act = st.date_input("Act", value=s_act_val, key=f"s_{s['id']}_{gw}_a", label_visibility="collapsed")
                                         if str(s_new_act) != str(sa_date) if sa_date else (s_new_act is not None):
                                             s['gateways'][gw]['a'] = str(s_new_act) if s_new_act else ""
                                             utils.save_data(projects)
                                             st.rerun()
                                         
                                         s_new_ecn = st.text_input("ECN", value=sgw_data.get('ecn', ""), key=f"s_{s['id']}_{gw}_ecn", label_visibility="collapsed")
                                         if s_new_ecn != sgw_data.get('ecn', ""):
                                             s['gateways'][gw]['ecn'] = s_new_ecn
                                             utils.save_data(projects)

    # Footer Removed (Merged into Header)





    # Legacy Loop Disabled
    if False:
        p = None
        # Filter applied via filtered_projects list
        
        with st.container(border=True):
            # Custom Header Row within Container
            row_head_1, row_head_2 = st.columns([0.95, 0.05])
            with row_head_1:
                 # Bigger Project Name
                 st.markdown(f"### {p['name']}")
            with row_head_2:
                 # Settings Icon Only
                 show_settings = st.checkbox("⚙️", key=f"show_set_{p['id']}", label_visibility="visible")
            
            # Settings Panel (Conditional Display)
            if show_settings:
                with st.container():
                    st.markdown("#### Project Settings")
                    ps_c1, ps_c2 = st.columns([3, 1])
                    with ps_c1:
                       new_p_name = st.text_input("Edit Project Name", value=p['name'], key=f"p_name_edit_{p['id']}")
                       if new_p_name != p['name']:
                           p['name'] = new_p_name
                           utils.save_data(projects)
                           st.rerun()
                    with ps_c2:
                        st.write("") # Spacer
                        st.write("") 
                        if st.button("🗑️ Delete Project", key=f"del_proj_{p['id']}", type="primary"):
                            projects.remove(p)
                            utils.save_data(projects)
                            st.rerun()
                st.divider()

            # Project Plan Data Row
            pc1, pc2, pc3, pc4, pc5, pc6, pc7 = st.columns([2, 1, 1, 1, 1, 1, 1])
            pc2.caption(p.get('type'))

            # Helper to safely parse date or return None
            def parse_date(d_str):
                if not d_str: return None
                try: return datetime.strptime(d_str, "%Y-%m-%d").date()
                except: return None
            
            # Project Gateways Inputs
            with pc3:
                curr_p = p['gateways']['D0'].get('p')
                new_d0 = st.date_input("Plan", value=parse_date(curr_p), key=f"p_{p['id']}_D0", label_visibility="collapsed")
                if str(new_d0) != curr_p and new_d0 is not None:
                     p['gateways']['D0']['p'] = str(new_d0)
                     utils.save_data(projects) # Auto-save (naive)

            with pc4:
                curr_p = p['gateways']['D1'].get('p')
                new_d1 = st.date_input("Plan", value=parse_date(curr_p), key=f"p_{p['id']}_D1", label_visibility="collapsed")
                if str(new_d1) != curr_p and new_d1 is not None:
                     p['gateways']['D1']['p'] = str(new_d1)
                     utils.save_data(projects)

            with pc5:
                curr_p = p['gateways']['D2'].get('p')
                new_d2 = st.date_input("Plan", value=parse_date(curr_p), key=f"p_{p['id']}_D2", label_visibility="collapsed")
                if str(new_d2) != curr_p and new_d2 is not None:
                     p['gateways']['D2']['p'] = str(new_d2)
                     utils.save_data(projects)

            with pc6:
                curr_p = p['gateways']['D3'].get('p')
                new_d3 = st.date_input("Plan", value=parse_date(curr_p), key=f"p_{p['id']}_D3", label_visibility="collapsed")
                if str(new_d3) != curr_p and new_d3 is not None:
                     p['gateways']['D3']['p'] = str(new_d3)
                     utils.save_data(projects)

            with pc7:
                curr_p = p['gateways']['D4'].get('p')
                new_d4 = st.date_input("Plan", value=parse_date(curr_p), key=f"p_{p['id']}_D4", label_visibility="collapsed")
                if str(new_d4) != curr_p and new_d4 is not None:
                     p['gateways']['D4']['p'] = str(new_d4)
                     utils.save_data(projects)
            
            
            st.markdown("---")

            st.markdown("---")
            
            # Modules
            if 'modules' in p:
                for m_idx, m in enumerate(p['modules']):
                    mc1, mc2, mc3, mc4, mc5, mc6, mc7 = st.columns([2, 1, 1, 1, 1, 1, 1])
                    
                    mac1, mac2 = mc1.columns([4, 1])
                    with mac1:
                        st.write("") # Spacer
                        st.caption("Module")
                        new_name = st.text_input("Name", value=m['name'], key=f"m_name_{m['id']}", label_visibility="collapsed")
                        if new_name != m['name']:
                            m['name'] = new_name
                            utils.save_data(projects)
                    
                    with mac2:
                        st.write("")
                        st.write("")
                        if st.button("🗑️", key=f"del_mod_{m['id']}"):
                            p['modules'].pop(m_idx)
                            utils.save_data(projects)
                            st.rerun()
                    
                    gw_cols = [mc3, mc4, mc5, mc6, mc7]
                    gws = ['D0', 'D1', 'D2', 'D3', 'D4']
                    
                    for i, gw in enumerate(gws):
                        col = gw_cols[i]
                        gw_data = m['gateways'].get(gw, {})
                        
                        gw_status = utils.get_status(p['gateways'].get(gw, {}).get('p'), gw_data.get('a'))
                        
                        # Use markdown for "Card" like feel or Status header
                        # Using emoji is cleanest, or color text
                        status_color_css = {
                            "green": "color: #10b981", 
                            "yellow": "color: #f59e0b", 
                            "red": "color: #f43f5e", 
                            "grey": "color: #94a3b8"
                        }
                        
                        with col:
                            with st.container(border=True):
                                st.markdown(f"<div style='font-size:0.8em; font-weight:bold; {status_color_css[gw_status]}'>{gw} Status</div>", unsafe_allow_html=True)
                                
                                has_subs = bool(m.get('sub_modules'))
                                
                                act_val = parse_date(gw_data.get('a'))
                                st.caption("ACT")
                                new_act = st.date_input("Act", value=act_val, key=f"m_{m['id']}_{gw}_a", label_visibility="collapsed", disabled=has_subs)
                                
                                if has_subs:
                                    # Show info tooltip or just locked icon? 
                                    # Using disabled is enough
                                    pass
                                
                                ecn_val = gw_data.get('ecn', '')
                                st.caption("ECN")
                                new_ecn = st.text_input("ECN", value=ecn_val, placeholder="-", key=f"m_{m['id']}_{gw}_ecn", label_visibility="collapsed")
                                
                                # Update Logic
                                # Allow clearing: if new_act is None, we save empty string
                                if not has_subs:
                                    if new_act != act_val:
                                        clean_new = str(new_act) if new_act else ""
                                        gw_data['a'] = clean_new
                                        utils.save_data(projects)
                                
                                # Note: if has_subs is True, the input is disabled, so user can't change it.
                                # The rollup logic in utils.py will overwrite it anyway on save.
                                        
                                if new_ecn != ecn_val:
                                    gw_data['ecn'] = new_ecn
                                    utils.save_data(projects)
                                    
                            if new_ecn != ecn_val:
                                gw_data['ecn'] = new_ecn
                                utils.save_data(projects)
                                
                    # --- Sub-modules Logic ---
                    sub_mods = m.get('sub_modules', [])
                    for s_idx, s in enumerate(sub_mods):
                        sc1, sc2, sc3, sc4, sc5, sc6, sc7 = st.columns([2, 1, 1, 1, 1, 1, 1])
                        with sc1:
                            st.write("") 
                            st.caption("Sub-module")
                            # Visual indentation
                            c_name, c_del = st.columns([4, 1])
                            with c_name:
                                s_name = st.text_input("Name", value=s['name'], key=f"s_name_{s['id']}", label_visibility="collapsed")
                            with c_del:
                                if st.button("🗑️", key=f"del_s_{s['id']}"):
                                    m['sub_modules'].pop(s_idx)
                                    utils.save_data(projects)
                                    st.rerun()

                            st.markdown("<span style='color:grey; font-size:0.8em'>↳ Nested</span>", unsafe_allow_html=True)
                            
                            if s_name != s['name']:
                                s['name'] = s_name
                                utils.save_data(projects)

                        s_gw_cols = [sc3, sc4, sc5, sc6, sc7]
                        for i, gw in enumerate(gws):
                            col = s_gw_cols[i]
                            gw_data = s['gateways'].get(gw, {})
                            
                            # Inherit Project Plan for Status comparison (or should it be independent? Using Project plan for now)
                            gw_status = utils.get_status(p['gateways'].get(gw, {}).get('p'), gw_data.get('a'))
                            
                            with col:
                                with st.container(border=True):
                                    st.markdown(f"<div style='font-size:0.7em; color:grey'>{gw} (Sub)</div>", unsafe_allow_html=True)
                                    
                                    act_val = parse_date(gw_data.get('a'))
                                    new_act = st.date_input("Act", value=act_val, key=f"s_{s['id']}_{gw}_a", label_visibility="collapsed")
                                    
                                    ecn_val = gw_data.get('ecn', '')
                                    new_ecn = st.text_input("ECN", value=ecn_val, placeholder="-", key=f"s_{s['id']}_{gw}_ecn", label_visibility="collapsed")
                                    
                                    # Allow clearing date
                                    if new_act != act_val:
                                        clean_new = str(new_act) if new_act else ""
                                        gw_data['a'] = clean_new
                                        utils.save_data(projects)
                                            
                                    if new_ecn != ecn_val:
                                        gw_data['ecn'] = new_ecn
                                        utils.save_data(projects)
                        st.divider()

                    # Add Sub-module Button
                    if st.button(f"➕ Add Sub-module to {m['name']}", key=f"add_sub_{m['id']}"):
                        if 'sub_modules' not in m:
                            m['sub_modules'] = []
                        
                        defaults = { "p": "", "a": "", "ecn": "" }
                        new_sub_id = int(datetime.now().timestamp() * 1000) + 999 
                        m['sub_modules'].append({
                            "id": new_sub_id,
                            "name": "New Part",
                            "gateways": { "D0": defaults.copy(), "D1": defaults.copy(), "D2": defaults.copy(), "D3": defaults.copy(), "D4": defaults.copy() }
                        })
                        utils.save_data(projects)
                        st.rerun()

                    st.divider() 
            else:
                st.info("No modules added.")
                
            if st.button("➕ Add Module", key=f"add_mod_{p['id']}"):
                defaults = { "p": "", "a": "", "ecn": "" }
                new_mod_id = int(datetime.now().timestamp() * 1000)
                p['modules'].append({
                    "id": new_mod_id,
                    "name": "New Module",
                    "gateways": { "D0": defaults.copy(), "D1": defaults.copy(), "D2": defaults.copy(), "D3": defaults.copy(), "D4": defaults.copy() }
                })
                utils.save_data(projects)
                st.rerun()



elif st.session_state.view == "Deliverables Tracker":
    st.title("📋 Project Deliverables Checker")
    
    if not projects:
         st.info("No projects found.")
    else:
        # Selection
        project_names = [p['name'] for p in projects]
        # Use simple st.selectbox at top
        c_sel, _ = st.columns([1, 2])
        with c_sel:
            selected_p_name = st.selectbox("Select Project to Track", project_names, key="deliv_proj_sel")
        
        selected_project = next((p for p in projects if p['name'] == selected_p_name), None)

        if selected_project:
            # Header Row
            d_head_1, d_head_2 = st.columns([3, 1])
            with d_head_1:
                st.caption(f"Project Type: {selected_project.get('type')}")
            with d_head_2:
                # Reload Button
                if st.button("⟳ Reload Standard Deliverables", key=f"reload_deliv_{selected_project['id']}"):
                    # Logic: Clear and Reload
                    # 1. Clear existing
                    selected_project['deliverables'] = []
                    # 2. Reload from utils (which reads fresh CSV)
                    selected_project['deliverables'] = utils.populate_deliverables(selected_project['id'], selected_project.get('type'))
                    # 3. Save
                    if utils.save_data(projects):
                        st.success("Deliverables list has been reset to the latest standard.")
                        st.rerun()
                    else:
                        st.error("Failed to save reset data.")
            
            if 'deliverables' not in selected_project:
                selected_project['deliverables'] = []
            
            all_delivs = selected_project['deliverables']
            
            # --- Gateway Tiles Navigation ---
            if 'deliv_active_gw' not in st.session_state:
                st.session_state.deliv_active_gw = 'D0'

            st.markdown("###")
            cols = st.columns(5)
            gateways = {
                'D0': 'D0 Concept', 
                'D1': 'D1 Proto', 
                'D2': 'D2 Pilot', 
                'D3': 'D3 Launch', 
                'D4': 'D4 Close'
            }
            
            for i, (gw_key, gw_label) in enumerate(gateways.items()):
                # Highlight active button
                if st.session_state.deliv_active_gw == gw_key:
                    if cols[i].button(f"🔵 {gw_label}", key=f"btn_{gw_key}", use_container_width=True):
                        pass # Already active
                else:
                    if cols[i].button(gw_label, key=f"btn_{gw_key}", use_container_width=True):
                        st.session_state.deliv_active_gw = gw_key
                        st.rerun()
            
            active_gw = st.session_state.deliv_active_gw
            active_label = gateways[active_gw]
            
            # --- Main Content Card ---
            with st.container():
                st.markdown(f"#### Currently Viewing: {active_label} Deliverables")
                
                gw_delivs = [d for d in all_delivs if d.get('gateway_stage') == active_gw]
                
                if not gw_delivs:
                    st.info(f"No deliverables checklist for {active_gw}.")
                else:
                    # Progress
                    comp_count = len([d for d in gw_delivs if d['status'] == 'Completed' or d['status'] == 'NA'])
                    prog = comp_count / len(gw_delivs)
                    st.progress(prog, text=f"{int(prog*100)}% Completed")
                    
                    df = pd.DataFrame(gw_delivs)
                    
                    # CSS: Card Style + Big Table Fonts + Hide Toolbar
                    st.markdown("""
                    <style>
                    /* Increase Font Size for Data Editor */
                    div[data-testid="stDataEditor"] table {
                        font-size: 22px !important;
                    }
                    div[data-testid="stDataEditor"] td {
                        font-size: 22px !important;
                        height: 75px !important; /* Increased Height */
                        padding-top: 15px !important;
                        padding-bottom: 15px !important;
                    }
                    div[data-testid="stDataEditor"] th {
                        font-size: 22px !important;
                        height: 75px !important; /* Increased Height */
                    }
                    /* Attempts to target internal grid if table css fails */
                    div[class*="stDataFrame"] {
                        font-size: 22px !important;
                    }
                    /* Hide Streamlit Toolbar (Zoom/Fullscreen) on DataFrame/DataEditor */
                    div[data-testid="stElementToolbar"] {
                        display: none !important;
                    }
                    button[title="View fullscreen"] {
                        display: none !important;
                    }
                    </style>
                    """, unsafe_allow_html=True)
                    
                    # Status Mapping (Logic for Colors)
                    status_map = {
                        "Completed": "🟢 Completed",
                        "WIP": "🟡 WIP",
                        "Pending": "🔴 Pending",
                        "NA": "⚪ NA"
                    }
                    # Reverse map for saving
                    rev_status_map = {v: k for k, v in status_map.items()}
                    
                    # Apply mapping to DF for display
                    if 'status' in df.columns:
                        df['status'] = df['status'].map(lambda x: status_map.get(x, x))

                    # Container style wrapper
                    with st.container(border=True):
                        edit_df = st.data_editor(
                            df,
                            column_config={
                                "id": None,
                                "gateway_stage": None,
                                "deliverable_name": st.column_config.TextColumn("Deliverable", disabled=True, width="large"),
                                "status": st.column_config.SelectboxColumn(
                                    "Status", 
                                    options=["🔴 Pending", "🟡 WIP", "🟢 Completed", "⚪ NA"], 
                                    required=True, 
                                    width="medium"
                                ),
                                "evidence_link": st.column_config.TextColumn("Evidence Link", width="large"),
                                "remarks": st.column_config.TextColumn("Remarks", width="large")
                            },
                            hide_index=True,
                            use_container_width=True,
                            key=f"editor_{selected_project['id']}_{active_gw}"
                        )
                    
                        # Save Logic
                        has_changes = False
                        for index, row in edit_df.iterrows():
                            # Clean status back to plain text
                            clean_status = rev_status_map.get(row['status'], row['status'])
                            
                            orig = next((d for d in all_delivs if d['id'] == row['id']), None)
                            if orig:
                                if (orig['status'] != clean_status or orig['evidence_link'] != row['evidence_link'] or orig['remarks'] != row['remarks']):
                                    orig['status'] = clean_status
                                    orig['evidence_link'] = row['evidence_link']
                                    orig['remarks'] = row['remarks']
                                    has_changes = True
                        
                        if has_changes:
                            if utils.save_data(projects):
                                st.toast(f"Saved changes for {active_gw}!", icon="✅")
