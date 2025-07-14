import asyncio
import os
from uuid import UUID

import pandas as pd
import streamlit as st
from prefect.client.orchestration import get_client

from bagman.utils import bagman_utils
from bagman.utils.db import BagmanDB
from dashboard_pages import dashboard_utils

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "..", "config.yaml")


async def check_connection():
    async with get_client() as client:
        try:
            response = await client.hello()
            return response.status_code == 200
        except Exception:
            return False


async def get_prefect_deployments():
    deployments = []
    async with get_client() as client:
        try:
            response = await client.read_deployments()

            for deployment in response:
                deployments.append(
                    {
                        "deployment_id": str(deployment.id),
                        "flow_id": str(deployment.flow_id),
                        "entrypoint": deployment.entrypoint,
                        "name": deployment.name,
                        "parameters": deployment.parameter_openapi_schema["properties"]
                        if deployment.parameter_openapi_schema
                        else {},
                    }
                )

            df = pd.DataFrame(deployments)
            return df

        except Exception as e:
            print(f"Error connecting to Prefect server: {e}")
            print("Ensure the PREFECT_API_URL is correct and the server is running.")


async def list_flow_runs(start_time=None):
    flow_run_data = []

    async with get_client() as client:
        try:
            # Optionally filter by time range (e.g., last 7 days)
            # start_time = datetime.utcnow() - timedelta(days=7)
            # flow_runs = await client.read_flow_runs(
            # flow_run_filter=dict(
            #     start_time=dict(after=start_time)
            # )

            runs = await client.read_flow_runs()

            for run in runs:
                duration = None
                if run.start_time and run.end_time:
                    duration = (
                        run.end_time - run.start_time
                    ).total_seconds() / 60.0  # minutes
                flow_run_data.append(
                    {
                        "run_id": str(run.id),
                        "run name": run.name,
                        "flow id": str(run.flow_id),
                        "parameters": run.parameters,
                        "state": run.state_name,
                        "start_time": run.start_time,
                        "end_time": run.end_time,
                        "duration": duration,
                    }
                )

            df = pd.DataFrame(flow_run_data)
            return df

        except Exception as e:
            print(f"Error connecting to Prefect server: {e}")
            print("Ensure the PREFECT_API_URL is correct and the server is running.")


async def trigger_flow_run(deployment_id: UUID, parameters: dict = {}):
    async with get_client() as client:
        flow_run = await client.create_flow_run_from_deployment(
            deployment_id=deployment_id,
            parameters=parameters or {},
        )
        if flow_run is None:
            raise RuntimeError(
                f"Flow run could not be created for deployment {deployment_id}"
            )

        return flow_run


def main():
    st.header("Jobs")

    # config prefect connection
    try:
        config = bagman_utils.load_config(CONFIG_PATH)
    except Exception as e:
        st.error(f"Error loading config: {e}")
        st.stop()

    if "prefect_api_url" in config.keys():
        os.environ["PREFECT_API_URL"] = config["prefect_api_url"]
    else:
        st.error(
            "Prefect API URL not found in config. Please check your configuration."
        )
        st.stop()

    # check prefect connection
    result = asyncio.run(check_connection())
    if not result:
        st.error(f"Error connecting to Prefect server: {result['error']}")
        st.stop()

    # overview of running and finished jobs
    st.subheader("Job Overview")
    try:
        runs = asyncio.run(list_flow_runs())
        st.dataframe(
            runs,
            use_container_width=True,
            height=250,
            hide_index=True,
            on_select="ignore",
        )
    except Exception as e:
        st.error(f"Error fetching runs: {e}")

    # allow user to trigger a flow run
    st.subheader("Start Job")
    try:
        with st.spinner("Connecting to database..."):
            # the abspath check is required to use the recordings_example.json which has a relative path
            if config["database_type"] == "json":
                database_path = config["database_uri"]
                if not os.path.isabs(database_path):
                    database_path = os.path.join(PROJECT_ROOT, database_path)
                db = BagmanDB(
                    config["database_type"], database_path, config["database_name"]
                )
            else:
                db = BagmanDB(
                    config["database_type"],
                    config["database_uri"],
                    config["database_name"],
                )
            data = dashboard_utils.load_recordings(db, config)
    except Exception:
        st.error("⚠️ no connection to database")
        return

    # filter data based on search query
    search_query = st.text_input("Search", "")
    if search_query:
        data = data[
            data.apply(
                lambda row: row.astype(str)
                .str.contains(search_query, case=False)
                .any(),
                axis=1,
            )
        ]

    event = st.dataframe(
        data,
        use_container_width=True,
        height=250,
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row",
    )
    selected_recs = event.selection.rows

    try:
        deployments = asyncio.run(get_prefect_deployments())
    except Exception as e:
        st.error(f"Error fetching flows: {e}")
        st.stop()

    # checkbox for each deployment
    selected_deployments = []
    for index, row in deployments.iterrows():
        deployment_id = row["deployment_id"]
        deployment_name = row["name"]
        if st.checkbox(f"{deployment_name}"):
            selected_deployments.append(row)

    # trigger flows if button is clicked
    if st.button("Start flows"):
        if not selected_deployments:
            st.warning("No flows selected.")
        elif len(selected_recs) == 0:
            st.warning("No recordings selected.")
        else:
            st.info("Starting selected flows...")

            for i in range(len(selected_recs)):
                rec_name = data.iloc[selected_recs[i]]["name"]

                for deployment in selected_deployments:
                    try:
                        deployment_id = UUID(deployment["deployment_id"])
                        deployment_name = deployment["name"]

                        # TODO check parameter
                        flow_run = asyncio.run(
                            trigger_flow_run(
                                deployment_id,
                                parameters={
                                    "recording_name": rec_name,
                                    "config_file": CONFIG_PATH,
                                },
                            )
                        )
                        st.success(
                            f"✅ Started flow `{deployment_name}` — FlowRun ID: `{flow_run.id}`"
                        )
                    except Exception as e:
                        st.error(f"Failed to start {row['name']}: {e}")


if __name__ == "__main__":
    main()
