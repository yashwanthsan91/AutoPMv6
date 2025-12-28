import datetime

# Placeholder for API Key
OPENAI_API_KEY = "sk-placeholder-key" 

def generate_project_summary(project_name, status_data, delay_list):
    """
    Generates a project summary using a Generative AI model (Simulated/Fallback).
    
    Args:
        project_name (str): Name of the project.
        status_data (dict): General status info (e.g., {'type': 'Major', 'readiness': 85}).
        delay_list (list): List of delayed items (e.g., [{'module': 'Mod1', 'gateway': 'D2', 'days': 45}]).
        
    Returns:
        str: A 3-bullet executive summary.
    """
    
    # 1. Prompt Construction (for reference/future use)
    prompt = f"""
    Act as a Senior Automotive Program Manager. Review this data for Project '{project_name}':
    Type: {status_data.get('type')}
    Readiness: {status_data.get('readiness')}%
    
    Delays:
    {delay_list}
    
    Write a 3-bullet executive summary focusing on risks and timeline recovery. 
    Keep it professional and concise.
    """
    
    # 2. Simulated API Call / Fallback Logic
    # In a real scenario, we would call client.chat.completions.create(...) here.
    # Since we strictly use local execution:
    
    try:
        # Check for API Key (Simulation)
        if not OPENAI_API_KEY or "placeholder" in OPENAI_API_KEY:
            raise ValueError("No valid API Key found.")
            
        # ... API call logic would go here ...
        response_text = "AI Generated Response..."
        
    except Exception as e:
        # 3. Rule-Based Fallback
        # Analyze delays
        critical_delays = [d for d in delay_list if d['days'] > 30]
        minor_delays = [d for d in delay_list if d['days'] <= 30]
        
        status_str = "On Track"
        if critical_delays:
            status_str = "Critical Delay"
        elif minor_delays:
            status_str = "At Risk"
            
        if critical_delays:
            top_delay = critical_delays[0]
            risk_desc = f"Major risk identified in **{top_delay['module']}** ({top_delay['gateway']}), currently delayed by {top_delay['days']} days. Immediate recovery planning is required."
        elif minor_delays:
             top_delay = minor_delays[0]
             risk_desc = f"A minor deviation is noted in **{top_delay['module']}** ({top_delay['gateway']}), showing a slip of {top_delay['days']} days. Monitoring is advised."
        else:
            risk_desc = "All modules are currently progressing according to the baseline plan with no significant deviations."

        # Generate Paragraph
        response_text = f"""
**Subject: Project {project_name} Status Update - {status_str}**

This email serves as an executive summary for Project **{project_name}**, which is currently classified as **{status_str.upper()}**. 

We are currently tracking **{len(delay_list)}** active schedule deviations. {risk_desc} Additionally, the overall deliverables readiness stands at **{status_data.get('readiness')}%**. 

{("Immediate attention is required to address the critical path items mentioned above." if critical_delays else "We will continue to monitor the minor risks to ensure no impact on the upcoming gateways.")}
"""
    
    return response_text.strip()
