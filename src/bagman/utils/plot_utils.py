import numpy as np
import pandas as pd
import plotly.express as px


def plot_map(positions, output_file, color_map="matter"):
    if len(positions) == 0:
        return

    # convert positions to DataFrame
    df = pd.DataFrame(positions)
    df["time"] = df["stamp"] - df["stamp"].iloc[0]

    # auto-zoom inspired by: https://stackoverflow.com/a/65043576
    max_bound = (
        max(
            abs(max(df["longitude"]) - min(df["longitude"])),
            abs(max(df["latitude"]) - min(df["latitude"])),
        )
        * 111
    )
    if np.log(max_bound) > 0:
        zoom = -0.04 * max_bound + 16 - np.log(max_bound)
    else:
        zoom = 16
    center = {
        "lat": min(df["latitude"]) + (max(df["latitude"]) - min(df["latitude"])) / 2,
        "lon": min(df["longitude"]) + (max(df["longitude"]) - min(df["longitude"])) / 2,
    }

    if "speed" in df.columns:
        map_figure = px.scatter_mapbox(
            df,
            lat="latitude",
            lon="longitude",
            color="speed",
            hover_data=df.columns,
            mapbox_style="open-street-map",
            zoom=zoom,
            center=center,
            color_continuous_scale=color_map,
        )
    else:
        map_figure = px.scatter_mapbox(
            df,
            lat="latitude",
            lon="longitude",
            hover_data=df.columns,
            mapbox_style="open-street-map",
            zoom=zoom,
            center=center,
        )

    map_figure.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    map_figure.write_html(output_file, config={"scrollZoom": True})
