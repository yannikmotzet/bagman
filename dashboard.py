import streamlit as st
import pandas as pd
import numpy as np
import sqlite3

MANDATORY_COLUMNS = ['datetime']
IGNORED_COLUMNS = ['timestamp']
DATABASE = "pv_minutes.db"
DATABASE_TABLE = "2024-01"
MAX_CATEGORIES = 10

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


def main():
    st.set_page_config(
        page_title="bagman",
        page_icon="🛍️",
        layout = "wide",
        initial_sidebar_state="collapsed",
    )
    st.title('bagman')

    data = load_database(DATABASE, DATABASE_TABLE)
    num_total_data = len(data)
    columns = data.columns.tolist()

    st_filter_object = st.sidebar
    # st_filter_object = st.container()

    st_metric_number_results = st_filter_object.metric("number results", num_total_data, border=False)

    # filter option to add/remove optional columns (alternative: st.pills, st.segmented_control with selection_mode="multi")
    selectable_columns = [col for col in columns if col not in MANDATORY_COLUMNS]
    default_columns = [c for c in selectable_columns if c not in IGNORED_COLUMNS]
    selected_columns = st_filter_object.multiselect("Select columns", options=selectable_columns, default=default_columns)

    # select selected columns
    data = data[MANDATORY_COLUMNS + selected_columns]

    for column in columns:
        if column not in selected_columns + MANDATORY_COLUMNS:
            continue
        if column in IGNORED_COLUMNS:
            continue
        if data.empty:
            continue
        
        # categorial data
        unique_values = data[column].unique().tolist()
        if len(unique_values) <= MAX_CATEGORIES or data[column].dtype == object:
            # TODO sort values
            filter_categories = st_filter_object.segmented_control(f'Filter {column}', options=unique_values, default=unique_values, selection_mode="multi", key=f"{column}")
            if filter_categories:
                data = data[data[column].isin(filter_categories)]
            else:
                data = data.iloc[0:0]  # return empty DataFrame
            continue
        
        # datetime column
        if np.issubdtype(data[column].dtype, np.datetime64):
            min_date = data[column].min().date()
            max_date = data[column].max().date()
            filter_date = st_filter_object.date_input(f"Filter {column}", (min_date, max_date), min_value=min_date, max_value=max_date, format="YYYY-MM-DD", key=f"{column}")
            if len(filter_date) == 2:
                data = data[(data[column].dt.date >= filter_date[0]) & (data[column].dt.date <= filter_date[0])]
            continue

        # numerical data
        if np.issubdtype(data[column].dtype, np.number):
            min_val = data[column].min()
            max_val = data[column].max()
            filter_data = st_filter_object.slider(f'Filter {column}', min_val, max_val, (min_val, max_val), key=f"{column}")
            data = data[(data[column] >= filter_data[0]) & (data[column] <= filter_data[1])]
            continue

    st_metric_number_results.metric("number results", len(data))

    # if st_filter_object.button("Reset Filters"):
    #     for key in st.session_state.keys():
    #         del st.session_state[key]
    #     st.rerun()

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