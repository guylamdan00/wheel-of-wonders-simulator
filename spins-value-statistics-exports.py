#@title Spins Value Statistics and Exports
import math

# Calculate spins_value per by level and include percentiles
percentile_spins_value_per_level = score_data_filtered.groupby('level')['spins_value'].agg(['mean', 'median', lambda x: x.quantile(0.75), lambda x: x.quantile(0.90), lambda x: x.quantile(0.95)]).reset_index()
percentile_spins_value_per_level.rename(columns={'<lambda_0>': '75th_percentile', '<lambda_1>': '90th_percentile', '<lambda_2>': '95th_percentile'}, inplace=True)


# print("\n Average Spins Value Per Spin by Level with Percentiles:")
# display(percentile_spins_value_per_level)

# ------------------ Spins Value per Spin by Level Table --------------------

# Calculate spins_value per spin by level and include percentiles
percentile_spins_value_per_spin = score_data_filtered.groupby(['level', 'spin'])['spins_value'].agg(['mean', 'median', lambda x: x.quantile(0.75), lambda x: x.quantile(0.90), lambda x: x.quantile(0.95)]).reset_index()
percentile_spins_value_per_spin.rename(columns={'<lambda_0>': '75th_percentile', '<lambda_1>': '90th_percentile', '<lambda_2>': '95th_percentile'}, inplace=True)

# print("\n Spins Value Per Spin by Level with Percentiles:")
# display(percentile_spins_value_per_spin)

# --------------- Cumulative Spins and Cumulative Spins Value per Player ------------------------
# Sort data by player_id and spin to ensure correct cumulative calculation
score_data_filtered_sorted = score_data_filtered.sort_values(['player_id', 'level','spin']).copy()

# Calculate cumulative spins per player
score_data_filtered_sorted['cumulative_spins'] = score_data_filtered_sorted.groupby('player_id').cumcount() + 1

# Calculate cumulative spins value per player
score_data_filtered_sorted['cumulative_spins_value'] = score_data_filtered_sorted.groupby('player_id')['spins_value'].cumsum()

# ------------------------ Cumulative Spins Value by Percentiles per Cumulative Spins Table --------------------------------------

# Calculate cumulative_spins_value by percentiles for each cumulative spin
cumulative_spins_value_percentiles_table = score_data_filtered_sorted.groupby('cumulative_spins')['cumulative_spins_value'].agg([
    'mean', 'median', lambda x: x.quantile(0.25), lambda x: x.quantile(0.75), lambda x: x.quantile(0.90), lambda x: x.quantile(0.95)
]).reset_index()

cumulative_spins_value_percentiles_table.rename(columns={
    '<lambda_0>': '25th_percentile',
    '<lambda_1>': '75th_percentile',
    '<lambda_2>': '90th_percentile',
    '<lambda_3>': '95th_percentile'
}, inplace=True)

# print("\n Cumulative Spins Value by Percentiles per Cumulative Spins:")
# display(cumulative_spins_value_percentiles_table)

# ---------- Overall Spins Value by Percentiles Table -------------------
# Calculate overall percentiles for spins_value
overall_spins_value_percentiles = score_data_filtered['spins_value'].agg({
    'mean': 'mean',
    'median': 'median',
    '25th_percentile': lambda x: x.quantile(0.25),
    '75th_percentile': lambda x: x.quantile(0.75),
    '90th_percentile': lambda x: x.quantile(0.90),
    '95th_percentile': lambda x: x.quantile(0.95),
}).reset_index()

# Rename the columns to the desired percentile names
overall_spins_value_percentiles.rename(columns={
    'index': 'Statistic',
    '<lambda_0>': '25th_percentile',
    '<lambda_1>': '75th_percentile',
    '<lambda_2>': '90th_percentile',
    '<lambda_3>': '95th_percentile'
}, inplace=True)

# Transpose the table for better readability
overall_spins_value_percentiles_transposed = overall_spins_value_percentiles.set_index('Statistic').T


# print("\n Overall Spins Value by Percentiles:")
# display(overall_spins_value_percentiles_transposed)

# --------------------- Spins Value by Percentiles per Cumulative Spins ---------------------------------------

# Calculate spins_value by percentiles for each cumulative spin
marginal_spins_value = score_data_filtered_sorted.groupby('cumulative_spins')['spins_value'].agg([
    'mean', 'median', lambda x: x.quantile(0.25), lambda x: x.quantile(0.75), lambda x: x.quantile(0.90), lambda x: x.quantile(0.95)
]).reset_index()

marginal_spins_value.rename(columns={
    '<lambda_0>': '25th_percentile',
    '<lambda_1>': '75th_percentile',
    '<lambda_2>': '90th_percentile',
    '<lambda_3>': '95th_percentile'
}, inplace=True)

