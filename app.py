import streamlit as st
import subprocess
import os
import time
import pandas as pd
import glob
import shutil
from pathlib import Path
import streamlit.components.v1 as components

# --- Page Config ---
st.set_page_config(
    page_title="Genos - AI Variant Interpretation",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Premium Look ---
st.markdown("""
<style>
    .reportview-container {
        background: #0e1117;
    }
    .main {
        background-color: #0e1117; 
        color: #ffffff;
    }
    h1, h2, h3 {
        color: #00cec9 !important;
        font-family: 'Helvetica Neue', sans-serif;
    }
    .stButton>button {
        background-color: #00cec9;
        color: white;
        border-radius: 10px;
        border: none;
        padding: 10px 24px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #01b8b4;
        box-shadow: 0 4px 15px rgba(0, 206, 201, 0.4);
        transform: translateY(-2px);
    }
    .stAlert {
        background-color: #1f2937;
        color: #e5e7eb;
        border: 1px solid #374151;
    }
    /* Metric Card Styling */
    div[data-testid="metric-container"] {
        background-color: #1f2937;
        border: 1px solid #374151;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.image("https://img.icons8.com/nolan/96/dna-helix.png", width=80)
    st.title("Genos Pipeline")
    st.markdown("---")
    
    st.markdown("### ⚙️ System Status")
    
    # Check Genos Server
    try:
        import requests
        resp = requests.get("http://172.16.227.27:8010/health", timeout=2)
        if resp.status_code == 200:
            st.success("🟢 Genos Core: Online")
        else:
            st.error("🔴 Genos Core: Offline")
    except:
        st.error("🔴 Genos Core: Unreachable")
        
    st.markdown("### 🛠 Configuration")
    model_type = st.selectbox("AI Model", ["DeepSeek-V3", "Genos-1.2B (Local)"])
    output_dir = st.text_input("Output Directory", value="runs/web_upload")

    st.markdown("---")
    st.info("Graduation Project Demo\nv1.0.0")

# --- Main Content ---
st.title("🧬 Genos: Intelligent Variant Analysis")
st.markdown("### Upload your VCF file to start AI-driven pathogenic analysis")

uploaded_file = st.file_uploader("Choose a VCF file (e.g., patient_data.vcf)", type=['vcf', 'vcf.gz'])

if "analysis_running" not in st.session_state:
    st.session_state.analysis_running = False

if uploaded_file is not None:
    # Save file
    os.makedirs("temp_uploads", exist_ok=True)
    file_path = f"temp_uploads/{uploaded_file.name}"
    
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    st.metric(label="File Size", value=f"{uploaded_file.size / 1024:.2f} KB")
    
    # Action Button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🚀 Start Analysis", use_container_width=True):
            st.session_state.analysis_running = True
            
    if st.session_state.analysis_running:
        status_container = st.container()
        
        with status_container:
            progress_bar = st.progress(0)
            status_text = st.empty()
            log_area = st.empty()
            
            # Clean previous run
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir, ignore_errors=True)
                
            # Construct Command
            cmd = [
                "python", "main.py",
                "--vcf", file_path,
                "--output", output_dir
            ]
            
            # Run Pipeline
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Tracking
            logs = []
            
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                
                if line:
                    logs.append(line.strip())
                    if len(logs) > 10: logs.pop(0)  # Keep last 10 lines
                    log_area.code("\n".join(logs), language="bash")
                    
                    # Fuzzy progress tracking based on log keywords
                    if "variant_filter" in line:
                        progress_bar.progress(20, text="STEP 1/6: Filtering Variants...")
                    elif "sequence_context" in line:
                        progress_bar.progress(40, text="STEP 2/6: Extracting Context...")
                    elif "genos_embedding" in line:
                        progress_bar.progress(60, text="STEP 3/6: Generating Embeddings (Remote GPU)...")
                    elif "scoring" in line:
                        progress_bar.progress(80, text="STEP 4/6: AI Scoring (DeepSeek)...")
                    elif "report_generation" in line:
                        progress_bar.progress(95, text="STEP 6/6: Generating Report...")
            
            if process.returncode == 0:
                progress_bar.progress(100, text="✅ Analysis Complete!")
                st.balloons()
                st.session_state.analysis_running = False
                
                # --- Results View ---
                st.divider()
                st.subheader("📊 Analysis Results")
                
                # 1. read stats
                report_path = os.path.join(output_dir, "report.html")
                scores_path = os.path.join(output_dir, "scores.tsv")
                
                if os.path.exists(scores_path):
                    df = pd.read_csv(scores_path, sep='\t')
                    
                    # Metrics Row
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Total Variants Analyzed", len(df))
                    high_risk = len(df[df['final_score'] > 0.8])
                    m2.metric("High Risk Variants", high_risk, delta=f"{high_risk}", delta_color="inverse")
                    m3.metric("Avg Pathogenicity Score", f"{df['final_score'].mean():.3f}")
                    
                    # Top Variants Table
                    st.markdown("#### 🔥 Top Pathogenic Candidates")
                    st.dataframe(
                        df.sort_values(by="final_score", ascending=False).head(10)[['variant_id', 'chrom', 'pos', 'ref', 'alt', 'final_score', 'impact_level']],
                        use_container_width=True
                    )
                
                # 2. Embed Report
                if os.path.exists(report_path):
                    st.markdown("#### 📄 Full Clinical Report")
                    
                    # Download Button
                    with open(report_path, "rb") as f:
                        btn = st.download_button(
                            label="📥 Download HTML Report",
                            data=f,
                            file_name="Genos_Clinical_Report.html",
                            mime="text/html"
                        )
                    
                    # Embedding HTML (Need to handle height)
                    with open(report_path, "r", encoding='utf-8') as f:
                        html_content = f.read()
                        components.html(html_content, height=800, scrolling=True)
            
            else:
                st.error("❌ Pipeline failed. Please check the logs.")
                st.error(process.stderr.read())

else:
    # Landing Page State
    col1, col2 = st.columns(2)
    with col1:
        st.info("👋 Welcome! Please upload a VCF file from the sidebar to begin.")
    with col2:
        st.markdown("##### Features")
        st.markdown("""
        *   **Local Privacy**: Data stays in your network/system.
        *   **Deep Genos Model**: Utilizes 1.2B param biology model.
        *   **RAG Knowledge**: Integrated with ClinVar & PubMed.
        """)
