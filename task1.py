import requests
import time
import re
import csv
import sys

def download_crawler_index(year: str, quarter: str):
    """Download the crawler.idx file from the SEC website for the given year and quarter."""
    base_url = "https://www.sec.gov/Archives/edgar/full-index"
    crawler_url = f"{base_url}/{year}/QTR{quarter}/crawler.idx"

    headers = {
        'User-Agent': 'Siva Nehesh - For Research - siva.nehesh@example.com',
        'Accept-Encoding': 'gzip, deflate',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Connection': 'keep-alive'
    }

    print(f"Fetching data from {crawler_url}...")

    for attempt in range(3):  # Retry mechanism in case of failures
        try:
            time.sleep(5)  # Sleep to prevent SEC rate limiting
            response = requests.get(crawler_url, headers=headers)

            if response.status_code == 200:
                print("Data fetched successfully.")
                return response.text
            elif response.status_code == 403:
                print(f"Access denied (403). Retrying... Attempt {attempt + 1}/3")
                time.sleep(10)  # Wait before retrying to avoid IP ban
            else:
                print(f"Failed to fetch data. HTTP Status Code: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Network error: {e}. Retrying...")
            time.sleep(10)

    return None  # Return None if all attempts fail

def extract_10Q_filings(data, year, quarter):
    """Extract 10-Q filings from the crawler.idx file and save them to a CSV file."""
    lines = data.split("\n")
    start_processing = False
    extracted_data = []

    print("Extracting 10-Q filings...")

    for line in lines:
        # Identify the starting point of valid records
        if "Form Type" in line:
            start_processing = True
            continue

        if start_processing:
            # Ensure proper extraction of the last column (URL)
            fields = re.split(r'\s{2,}', line.strip())  # Split by 2+ spaces
            if len(fields) >= 5 and fields[1] == "10-Q":  # Check if it is a 10-Q filing
                date_filed = fields[-2]
                cik = fields[-3]
                url = fields[-1]  # Keep URL as is

                # No more filtering—keep SEC URLs untouched
                extracted_data.append([date_filed, cik, url])
                print(f"Date Filed: {date_filed}, CIK: {cik}, URL: {url}")

    # Save extracted data to a CSV file with a dynamic filename
    csv_filename = f"10Q_filings_{year}_Q{quarter}.csv"
    with open(csv_filename, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Date Filed", "CIK", "URL"])  # Header row
        writer.writerows(extracted_data)

    print(f"10-Q filings saved to {csv_filename}")

if __name__ == "__main__":
    # Read year & quarter from command-line arguments
    if len(sys.argv) != 3:
        print("Usage: python script.py <YEAR> <QUARTER>")
        sys.exit(1)

    year, quarter = sys.argv[1], sys.argv[2]

    # Validate inputs
    if not year.isdigit() or not quarter.isdigit() or int(quarter) not in [1, 2, 3, 4]:
        print("Invalid input. Enter a valid year (YYYY) and quarter (1-4).")
        sys.exit(1)

    # Download & process the crawler.idx file
    data = download_crawler_index(year, quarter)

    if data:
        extract_10Q_filings(data, year, quarter)
    else:
        print("No data received.")
