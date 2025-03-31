import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Base URL of SEC
BASE_URL = "https://www.sec.gov"

# Get user inputs
filing_url = input("Enter the SEC Filing URL: ").strip()
section_name = input("Enter the start section (e.g., 'Filing Date'): ").strip()
end_marker = input("Enter the end section (e.g., 'Data Files'): ").strip()

# Headers
HEADERS = {
    'User-Agent': 'Siva Nehesh - For Research - siva.nehesh@example.com',
    'Accept-Encoding': 'gzip, deflate',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Connection': 'keep-alive'
}

try:
    # Send request to SEC website
    response = requests.get(filing_url, headers=HEADERS)
    response.raise_for_status()

    # Parse HTML
    soup = BeautifulSoup(response.text, "html.parser")

    # Find the Form 10-Q document link
    doc_link = None
    for link in soup.find_all("a", href=True):
        if "10q.htm" in link["href"].lower():
            doc_link = urljoin(BASE_URL, link["href"])
            break

    if doc_link:
        print(f"\nFound Form 10-Q Document: {doc_link}\n")
    else:
        print("Form 10-Q Document Not Found.")

    # Extracting required section
    text_lines = soup.get_text("\n").split("\n")
    start_idx, end_idx = None, None
    extracted_section = []

    for i, line in enumerate(text_lines):
        clean_line = line.strip()
        if section_name in clean_line and start_idx is None:
            start_idx = i
        if start_idx is not None:
            extracted_section.append(clean_line)
        if end_marker in clean_line and start_idx is not None:
            break

    extracted_text = "\n".join(filter(None, extracted_section))

    # Print extracted section
    if extracted_text:
        print("\nExtracted Section:\n" + "=" * 40)
        print(extracted_text)
        print("=" * 40)
    else:
        print("Could not extract the required section.")

except requests.exceptions.RequestException as e:
    print(f"Error fetching URL: {e}")
