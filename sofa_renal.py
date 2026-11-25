import pandas as pd


def calculate_sofa_renal(
    creatinine_path,
    urine_path,
    output_path,
    admissions_path=None,
    aggregation_window=1,
    method="worst",
    urine_window=24,
):
    """Calculate renal SOFA from creatinine and precomputed rolling urine volumes."""

    if (
        isinstance(aggregation_window, bool)
        or not isinstance(aggregation_window, int)
        or aggregation_window < 1
    ):
        raise ValueError("aggregation_window must be a positive integer.")

    if method not in {"worst", "mean"}:
        raise ValueError("method must be 'worst' or 'mean'.")

    if isinstance(urine_window, bool) or urine_window not in {6, 8, 12, 24}:
        raise ValueError("urine_window must be 6, 8, 12, or 24.")

    if admissions_path is None:
        raise ValueError("admissions_path is required for all window sizes.")

    admissions = pd.read_csv(
        admissions_path,
        usecols=["subject_id", "admission_number", "admittime", "starttime", "endtime"],
        dtype={"subject_id": "string", "admission_number": "Int64"},
    )

    for column in ("admittime", "starttime", "endtime"):
        admissions[column] = (
            pd.to_datetime(admissions[column], errors="raise")
            .dt.floor("h")
            .astype("datetime64[ns]")
        )

    if admissions.isna().any().any():
        raise ValueError("Admission identifiers and timestamps must not be missing.")

    if admissions["endtime"].lt(admissions["starttime"]).any():
        raise ValueError("Admission endtime must not precede starttime.")

    admissions = admissions.drop_duplicates().reset_index(drop=True)
    if admissions.duplicated(["subject_id", "admission_number"]).any():
        raise ValueError("Each subject/admission_number must identify one admission interval.")

    urine_column = f"urine_{urine_window}h"

    creatinine = pd.read_csv(
        creatinine_path,
        usecols=["subject_id", "charttime", "value"],
        dtype={"subject_id": "string"},
    )
    urine = pd.read_csv(
        urine_path,
        usecols=["subject_id", "charttime", urine_column],
        dtype={"subject_id": "string"},
    ).rename(columns={urine_column: "value"})

    # Exclude unknown subjects and ignore missing measurement values.
    for frame in (creatinine, urine):
        frame["value"] = pd.to_numeric(frame["value"], errors="raise")

    creatinine = creatinine.loc[
        creatinine["subject_id"].isin(admissions["subject_id"])
        & creatinine["value"].notna()
    ].copy()
    urine = urine.loc[
        urine["subject_id"].isin(admissions["subject_id"])
        & urine["value"].notna()
    ].copy()

    for frame in (creatinine, urine):
        frame["charttime"] = (
            pd.to_datetime(frame["charttime"], errors="raise")
            .dt.floor("h")
            .astype("datetime64[ns]")
        )
        if frame[["subject_id", "charttime"]].isna().any().any():
            raise ValueError("subject_id and charttime must not be missing.")

    creatinine["_item"] = "creatinine"
    urine["_item"] = "urine"
    df = pd.concat([creatinine, urine], ignore_index=True)

    output_columns = ["subject_id", "admission_number", "charttime", "sofa_renal"]
    if df.empty:
        return pd.DataFrame(columns=output_columns)

    # Match observations to admission intervals for every window size.
    # If hourly rounding creates a shared boundary, prefer the latest start.
    df = pd.merge_asof(
        df.sort_values("charttime", kind="stable"),
        admissions.sort_values("starttime", kind="stable"),
        by="subject_id",
        left_on="charttime",
        right_on="starttime",
        direction="backward",
        allow_exact_matches=True,
    )
    df = df.loc[df["charttime"].le(df["endtime"])].copy()

    # Determine urine eligibility separately for each matched admission.
    admission_keys = ["subject_id", "admission_number"]
    eligible_admissions = df.loc[
        df["_item"].eq("creatinine") & df["value"].ge(2),
        admission_keys,
    ].drop_duplicates()
    urine_eligible = pd.MultiIndex.from_frame(df[admission_keys]).isin(
        pd.MultiIndex.from_frame(eligible_admissions)
    )
    df = df.loc[df["_item"].ne("urine") | urine_eligible].copy()

    if df.empty:
        return pd.DataFrame(columns=output_columns)

    if aggregation_window > 1:
        # Align windows to the admittime of the matched admission.
        window = pd.Timedelta(hours=aggregation_window)
        window_number = (df["charttime"] - df["admittime"]) // window
        df["charttime"] = (
            df["admittime"]
            + pd.to_timedelta(
                window_number * aggregation_window,
                unit="h",
            )
        )

    group_columns = [
        "subject_id",
        "admission_number",
        "charttime",
        "_item",
    ]

    if method == "mean":
        # Average available observations separately for each measurement type.
        # Urine values are already rolling volumes, so do not sum them again.
        aggregated = (
            df.groupby(group_columns, as_index=False)["value"]
            .mean()
        )
    else:
        # Higher creatinine and lower urine volume represent worse function.
        aggregated = (
            df.groupby(group_columns, as_index=False)
            .agg(
                minimum=("value", "min"),
                maximum=("value", "max"),
            )
        )
        aggregated["value"] = aggregated["maximum"].where(
            aggregated["_item"].eq("creatinine"),
            aggregated["minimum"],
        )

    # Keep separate admissions distinct when constructing window-level values.
    result = (
        aggregated.pivot(
            index=["subject_id", "admission_number", "charttime"],
            columns="_item",
            values="value",
        )
        .reindex(columns=["creatinine", "urine"])
        .reset_index()
    )
    result.columns.name = None

    # Creatinine thresholds assume mg/dL.
    result["sofa_renal"] = 0
    result.loc[result["creatinine"].ge(1.2), "sofa_renal"] = 1
    result.loc[result["creatinine"].ge(2), "sofa_renal"] = 2
    result.loc[result["creatinine"].ge(3.5), "sofa_renal"] = 3
    result.loc[result["creatinine"].ge(5), "sofa_renal"] = 4

    # Scale urine thresholds in mL to the selected rolling duration.
    threshold_3 = 500 * urine_window / 24
    threshold_4 = 200 * urine_window / 24

    # Retain the higher score contributed by creatinine or urine output.
    result.loc[
        result["urine"].lt(threshold_3) & result["sofa_renal"].lt(3),
        "sofa_renal",
    ] = 3
    result.loc[result["urine"].lt(threshold_4), "sofa_renal"] = 4

    # Omit normal windows and do not create windows without observations.
    output = (
        result.loc[result["sofa_renal"].gt(0), output_columns]
        .sort_values(["subject_id", "admission_number", "charttime"])
        .reset_index(drop=True)
    )
    output.to_csv(output_path, index=False)

    return output

if __name__ == "__main__":
    calculate_sofa_renal('creatinine.csv', 'hourly_urine.csv', 'sofa_renal_1_worst_u12.csv',
                         '../repo_label_m4_public/admissions_merged.csv',
                         aggregation_window=1, method="worst", urine_window=12)