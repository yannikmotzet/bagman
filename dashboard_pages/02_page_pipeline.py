import asyncio
import os
from datetime import datetime
from uuid import UUID

import pandas as pd
import streamlit as st
# the flow import is a prefect workaround to suppress error (https://linen.prefect.io/t/23222690/hi-all-i-m-overhauling-our-current-prefect-2-19-1-to-prefect)
from prefect import flow  # noqa: F401
from prefect.client.orchestration import get_client

from bagman.utils.db import BagmanDB
from dashboard_pages import dashboard_utils

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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


async def get_prefect_flows():
    flows = []
    async with get_client() as client:
        try:
            response = await client.read_flows()

            for f in response:
                flows.append(
                    {
                        "flow_id": str(f.id),
                        "name": f.name,
                    }
                )

            df = pd.DataFrame(flows)
            return df

        except Exception as e:
            print(f"Error connecting to Prefect server: {e}")
            print("Ensure the PREFECT_API_URL is correct and the server is running.")


async def get_prefect_runs(start_time=None, deployments=None):
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
                deployment = str(run.deployment_id)
                if deployments is not None:
                    for index, row in deployments.iterrows():
                        if row["deployment_id"] == str(run.deployment_id):
                            deployment = row["name"]

                flow_run_data.append(
                    {
                        # "run_id": str(run.id),
                        "run": run.name,
                        "deployment": deployment,
                        "recording_name": run.parameters.get("recording_name", "N/A"),
                        "state": run.state_name,
                        "created": run.created,
                        # "start_time": run.start_time,
                        # "end_time": run.end_time,
                        "run_time": run.estimated_run_time,
                        "url": f'{st.session_state["config"]["prefect_api_url"].replace("/api", "")}/runs/flow-run/{run.id}',
                    }
                )

            df = pd.DataFrame(flow_run_data)
            df = df.sort_values(by="created", ascending=False)

            # convert to local timezone
            timezone = datetime.now().astimezone().tzinfo
            df["created"] = df["created"].dt.tz_convert(timezone).dt.tz_localize(None)

            # fix the issue of timedelta64[ns] not being displayed as real value
            df["run_time"] = df["run_time"].apply(
                lambda x: (
                    str(x)
                    if pd.isnull(x)
                    else f"{int(x.total_seconds() // 3600):02}:{int((x.total_seconds() % 3600) // 60):02}:{int(x.total_seconds() % 60):02}"
                )
            )

            return df

        except Exception as e:
            print(f"Error connecting to Prefect server: {e}")
            print("Ensure the PREFECT_API_URL is correct and the server is running.")


async def create_prefect_run(deployment_id: UUID, parameters: dict = {}):
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


@st.fragment
def show_runs(deployments):
    st.button("🔄 Refresh")
    runs = asyncio.run(get_prefect_runs(deployments=deployments))

    if runs is None:
        st.info("No runs found.")
    else:
        for index, row in runs.iterrows():
            if row["state"] == "Completed":
                runs.at[index, "state"] = "✅ Completed"
            elif row["state"] == "Failed":
                runs.at[index, "state"] = "❌ Failed"
            elif row["state"] == "Crashed":
                runs.at[index, "state"] = "❌ Crashed"
            elif row["state"] == "Cancelled":
                runs.at[index, "state"] = "🚫 Cancelled"
            elif row["state"] == "Running":
                runs.at[index, "state"] = "🏃 Running"
            elif row["state"] == "Late":
                runs.at[index, "state"] = "⏳ Late"
            else:
                runs.at[index, "state"] = f"❓ {row['state']}"

        st.dataframe(
            runs,
            use_container_width=True,
            height=150,
            hide_index=True,
            on_select="ignore",
            column_config={
                "url": st.column_config.LinkColumn(
                    "url", display_text=r".*/([0-9a-fA-F-]{36})$"
                )
            },
        )


def main():
    st.header("Pipeline")

    if "prefect_api_url" in st.session_state["config"].keys():
        os.environ["PREFECT_API_URL"] = st.session_state["config"]["prefect_api_url"]
    else:
        st.error(
            "Prefect API URL not found in config. Please check your configuration."
        )
        st.stop()

    # check prefect connection
    result = asyncio.run(check_connection())
    if not result:
        st.error("Error connecting to Prefect server.")
        st.stop()

    # get available deployments
    try:
        deployments = asyncio.run(get_prefect_deployments())
    except Exception as e:
        st.error(f"Error fetching flows: {e}")
        st.stop()

    # overview of runs
    st.subheader("All Runs")

    try:
        show_runs(deployments)
    except Exception as e:
        st.error(f"Error fetching runs: {e}")

    # allow user to trigger a run
    st.subheader("Start Run")
    try:
        with st.spinner("Connecting to database..."):
            # the abspath check is required to use the recordings_example.json which has a relative path
            if st.session_state["config"]["database_type"] == "json":
                database_path = st.session_state["config"]["database_uri"]
                if not os.path.isabs(database_path):
                    database_path = os.path.join(PROJECT_ROOT, database_path)
                db = BagmanDB(
                    st.session_state["config"]["database_type"],
                    database_path,
                    st.session_state["config"]["database_name"],
                )
            else:
                db = BagmanDB(
                    st.session_state["config"]["database_type"],
                    st.session_state["config"]["database_uri"],
                    st.session_state["config"]["database_name"],
                )
            data = dashboard_utils.load_recordings(db, st.session_state["config"])
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
        height=200,
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
    st.markdown("Select deployments to run:")
    for index, row in deployments.iterrows():
        deployment_name = row["name"]
        if st.checkbox(f"{deployment_name}"):
            selected_deployments.append(row)

    # trigger flows if button is clicked
    if st.button("Start run"):
        if not selected_deployments:
            st.warning("No deployments selected.")
        elif len(selected_recs) == 0:
            st.warning("No recordings selected.")
        else:
            with st.spinner("Starting selected deployments..."):
                for i in range(len(selected_recs)):
                    rec_name = data.iloc[selected_recs[i]]["name"]

                    for deployment in selected_deployments:
                        try:
                            deployment_id = UUID(deployment["deployment_id"])
                            deployment_name = deployment["name"]

                            if not list(deployment["parameters"].keys()) == [
                                "recording_name",
                                "config_file",
                            ]:
                                st.warning(
                                    f"Deployment {deployment_name} has unexpected parameters: {deployment['parameters'].keys()}. Expected parameters are 'recording_name' and 'config_file'. Skipping."
                                )
                                continue

                            flow_run = asyncio.run(
                                create_prefect_run(
                                    deployment_id,
                                    parameters={
                                        "recording_name": rec_name,
                                        "config_file": st.session_state["config_path"],
                                    },
                                )
                            )
                            st.success(
                                f"✅ Started flow `{deployment_name}` for recording `{rec_name}` — Run ID: `{flow_run.id}` — Run Name: `{flow_run.name}`"
                            )

                        except Exception as e:
                            st.error(f"Failed to start {row['name']}: {e}")


if __name__ == "__main__":
    main()
