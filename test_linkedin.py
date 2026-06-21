import sys
import logging
from jobspy import scrape_jobs
import pandas as pd

logging.basicConfig(level=logging.INFO)

test_configs = [
    {'loc': 'Lahore, Pakistan', 'name': 'Full String'},
    {'loc': 'Pakistan', 'name': 'Country Only'},
    {'loc': 'Lahore', 'name': 'City Only'},
]

for config in test_configs:
    print(f"\n--- Testing Location: {config['loc']} ({config['name']}) ---")
    try:
        df = scrape_jobs(
            site_name=["linkedin"],
            search_term="Analytics Engineer",
            location=config['loc'],
            results_wanted=50,
            country_indeed="Pakistan",
            hours_old=720,
            is_remote=False,
        )
        if df is not None and not df.empty:
            print(f"Results: {len(df)} jobs found.")
            titles = df["title"].head(3).tolist()
            print(f"Sample titles: {titles}")
        else:
            print("Results: 0 jobs found.")
    except Exception as e:
        print(f"Error occurred: {e}")
