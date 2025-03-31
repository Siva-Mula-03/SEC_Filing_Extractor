
import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import os
import base64

# SEC Base URL
BASE_URL = "https://www.sec.gov"

# Headers to avoid 403 Forbidden errors
HEADERS = {
    'User-Agent': 'Siva Nehesh - For Research - siva.nehesh@example.com',
    'Accept-Encoding': 'gzip, deflate',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Connection': 'keep-alive'
}

def fetch_10q_filings(year, quarter):
    sec_url = f"{BASE_URL}/Archives/edgar/full-index/{year}/QTR{quarter}/crawler.idx"
    try:
        response = requests.get(sec_url, headers=HEADERS)
        response.raise_for_status()
        filings = []
        for line in response.text.split('\n'):
            if '10-Q' in line and 'edgar/data/' in line:
                parts = line.split()
                if len(parts) >= 5:
                    filings.append({
                        "Form Type": parts[-4],
                        "CIK": parts[-3],
                        "Date": parts[-2],
                        "URL": parts[-1]
                    })
        return filings
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching filings: {e}")
        return []

def get_document_url(filing_url):
    try:
        response = requests.get(filing_url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the table with filing documents
        documents_table = soup.find('table', {'class': 'tableFile'})
        if not documents_table:
            st.error("Could not find documents table in the filing")
            return None
            
        # Find the primary document (usually 10-Q)
        primary_doc = None
        for row in documents_table.find_all('tr')[1:]:  # Skip header row
            cols = row.find_all('td')
            if len(cols) >= 3:
                doc_type = cols[3].text.strip()
                if '10-Q' in doc_type or '10Q' in doc_type:
                    doc_href = cols[2].find('a')['href']
                    primary_doc = urljoin(filing_url, doc_href)
                    break
        
        if not primary_doc:
            # If no 10-Q found, get the first HTML document
            for row in documents_table.find_all('tr')[1:]:
                cols = row.find_all('td')
                if len(cols) >= 3:
                    doc_href = cols[2].find('a')['href']
                    if doc_href.endswith('.htm') or doc_href.endswith('.html'):
                        primary_doc = urljoin(filing_url, doc_href)
                        break
        
        return primary_doc
    except Exception as e:
        st.error(f"Error finding document URL: {str(e)}")
        return None

def extract_section_text(doc_url, start_section=None, end_section=None):
    try:
        response = requests.get(doc_url, headers=HEADERS)
        response.raise_for_status()
        
        # Handle both HTML and plain text documents
        if doc_url.endswith('.txt'):
            # For plain text filings
            text = response.text
            lines = [line.strip() for line in text.split('\n') if line.strip()]
        else:
            # For HTML filings
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'meta', 'link', 'nav', 'header', 'footer']):
                element.decompose()
            
            text = soup.get_text('\n', strip=True)
            lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        if not start_section and not end_section:
            return lines
        
        start_idx = 0
        end_idx = len(lines)
        
        if start_section:
            start_pattern = re.compile(rf'\b{re.escape(start_section)}\b', re.IGNORECASE)
            for i, line in enumerate(lines):
                if start_pattern.search(line):
                    start_idx = i
                    break
        
        if end_section:
            end_pattern = re.compile(rf'\b{re.escape(end_section)}\b', re.IGNORECASE)
            for i, line in enumerate(lines[start_idx:], start=start_idx):
                if end_pattern.search(line):
                    end_idx = i
                    break
        
        return lines[start_idx:end_idx]
    except Exception as e:
        st.error(f"Extraction error: {str(e)}")
        return None

# Set up the groq API configuration
API_KEY = "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"
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Function to send a message to the groq API and get a response
def process_with_groq(text):
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }

    data = {
        "model": "llama-3.3-70b-versatile",  # Model name as per the documentation
        "messages": [
            {"role": "user", "content": str(text)}  # Ensure content is a string
        ],
        "temperature": 0.7  # Optional parameter
    }

    try:
        # Send POST request with a timeout of 30 seconds
        response = requests.post(API_URL, headers=headers, json=data, timeout=30)

        # Log the response status code and response body for debugging
        print("Response Status Code:", response.status_code)
        print("Response Text:", response.text)

        # Check if the request was successful (status code 200)
        response.raise_for_status()  # Will raise an exception for 4xx or 5xx status codes

        response_data = response.json()

        # Check if 'choices' are in the response and return content
        if 'choices' in response_data and len(response_data['choices']) > 0:
            return response_data['choices'][0]['message']['content']
        else:
            print("Unexpected response structure:", json.dumps(response_data, indent=2))
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error during API request: {e}")
        return None

# Set page config
st.set_page_config(page_title="SEC Filing Analyzer", layout="wide")
st.title("📊 SEC Extract")

