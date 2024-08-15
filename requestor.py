import requests
import json
import csv
import pandas as pd
import time 
import os
import streamlit as st


def get_part_data(mpn):
    try:
        payload = {'searchByPartRequest': {'mouserPartNumber': mpn}}
        headers = {'Content-Type': 'application/json'}
        response = requests.post(MOUSER_API_URL, headers=headers, json=payload)
        
        if response.status_code == 200:
            return json.loads(response.text)
        else:
            if response.status_code == 403:
                print("Error: Received status code 403. Retrying in 10 seconds...")
                time.sleep(10)
                response = requests.post(MOUSER_API_URL, headers=headers, json=payload)
                if response.status_code == 200:
                    return json.loads(response.text)
                else:
                    print(f"Error: Received status code {response.status_code} after retry")
                    return None
            # print(f"Error: Received status code {response.status_code}")
            # return None
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return None

def group_mpns(mpns, max_per_group=10, low=None, high=None, limit_rows=False):
    grouped_mpns = []
    current_group = []

    if limit_rows:
        mpns = mpns[low:high]
    for mpn in mpns:
        current_group.append(str(mpn))
        if len(current_group) == max_per_group:
            grouped_mpns.append("|".join(current_group))
            current_group = []

    # Add any remaining MPNs in the last group
    if current_group:
        grouped_mpns.append(" | ".join(current_group))

    return grouped_mpns

def read_mpn_csv(uploaded_file):
    mpns = []
    try:
        df = pd.read_csv(uploaded_file, header=None)
        mpns = df.iloc[:, 0].tolist()  # Assuming the MPNs are in the first column
    except Exception as e:
        st.error(f"Failed to read the uploaded CSV file: {e}")
    return mpns


def process_list(grouped_mpn_strings):
    failures = 0
    placeholder = st.empty()
    progress_bar = st.progress(0, text="Request progress...")  # Initialize the progress bar
    total_groups = len(grouped_mpn_strings)

    for (i, mpn_group) in enumerate (grouped_mpn_strings):
        time.sleep(2)
        group_count = len(grouped_mpn_strings)
        placeholder.write(f"Processing group {i} of {group_count} - time remaining {(group_count - i) * 2} seconds")
        try:
            response = get_part_data(mpn_group)
            if response:
                print(response)
                print("Errors: ", response['Errors'])
                print("Result count: ", response['SearchResults']['NumberOfResult'])
                for idx, part in enumerate(response['SearchResults']['Parts']):
                    # print(idx, " | MPN: ", part['ManufacturerPartNumber'], " | Mouser PN: ", part['MouserPartNumber'], " | Description:", part['Description'])
                    # print("  ")
                    parts_data.append([
                        part['ManufacturerPartNumber'], 
                        part['Description'],
                        part['Category'],
                        part['Manufacturer'],
                        part['LifecycleStatus'],
                        part['LeadTime'],
                        part['ROHSStatus'],
                        part['SuggestedReplacement'],
                        part['ProductCompliance'],
                        part['ProductAttributes'],
                        ])
                    failures = 0
                    
            else: 
                print("No response")  
                continue
        except Exception as e:
            if failures == 3:
                st.error(f"Error: {e}")
                break
            print(f"Error: {e}")
            failures += 1

        progress_bar.progress((i + 1) / total_groups)


st.set_page_config(
    page_title="Mouser API Request Tool",
    page_icon="🐭",
    layout="centered",
    menu_items={
        'About': "Contact Ben Dibuz in PERL for support."
    }
)

st.title("🐭 Mouser API Request Tool")
with st.container(border=True):
    st.subheader("About")
    st.write("This tool can be used to request data from Mouser for a list of MPNs. You will need an API Key from Mouser, which is free to get, and will allow you to request up to 10,000 MPNs per 24 hours.")
    st.subheader("Instructions")
    st.write("Upload a csv with the list of MPNs in the first column and no column header")
    st.write("You can run at most 10,000 MPNs in 24 hours with one API key")
    st.write("If you are running the file in batches, use the start and stop index (starting at 0 for line 1) to set the range of MPNs in the file to be requested")



input_file = st.file_uploader("", type="csv")

if input_file:
    with st.container(border=True):
        API_KEY = st.text_input(label="Mouser API Key", placeholder="Mouser API Key")
        st.link_button("Get a key", url="https://www.mouser.com/api-search/#signup", use_container_width=True)
        limit_rows = st.toggle("Limit range of input rows read", value=True)
        start_row = st.number_input("Start index for MPN list", step=1, min_value=0, help="Use this if you need to start at a certain row of the input file, for example when batching a large list")
        stop_row = st.number_input("Stop index for MPN list", step=1, min_value=0, help="Use this if you need to start at a certain row of the input file, for example when batching a large list", value=9999)
        MOUSER_API_URL = 'https://api.mouser.com/api/v1.0/search/partnumber?apiKey={}'.format(API_KEY)

        mpns = read_mpn_csv(input_file)
        grouped_mpn_strings = group_mpns(mpns, low=start_row, high=stop_row, limit_rows = limit_rows)
        string_df = pd.DataFrame(grouped_mpn_strings, columns=['MPN Group Preview'])
        st.dataframe(string_df, use_container_width=True, hide_index=True)

        parts_data = []

    if st.button("▶️ Run Request", use_container_width=True):
        if len(API_KEY) > 30:        
            process_list(grouped_mpn_strings)
            if len(parts_data) == 0:
                st.error("Failed to fetch results")
            else:
                df = pd.DataFrame(parts_data, columns=[
                    'MPN',
                    'Description',
                    'Category',
                    'Manufacturer',
                    'Lifecycle Status',
                    'Lead Time',
                    'ROHSStatus',
                    'SuggestedReplacement',
                    'ProductCompliance',
                    'ProductAttributes',
                    ])

                st.write("Results sample (first 10)")
                st.dataframe(df.head(10))

                data_output = df.to_csv(index=False)
                st.download_button("Download Results", data_output, file_name="output_data.csv")
        else:
            st.error("Please enter an API key to continue")