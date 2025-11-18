import streamlit as st
import anthropic
from database import Database
from datetime import datetime, timedelta
import io

# Page config
st.set_page_config(
    page_title="ParentAdvocateAI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
db = Database()

# Load system prompt
SYSTEM_PROMPT = """You are Parent Advocate AI, an assistant built to support parents involved with the South Australian Department for Child Protection (DCP). You are NOT a lawyer. You provide information, explanation, education, structure, organisation, and support only.

JURISDICTION:
Assume all cases relate to South Australia, Department for Child Protection (DCP), and SA Youth Court.
You conceptually reference: Children and Young People (Safety) Act 2017, Children and Young People (Safety) Regulations 2017, Child Safety (Prohibited Persons) Act 2016, and related SA legislation.

TONE AND BEHAVIOUR:
- Supportive but direct, clear, calm, factual
- No judgement, no legal advice (information only)
- Break everything into steps, checklists, or bullet lists
- Always summarise "Next steps" at the end
- Avoid jargon unless you explain it
- Prioritise clarity, simplicity, accuracy

CRISIS AND SAFETY:
If the user appears distressed, in danger, or in crisis, gently recommend:
- Crisis Response Unit SA: 131 611
- Lifeline: 13 11 14
- Legal Helpline SA: 1300 366 424
- Alcohol and Drug Information Service: 1300 131 340
- Parent Helpline: 1300 364 100

RESPONSE STRUCTURE:
1. Acknowledge the situation briefly
2. Summarise the problem in simple terms
3. Explain what DCP or the court is expecting
4. Provide steps to take, evidence required, how to record it
5. Suggest relevant services if needed
6. End with a short NEXT STEPS list

BOUNDARIES:
You must NOT give legal advice, tell users to hide information, break the law, manipulate drug tests, promise outcomes, attack workers/agencies, or provide medical diagnoses.
You MUST provide safe, responsible, factual information and encourage speaking to a lawyer for case-specific legal advice.

WRITING STYLE:
- Short paragraphs
- Bullet lists
- Headings for long answers
- Child-focused, neutral, factual
- Encourage documentation and evidence
- Everything must be printable and court-friendly"""

# CSS Styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stat-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
    }
    .success-box {
        background: #d4edda;
        border-left: 4px solid #28a745;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .warning-box {
        background: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .info-box {
        background: #d1ecf1;
        border-left: 4px solid #17a2b8;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    }
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: bold;
        color: #667eea;
    }
</style>
""", unsafe_allow_html=True)

# Session state initialization
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'user_name' not in st.session_state:
    st.session_state.user_name = ""
if 'user_type' not in st.session_state:
    st.session_state.user_type = "parent"
if 'chat_messages' not in st.session_state:
    st.session_state.chat_messages = []

# Claude AI Client
def get_ai_response(user_message, chat_history=[]):
    try:
        client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
        
        # Build message history
        messages = []
        for msg in chat_history[-10:]:  # Last 10 messages for context
            messages.append({"role": msg[0], "content": msg[1]})
        messages.append({"role": "user", "content": user_message})
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=messages
        )
        
        return response.content[0].text
    except Exception as e:
        return f"Error connecting to AI: {str(e)}"

# Authentication Pages
def show_login():
    st.markdown('<div class="main-header"><h1>🛡️ ParentAdvocateAI</h1><p>AI-powered case management for family reunification</p></div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        tab1, tab2 = st.tabs(["🔐 Login", "📝 Sign Up"])
        
        with tab1:
            st.markdown("### Welcome Back")
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            
            if st.button("Login", use_container_width=True, type="primary"):
                if email and password:
                    user = db.verify_user(email, password)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user_id = user[0]
                        st.session_state.user_name = user[1]
                        st.session_state.user_type = user[2]
                        st.success("✅ Login successful!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials")
                else:
                    st.warning("Please enter both email and password")
        
        with tab2:
            st.markdown("### Create Your Account")
            full_name = st.text_input("Full Name", key="signup_name")
            signup_email = st.text_input("Email", key="signup_email")
            signup_password = st.text_input("Password", type="password", key="signup_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="confirm_password")
            
            st.info("📌 This system is for parents working with DCP South Australia")
            
            if st.button("Create Account", use_container_width=True, type="primary"):
                if not all([full_name, signup_email, signup_password, confirm_password]):
                    st.warning("Please fill in all fields")
                elif signup_password != confirm_password:
                    st.error("Passwords don't match")
                elif len(signup_password) < 6:
                    st.error("Password must be at least 6 characters")
                else:
                    success, message = db.create_user(signup_email, signup_password, full_name)
                    if success:
                        st.success("✅ " + message)
                        st.info("Please log in with your new account")
                    else:
                        st.error("❌ " + message)

# Dashboard
def show_dashboard():
    st.markdown(f'<div class="main-header"><h1>🏠 Dashboard</h1><p>Welcome back, {st.session_state.user_name}!</p></div>', unsafe_allow_html=True)
    
    # Get user stats
    stats = db.get_user_stats(st.session_state.user_id)
    case = stats['case_details']
    
    # Top metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📄 Documents", stats['documents'])
    with col2:
        st.metric("✅ Compliance", f"{stats['compliance_pct']}%")
    with col3:
        st.metric("⚠️ Open Violations", stats['violations'])
    with col4:
        st.metric("📅 Appointments", stats['appointments'])
    
    st.markdown("---")
    
    # Quick actions
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📌 Quick Actions")
        if st.button("📄 Upload Document", use_container_width=True):
            st.session_state.page = "📄 Documents"
            st.rerun()
        if st.button("⚠️ Report Violation", use_container_width=True):
            st.session_state.page = "⚠️ Violations"
            st.rerun()
        if st.button("💬 Chat with AI", use_container_width=True):
            st.session_state.page = "💬 AI Chat"
            st.rerun()
        if st.button("📊 Generate Report", use_container_width=True):
            st.session_state.page = "📊 Reports"
            st.rerun()
    
    with col2:
        st.markdown("### 📋 Recent Activity")
        
        # Show recent violations
        violations = db.get_violations(st.session_state.user_id)
        if violations:
            st.markdown(f'<div class="warning-box">⚠️ {len(violations)} violation(s) tracked</div>', unsafe_allow_html=True)
        
        # Show pending tasks
        if stats['pending_tasks'] > 0:
            st.markdown(f'<div class="info-box">📌 {stats["pending_tasks"]} task(s) pending</div>', unsafe_allow_html=True)
        
        # Show compliance status
        if stats['compliance_pct'] >= 80:
            st.markdown(f'<div class="success-box">✅ Great compliance: {stats["compliance_pct"]}%</div>', unsafe_allow_html=True)
        elif stats['compliance_pct'] >= 50:
            st.markdown(f'<div class="info-box">📈 Keep going: {stats["compliance_pct"]}%</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="warning-box">⚠️ Needs attention: {stats["compliance_pct"]}%</div>', unsafe_allow_html=True)

# Documents
def show_documents():
    st.markdown('<div class="main-header"><h1>📄 Documents</h1><p>Upload and manage case documents</p></div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📤 Upload", "📂 My Documents"])
    
    with tab1:
        st.markdown("### Upload New Document")
        
        uploaded_file = st.file_uploader("Choose a file", type=['pdf', 'doc', 'docx', 'txt', 'jpg', 'png'])
        category = st.selectbox("Document Category", [
            "Court Orders",
            "Case Plans",
            "DCP Notes",
            "Lawyer Letters",
            "Contact Logs",
            "Assessments/Reports",
            "Drug Test Results",
            "Program Certificates",
            "Other"
        ])
        
        if uploaded_file and st.button("📤 Upload & Analyze with AI", type="primary"):
            with st.spinner("Uploading and analyzing document..."):
                # Read file
                file_data = uploaded_file.read()
                
                # Get AI analysis
                ai_prompt = f"Analyze this {category} document. Extract key information, identify any requirements, deadlines, or concerns mentioned. Summarize in bullet points."
                ai_analysis = get_ai_response(ai_prompt)
                
                # Save to database
                doc_id = db.add_document(
                    st.session_state.user_id,
                    uploaded_file.name,
                    uploaded_file.type,
                    category,
                    file_data,
                    ai_analysis
                )
                
                st.success(f"✅ Document uploaded successfully! (ID: {doc_id})")
                
                # Show AI analysis
                st.markdown("### 🤖 AI Analysis")
                st.info(ai_analysis)
    
    with tab2:
        st.markdown("### Your Documents")
        
        docs = db.get_documents(st.session_state.user_id)
        
        if docs:
            for doc in docs:
                doc_id, filename, file_type, category, upload_date, ai_analysis = doc
                
                with st.expander(f"📄 {filename} - {category}"):
                    st.write(f"**Uploaded:** {upload_date}")
                    st.write(f"**Type:** {file_type}")
                    if ai_analysis:
                        st.markdown("**AI Analysis:**")
                        st.info(ai_analysis)
        else:
            st.info("No documents uploaded yet")

# Violations Tracker
def show_violations():
    st.markdown('<div class="main-header"><h1>⚠️ Violations Tracker</h1><p>Track DCP violations of SA legislation</p></div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["➕ Report New", "📋 View All"])
    
    with tab1:
        st.markdown("### Report a New Violation")
        
        violation_type = st.selectbox("Violation Type", [
            "Failed to provide services (s20)",
            "Inadequate case planning (s37)",
            "Denied contact without court authority (s49)",
            "Failed to notify of court proceedings",
            "Inadequate consultation with parents (s18)",
            "Failed to follow reunification plan (s22)",
            "Breach of confidentiality",
            "Failure to provide interpreter",
            "Other legislative breach"
        ])
        
        description = st.text_area("Description of Violation", height=150,
            placeholder="Describe what happened, who was involved, and why you believe this violated the legislation...")
        
        date_occurred = st.date_input("Date Occurred")
        
        legislation_ref = st.text_input("Legislation Reference (if known)",
            placeholder="e.g. Children and Young People (Safety) Act 2017 s20")
        
        evidence = st.text_area("Evidence/Documentation",
            placeholder="List any evidence you have: emails, letters, witness statements, recordings, etc.")
        
        if st.button("⚠️ Submit Violation Report", type="primary"):
            if description:
                db.add_violation(
                    st.session_state.user_id,
                    violation_type,
                    description,
                    str(date_occurred),
                    legislation_ref,
                    evidence
                )
                st.success("✅ Violation reported and saved")
                st.info("💡 Consider discussing this with your lawyer")
            else:
                st.warning("Please provide a description")
    
    with tab2:
        st.markdown("### All Reported Violations")
        
        violations = db.get_violations(st.session_state.user_id)
        
        if violations:
            for v in violations:
                v_id, v_type, desc, date, leg_ref, status, created = v
                
                status_emoji = "🔴" if status == "open" else "✅"
                
                with st.expander(f"{status_emoji} {v_type} - {date}"):
                    st.write(f"**Description:** {desc}")
                    if leg_ref:
                        st.write(f"**Legislation:** {leg_ref}")
                    st.write(f"**Status:** {status}")
                    st.write(f"**Reported:** {created}")
        else:
            st.info("No violations reported yet")

# Compliance Tracker
def show_compliance():
    st.markdown('<div class="main-header"><h1>✅ Compliance Tracker</h1><p>Track requirements and progress</p></div>', unsafe_allow_html=True)
    
    # Overall compliance
    stats = db.get_user_stats(st.session_state.user_id)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Completed Tasks", stats['completed_tasks'])
    with col2:
        st.metric("Pending Tasks", stats['pending_tasks'])
    with col3:
        st.metric("Overall Compliance", f"{stats['compliance_pct']}%")
    
    st.progress(stats['compliance_pct'] / 100)
    
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["📋 Tasks", "➕ Add Task"])
    
    with tab1:
        st.markdown("### Your Compliance Tasks")
        
        tasks = db.get_compliance_tasks(st.session_state.user_id)
        
        if tasks:
            for task in tasks:
                task_id, name, category, due, status, completion, notes = task
                
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    status_emoji = "✅" if status == "completed" else "⏳"
                    st.write(f"{status_emoji} **{name}** ({category})")
                    if notes:
                        st.caption(notes)
                
                with col2:
                    st.write(f"Due: {due}")
                
                with col3:
                    if status == "pending":
                        if st.button("Mark Complete", key=f"complete_{task_id}"):
                            db.update_task_status(task_id, "completed")
                            st.rerun()
        else:
            st.info("No tasks yet. Add compliance requirements below.")
    
    with tab2:
        st.markdown("### Add New Task")
        
        task_name = st.text_input("Task Name", placeholder="e.g. Complete drug test")
        task_category = st.selectbox("Category", [
            "Drug Testing",
            "Programs (DASSA, Sonder, etc)",
            "Appointments",
            "Safety Plan Tasks",
            "Court Requirements",
            "Parent Programs",
            "Other"
        ])
        due_date = st.date_input("Due Date")
        task_notes = st.text_area("Notes")
        
        if st.button("➕ Add Task", type="primary"):
            if task_name:
                db.add_compliance_task(
                    st.session_state.user_id,
                    task_name,
                    task_category,
                    str(due_date),
                    task_notes
                )
                st.success("✅ Task added")
                st.rerun()

# Appointments
def show_appointments():
    st.markdown('<div class="main-header"><h1>📅 Appointments</h1><p>Manage your appointments and schedule</p></div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📅 Upcoming", "➕ Add New"])
    
    with tab1:
        appointments = db.get_appointments(st.session_state.user_id)
        
        if appointments:
            for appt in appointments:
                appt_id, appt_type, date_time, location, status, notes = appt
                
                status_color = "🟢" if status == "scheduled" else "🔴" if status == "missed" else "✅"
                
                with st.expander(f"{status_color} {appt_type} - {date_time}"):
                    st.write(f"**Location:** {location}")
                    st.write(f"**Status:** {status}")
                    if notes:
                        st.write(f"**Notes:** {notes}")
        else:
            st.info("No appointments scheduled")
    
    with tab2:
        st.markdown("### Schedule New Appointment")
        
        appt_type = st.selectbox("Appointment Type", [
            "Drug Test",
            "Court Hearing",
            "DCP Meeting",
            "Program Session",
            "Doctor/Health",
            "Lawyer Meeting",
            "Supervised Visit",
            "Other"
        ])
        
        appt_date = st.date_input("Date")
        appt_time = st.time_input("Time")
        location = st.text_input("Location")
        appt_notes = st.text_area("Notes")
        
        if st.button("📅 Add Appointment", type="primary"):
            if location:
                date_time = f"{appt_date} {appt_time}"
                db.add_appointment(
                    st.session_state.user_id,
                    appt_type,
                    date_time,
                    location,
                    appt_notes
                )
                st.success("✅ Appointment added")
                st.rerun()

# AI Chat
def show_ai_chat():
    st.markdown('<div class="main-header"><h1>💬 AI Chat Support</h1><p>Get guidance and support from ParentAdvocateAI</p></div>', unsafe_allow_html=True)
    
    # Load chat history from database
    if not st.session_state.chat_messages:
        history = db.get_chat_history(st.session_state.user_id)
        st.session_state.chat_messages = [{"role": msg[0], "content": msg[1]} for msg in history]
    
    # Display chat messages
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask me anything about your case, DCP processes, or SA legislation..."):
        # Add user message
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        
        # Save to database
        db.save_chat_message(st.session_state.user_id, "user", prompt)
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Build chat history for context
                chat_history = [(msg["role"], msg["content"]) for msg in st.session_state.chat_messages[:-1]]
                response = get_ai_response(prompt, chat_history)
                st.write(response)
        
        # Add assistant message
        st.session_state.chat_messages.append({"role": "assistant", "content": response})
        
        # Save to database
        db.save_chat_message(st.session_state.user_id, "assistant", response)

# Reflections/Journal
def show_reflections():
    st.markdown('<div class="main-header"><h1>💭 Reflections & Journal</h1><p>Document your progress and reflections</p></div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["✍️ New Entry", "📖 History"])
    
    with tab1:
        st.markdown("### Write a Reflection")
        
        st.info("""
        **Reflection Prompts:**
        - What progress have I made this week?
        - What challenges am I facing?
        - What am I doing to address DCP's concerns?
        - How am I working toward reunification?
        - What support do I need?
        """)
        
        reflection_date = st.date_input("Date")
        reflection_text = st.text_area("Your Reflection", height=300,
            placeholder="Write your thoughts, progress updates, challenges, and plans...")
        
        if st.button("💾 Save Reflection", type="primary"):
            if reflection_text:
                db.add_reflection(st.session_state.user_id, reflection_text, str(reflection_date))
                st.success("✅ Reflection saved")
                st.rerun()
    
    with tab2:
        st.markdown("### Your Reflection History")
        
        reflections = db.get_reflections(st.session_state.user_id)
        
        if reflections:
            for refl in reflections:
                text, date, created = refl
                
                with st.expander(f"📝 {date}"):
                    st.write(text)
                    st.caption(f"Created: {created}")
        else:
            st.info("No reflections yet")

# Reports
def show_reports():
    st.markdown('<div class="main-header"><h1>📊 Reports & Evidence</h1><p>Generate court-ready reports</p></div>', unsafe_allow_html=True)
    
    st.markdown("### Generate Reports")
    
    report_type = st.selectbox("Select Report Type", [
        "Comprehensive Case Summary",
        "Compliance Progress Report",
        "Violations Evidence Package",
        "Weekly Progress Update",
        "Court Submission Package"
    ])
    
    date_from = st.date_input("From Date")
    date_to = st.date_input("To Date")
    
    if st.button("📄 Generate Report with AI", type="primary"):
        with st.spinner("Generating comprehensive report..."):
            # Gather data
            stats = db.get_user_stats(st.session_state.user_id)
            violations = db.get_violations(st.session_state.user_id)
            tasks = db.get_compliance_tasks(st.session_state.user_id)
            docs = db.get_documents(st.session_state.user_id)
            reflections = db.get_reflections(st.session_state.user_id)
            
            # Build report prompt
            report_prompt = f"""Generate a professional {report_type} for a parent working toward reunification with DCP South Australia.

**Case Data:**
- Compliance Rate: {stats['compliance_pct']}%
- Completed Tasks: {stats['completed_tasks']}
- Pending Tasks: {stats['pending_tasks']}
- Violations Reported: {stats['violations']}
- Documents on File: {stats['documents']}
- Reflections Written: {len(reflections)}

**Date Range:** {date_from} to {date_to}

Create a detailed, court-appropriate report that:
1. Summarizes progress and compliance
2. Lists completed requirements
3. Addresses any concerns or violations
4. Demonstrates commitment to reunification
5. Includes next steps and goals

Format with headers, bullet points, and professional language suitable for court submission."""

            report = get_ai_response(report_prompt)
            
            st.markdown("### 📄 Generated Report")
            st.markdown(report)
            
            st.download_button(
                "📥 Download Report",
                report,
                file_name=f"{report_type.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain"
            )

# 18-Year Order Support
def show_18_year_support():
    st.markdown('<div class="main-header"><h1>📋 18-Year Order Support</h1><p>Understanding and navigating long-term orders</p></div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["📖 Information", "⚖️ Your Rights", "📍 Pathways", "🤖 AI Guidance"])
    
    with tab1:
        st.markdown("### What is an 18-Year Order?")
        
        st.info("""
        An 18-year guardianship order (under s38 of the Children and Young People (Safety) Act 2017) 
        means DCP has guardianship of your child until they turn 18. However:
        
        **This does NOT mean reunification is impossible.**
        """)
        
        st.markdown("""
        **Key Points:**
        - The order can be reviewed and varied
        - You can apply to revoke the order
        - Contact arrangements can be modified
        - The Court must consider the child's best interests
        - Demonstrable change is essential
        
        **Legislation:**
        Children and Young People (Safety) Act 2017:
        - s38: Long-term guardianship orders
        - s52: Variation/revocation of orders
        - s47-51: Contact provisions
        """)
    
    with tab2:
        st.markdown("### Your Rights Under an 18-Year Order")
        
        st.success("""
        **You Still Have Rights:**
        ✅ Right to contact (unless court order restricts it)
        ✅ Right to information about your child's welfare
        ✅ Right to apply for variation of the order
        ✅ Right to legal representation
        ✅ Right to be consulted on major decisions (in some cases)
        """)
        
        st.warning("""
        **DCP's Responsibilities:**
        - Must act in child's best interests
        - Should facilitate contact where appropriate
        - Must provide updates on child's welfare
        - Should support reunification efforts where possible
        """)
    
    with tab3:
        st.markdown("### Pathways to Modification or Revocation")
        
        st.markdown("""
        **Step-by-Step Process:**
        
        1. **Demonstrate Sustained Change**
           - Complete all recommended programs
           - Maintain stable housing and income
           - Address all concerns that led to removal
           - Document everything
        
        2. **Engage with DCP**
           - Attend all visits consistently
           - Follow contact conditions
           - Build positive relationship with caseworker
           - Show commitment to child's wellbeing
        
        3. **Gather Evidence**
           - Program completion certificates
           - Clean drug tests (6+ months)
           - Stable housing proof
           - Employment records
           - Character references
           - Therapy/counseling records
        
        4. **Legal Application**
           - Consult a family lawyer
           - Apply to vary or revoke order (s52)
           - File evidence of change
           - Attend court hearings
        
        5. **Court Considerations**
           - Child's best interests (paramount)
           - Strength of parent-child relationship
           - Evidence of sustained change
           - Child's views (age-appropriate)
           - Risk assessment
        """)
    
    with tab4:
        st.markdown("### Get AI Guidance on Your Situation")
        
        situation = st.text_area("Describe your situation and ask specific questions about 18-year orders...",
            height=200,
            placeholder="e.g., What evidence do I need? How long until I can apply? What are my chances?")
        
        if st.button("🤖 Get AI Guidance", type="primary"):
            if situation:
                with st.spinner("Analyzing your situation..."):
                    response = get_ai_response(f"Regarding 18-year guardianship orders in SA: {situation}")
                    st.info(response)

# Profile/Settings
def show_profile():
    st.markdown('<div class="main-header"><h1>👤 Profile & Case Details</h1></div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["👤 Personal Info", "📋 Case Details"])
    
    with tab1:
        st.markdown("### Your Information")
        st.text_input("Name", value=st.session_state.user_name, disabled=True)
        st.info("Contact support to change your email or password")
    
    with tab2:
        st.markdown("### Case Details")
        
        case = db.get_case_details(st.session_state.user_id)
        
        children_names = st.text_input("Children's Names", value=case[3] if case and case[3] else "")
        children_ages = st.text_input("Children's Ages", value=case[4] if case and case[4] else "")
        case_number = st.text_input("Case Number", value=case[5] if case and case[5] else "")
        dcp_worker = st.text_input("DCP Worker Name", value=case[6] if case and case[6] else "")
        dcp_contact = st.text_input("DCP Worker Contact", value=case[7] if case and case[7] else "")
        court_date = st.date_input("Next Court Date")
        separation_date = st.date_input("Separation Date")
        
        if st.button("💾 Save Case Details", type="primary"):
            db.update_case_details(
                st.session_state.user_id,
                children_names=children_names,
                children_ages=children_ages,
                case_number=case_number,
                dcp_worker_name=dcp_worker,
                dcp_worker_contact=dcp_contact,
                court_date=str(court_date),
                separation_date=str(separation_date)
            )
            st.success("✅ Case details updated")

# Main Application Logic
def main():
    if not st.session_state.authenticated:
        show_login()
    else:
        # Sidebar navigation
        with st.sidebar:
            st.markdown("### 🛡️ ParentAdvocateAI")
            st.markdown(f"**{st.session_state.user_name}**")
            st.caption(f"*{st.session_state.user_type.title()}*")
            st.markdown("---")
            
            # Navigation menu
            page = st.radio("Navigation", [
                "🏠 Dashboard",
                "📄 Documents",
                "⚠️ Violations",
                "✅ Compliance",
                "📅 Appointments",
                "💭 Reflections",
                "📊 Reports",
                "💬 AI Chat",
                "📋 18-Year Orders",
                "👤 Profile"
            ], key="sidebar_nav")
            
            st.markdown("---")
            
            # Emergency contacts
            with st.expander("🆘 Crisis Contacts"):
                st.markdown("""
                **Crisis Response Unit SA:**  
                131 611
                
                **Lifeline:**  
                13 11 14
                
                **Legal Helpline SA:**  
                1300 366 424
                
                **Parent Helpline:**  
                1300 364 100
                """)
            
            st.markdown("---")
            
            if st.button("🚪 Logout", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        
        # Route to pages
        if "Dashboard" in page:
            show_dashboard()
        elif "Documents" in page:
            show_documents()
        elif "Violations" in page:
            show_violations()
        elif "Compliance" in page:
            show_compliance()
        elif "Appointments" in page:
            show_appointments()
        elif "Reflections" in page:
            show_reflections()
        elif "Reports" in page:
            show_reports()
        elif "AI Chat" in page:
            show_ai_chat()
        elif "18-Year Orders" in page:
            show_18_year_support()
        elif "Profile" in page:
            show_profile()

if __name__ == "__main__":
    main()
    