# Sidebar: Task Selection
with st.sidebar:
    st.header("Configuration")
    task = st.radio("Select Task", ["Task 1: 10-Q Filings", "Task 2: URL Text Extraction", "Task 3: Code Files & Documentation"])

    # Add dropdown for code files selection under Task 3
    if task == "Task 3: Code Files & Documentation":
        codefile = st.selectbox("Select Code File", [
            "combined_tsk1_tsk2_with_ui-2.py",
            "task1.py",
            "task2.py",
            "Documentation.pdf"
        ])

# Debugging step: Check which task is selected
st.write(f"Selected Task: {task}")

# Check the current working directory
st.write(f"Current working directory: {os.getcwd()}")

if task == "Task 1: 10-Q Filings":
    st.header("🔍 Fetch 10-Q Filings")
    col1, col2 = st.columns([1, 2])
    with col1:
        year = st.number_input("Enter Year", min_value=1995, max_value=2025, value=2024)
    with col2:
        quarters = st.multiselect("Select Quarters", [1, 2, 3, 4], default=[1])

    if st.button("Fetch Filings"):
        with st.spinner("Fetching filings..."):
            all_filings = []
            for q in quarters:
                filings = fetch_10q_filings(year, q)
                if filings:
                    all_filings.extend(filings)

            if all_filings:
                df = pd.DataFrame(all_filings)
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
                df = df.sort_values(by='Date', ascending=False)
                st.session_state.df = df
                st.session_state.filtered_df = df.copy()
                st.success(f"Found {len(df)} filings!")
            else:
                st.warning("No filings found for the selected criteria")

    if 'df' in st.session_state:
        st.write("### Filter Results")
        query = st.text_input("Search by CIK, Form Type, or Date")
        
        if query:
            st.session_state.filtered_df = st.session_state.df[st.session_state.df.apply(
                lambda row: query.lower() in str(row).lower(), axis=1
            )]
            st.info(f"Filtered to {len(st.session_state.filtered_df)} filings")
        else:
            st.session_state.filtered_df = st.session_state.df.copy()

        st.dataframe(st.session_state.filtered_df, height=500)

        if not st.session_state.filtered_df.empty:
            col1, col2 = st.columns(2)
            with col1:
                csv = st.session_state.filtered_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv,
                    file_name=f"10Q_filings_{year}_Q{'-'.join(map(str, quarters))}.csv",
                    mime='text/csv'
                )
            with col2:
                txt = st.session_state.filtered_df.to_string(index=False)
                st.download_button(
                    label="📥 Download as Text",
                    data=txt,
                    file_name=f"10Q_filings_{year}_Q{'-'.join(map(str, quarters))}.txt",
                    mime='text/plain'
                )

elif task == "Task 2: URL Text Extraction":
    st.header("📑 Extract SEC Document Section")
    
    with st.expander("ℹ️ How to use", expanded=True):
        st.write("""1. Paste the SEC Filing URL for the document you want to extract from.
                   2. Specify the sections of the document (optional).
                   3. Extract the document and let the AI analyze its contents.""")

    doc_url = st.text_input("Enter SEC Filing URL", value="")
    start_section = st.text_input("Enter start section (optional)")
    end_section = st.text_input("Enter end section (optional)")

    if st.button("Extract Section"):
        if doc_url:
            with st.spinner("Extracting document..."):
                content = extract_section_text(doc_url, start_section, end_section)
                if not content:
                    st.warning("No content was extracted. Please check the URL and section names.")
                else:
                    st.write("### Extracted Content")
                    st.write("\n".join(content))
                    st.write("### Processing with AI...")
                    ai_results = process_with_groq(content)
                    if ai_results:
                        st.write("### AI Analysis Result")
                        st.markdown(ai_results)
                    else:
                        st.warning("AI processing did not return results.")
        else:
            st.warning("Please enter a valid SEC filing URL.")

elif task == "Task 3: Code Files & Documentation":
    st.header("📄 Code Files and Documentation")

    # Checking if the codefile dropdown is selected
    if codefile:
        try:
            file_path = os.path.join(os.getcwd(), codefile)
            if os.path.exists(file_path):
                if codefile.endswith('.pdf'):
                    # Display PDF with embedded viewer and download option
                    with open(file_path, "rb") as f:
                        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                        
                        # PDF Viewer
                        pdf_display = f"""
                        <iframe src="data:application/pdf;base64,{base64_pdf}" 
                                width="100%" 
                                height="800px" 
                                style="border:1px solid #EEE;">
                        </iframe>
                        """
                        st.markdown(pdf_display, unsafe_allow_html=True)
                        
                        # Download button
                        st.download_button(
                            label="📥 Download Full Documentation",
                            data=f,
                            file_name=codefile,
                            mime="application/pdf"
                        )
                else:
                    # Handle text/code files
                    with open(file_path, "r", encoding='utf-8') as file:
                        code = file.read()
                        if codefile.endswith('.py'):
                            st.code(code, language='python')
                        else:
                            st.text(code)
            else:
                st.error("File not found. Please check the file name or path.")
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")
