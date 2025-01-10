import streamlit as st
import pandas as pd
import numpy as np
from datetime import date
import sqlite3

DATE_COLUMN = 'date/time'
# MANDATORY_COLUMNS = ['date/time']
MANDATORY_COLUMNS = ['timestamp']
DATA_URL = ('https://s3-us-west-2.amazonaws.com/'
         'streamlit-demo-data/uber-raw-data-sep14.csv.gz')
DATABASE = "pv_minutes.db"
DATABASE_TABLE = "2024-01"
MAX_CATEGORIES = 10

@st.cache_data
def load_data(nrows):
    data = pd.read_csv(DATA_URL, nrows=nrows)
    lowercase = lambda x: str(x).lower()
    data.rename(lowercase, axis='columns', inplace=True)
    data[DATE_COLUMN] = pd.to_datetime(data[DATE_COLUMN])
    return data

@st.cache_data
def load_database(database, table):
    conn = sqlite3.connect(database)
    cursor = conn.execute(f"PRAGMA table_info('{table}')")
    columns = [info[1] for info in cursor.fetchall()]
    if 'timestamp' in columns:
        query = f"SELECT datetime(timestamp, 'unixepoch', 'localtime') as datetime, * FROM '{table}'"
    else:
        query = f"SELECT * FROM '{table}'"
    data = pd.read_sql_query(query, conn)
    if 'timestamp' in columns:
        data["datetime"] = pd.to_datetime(data["datetime"])
    conn.close()
    return data

def get_df_info(df, max_categories=10):
    # TODO in case unique() has less then 10 elements for -> category
    columns = df.columns.tolist()
    filter_info = []
    for column in columns:
        column_type = df[column].dtype
        if np.issubdtype(column_type, np.number):
            min_val = df[column].min()
            max_val = df[column].max()
            filter_info.append({'name': column, 'type': 'number', 'values': [min_val, max_val]})
        elif column_type == str:
            filter_info.append({'name': column, 'type': 'string'})
        elif np.issubdtype(column_type, np.bool_):
            unique_vals = df[column].unique().tolist()
            filter_info.append({'name': column, 'type': 'boolean', 'values': unique_vals})
        elif column_type == str:
            filter_info.append({'name': column, 'type': 'string'})
        elif np.issubdtype(column_type, np.datetime64):
            min_date = df[column].min().date()
            max_date = df[column].max().date()
            filter_info.append({'name': column, 'type': 'datetime', 'values': [min_date, max_date]})
        elif np.issubdtype(column_type, np.timedelta64):
            min_val = df[column].min().date()
            max_val = df[column].max().date()
            filter_info.append({'name': column, 'type': 'timedelta', 'values': [min_val, max_val]})
        elif column_type == object:
            unique_vals = df[column].unique().tolist()
            filter_info.append({'name': column, 'type': 'object', 'values': unique_vals})
        else:
            filter_info.append({'name': column, 'type': 'unknown'})
    return filter_info

def reset_filters(filter_info):
    pass

def main():
    st.set_page_config(
        page_title="dashboard",
        page_icon="🤖",
        layout = "wide",
        initial_sidebar_state="collapsed",
    )
    st.title('dashboard')

    # data = load_data(10000)
    data = load_database(DATABASE, DATABASE_TABLE)
    num_total_data = len(data)
    columns = data.columns.tolist()

    # info about type and values of columns for filtering
    filter_info = get_df_info(data)
 
    with st.sidebar:
        st_metric_number_results = st.metric("number results", num_total_data, border=False)

        # TODO show if filter is applied (e.g. add another metric with number of filtered data), add option to reset

        # filter option to add/remove optional columns (alternative: st.pills, st.segmented_control with selection_mode="multi")
        selectable_columns = [col for col in columns if col not in MANDATORY_COLUMNS]
        selected_columns = st.multiselect("Select columns", options=selectable_columns, default=selectable_columns)

        # add filter option for all columns
        for info in filter_info:
            if info["name"] not in selected_columns + MANDATORY_COLUMNS:
                continue
            if info["type"] == "datetime":
                info["filter"] = st.date_input("Select time frame", (info["values"][0], info["values"][1]), min_value=info["values"][0], max_value=info["values"][1], format="YYYY-MM-DD")
            elif info["type"] == "number":
                info["filter"] = st.slider(f'Select {info["name"]}', info["values"][0], info["values"][1], (info["values"][0], info["values"][1]))
            elif info["type"] == "object":
                info["filter"] = st.segmented_control(f'Select {info["name"]}', options=info["values"], default=info["values"] ,selection_mode="multi")

        if st.button("reset filters"):
            # TODO 
            pass
        st.divider()


    # select selected columns
    data = data[MANDATORY_COLUMNS + selected_columns]

    # apply filters
    for info in filter_info:
        if info["name"] not in selected_columns + MANDATORY_COLUMNS:
            continue
        if info["type"] == "datetime":
            if len(info["filter"]) == 2:
                start_date, end_date = info["filter"]
                data = data[(data[info["name"]].dt.date >= start_date) & (data[info["name"]].dt.date <= end_date)]
        if info["type"] == "number":
            if len(info["filter"]) == 2:
                min_value = info["filter"][0]
                max_value = info["filter"][1]
                data = data[(data[info["name"]] >= min_value) & (data[info["name"]] <= max_value)]
        if info["type"] == "object":
            if info["filter"]:
                data = data[data[info["name"]].isin(info["filter"])]
            else:
                data = data.iloc[0:0]  # return empty DataFrame
                

    st_metric_number_results.metric("number results", len(data))

    event = st.dataframe(
        data,
        use_container_width=True,
        height=600,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    selected_rows = event.selection.rows
    if len(selected_rows) > 0:
        st_selected_people = st.text(f"{selected_rows}")


if __name__ == "__main__":
    main()