# print("\n Spins Value by Percentiles per Cumulative Spins:")
# display(cumulative_spins_value_percentiles)

# --------- Wedge Reward Data by Spin and Level (Player Distribution %) ----------

# Group by level, spin, and wedge_reward and count players
wedge_reward_counts = score_data_filtered.groupby(['level', 'spin', 'wedge_number', 'wedge_reward', 'wedge_reward_amount']).size().reset_index(name='player_count')

# Calculate total players per level and spin
total_players_per_spin = wedge_reward_counts.groupby(['level', 'spin'])['player_count'].transform('sum')

# Calculate percentage of players for each wedge_reward per spin and level
wedge_reward_counts['player_percentage'] = (wedge_reward_counts['player_count'] / total_players_per_spin) * 100

# Pivot the data for the heatmap
# Keep the multi-index columns as they are needed for the desired axis layout
heatmap_data = wedge_reward_counts.pivot_table(index='spin', columns=['level','wedge_number','wedge_reward', 'wedge_reward_amount'], values='player_percentage').fillna(0)

print("\n Wedge Reward Heatmap by Spin and Level (Player Distribution %):")

def _flatten_columns(cols):
    """
    Flattens simple or MultiIndex columns into strings.
    """
    if isinstance(cols, pd.MultiIndex):
        flat = []
        for tpl in cols:
            # Join non-empty parts with ' | '
            parts = [str(x) for x in tpl if str(x) not in ("", "None")]
            flat.append(" | ".join(parts) if parts else "")
        return flat
    else:
        return [str(c) for c in cols]

def _df_to_values(df: pd.DataFrame, include_index=True):
    """
    Convert a DataFrame to a 2D list suitable for gspread.update().
    - Flattens MultiIndex columns
    - Optionally includes index as the first column (named)
    """
    if include_index:
        # Preserve index as a column (name if available, else "index")
        idx_name = df.index.name if df.index.name not in (None, "", "None") else "index"
        df_out = df.reset_index()
    else:
        df_out = df.copy()

    # Flatten columns
    df_out.columns = _flatten_columns(df_out.columns)

    # Replace NaNs with empty strings for Sheets
    values = df_out.where(pd.notnull(df_out), "").values.tolist()
    header = list(df_out.columns)
    return [header] + values

def _get_or_create_ws(sh, title, nrows, ncols):
    """
    Get a worksheet by title or create it. Ensures it is at least (nrows x ncols).
    """
    try:
        ws = sh.worksheet(title)
        # Clear existing content
        ws.clear()
        # Ensure size fits (Sheets needs at least 1x1)
        nrows = max(1, nrows)
        ncols = max(1, ncols)
        ws.resize(rows=nrows, cols=ncols)
        return ws
    except gspread.exceptions.WorksheetNotFound:
        # Sheets API needs at least 1x1 to create. We'll create small then resize if needed.
        ws = sh.add_worksheet(title=title, rows=max(1, nrows), cols=max(1, ncols))
        return ws

def export_tables_to_sheet(tables: dict[str, pd.DataFrame],
                           sheet_key: str,
                           gc_client,
                           include_index=True):
    """
    Export each DataFrame to a separate tab (worksheet).
    If the tab exists: clear + overwrite. Else: create it.
    Tab name = dict key.
    """
    # Open target spreadsheet once
    sh = gc_client.open_by_key(sheet_key)

    for name, df in tables.items():
        if not isinstance(df, pd.DataFrame):
            print(f"[SKIP] {name} is not a DataFrame.")
            continue

        # Convert DF to values for Sheets
        values = _df_to_values(df, include_index=include_index)

        # Determine needed size
        nrows = len(values)
        ncols = max((len(r) for r in values), default=1)

        # Get or create worksheet, clear it, ensure size, then upload
        ws = _get_or_create_ws(sh, name, nrows, ncols)
        ws.update(values, range_name="A1")
        print(f"\n ✅ Exported '{name}' to tab '{name}' ({nrows}x{ncols}).")

# ---- Call it with the tables you displayed in your cell ----
tables_to_export = {
    "Overall Spins Value by Percentile": overall_spins_value_percentiles_transposed,
    "Spins Value by Percentile per Level": percentile_spins_value_per_level,
    "Spins Value by Percentile per Level per Spin": percentile_spins_value_per_spin,
    "Margial Spin Value by Percentile per Spin": marginal_spins_value,
    "Cumulative Spin Value by Percentile per Spin": cumulative_spins_value_percentiles_table,
    "Player Dist by Wedge Reward per Spin per Level": heatmap_data  # MultiIndex columns flattened as "level | wedge_number | wedge_reward | wedge_reward_amount"
}

export_tables_to_sheet(tables_to_export, SHEET_KEY, gc, include_index=True)

