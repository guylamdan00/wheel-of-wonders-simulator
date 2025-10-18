# Wheel of Wonders (Pingo Light Wheel) — Simulator & Analysis

A fast, readable, and spreadsheet‑driven simulator for **multi‑level prize wheels** ("Wheel of Wonders"). Built for Google Colab + Google Sheets so designers can iterate on configuration in Sheets while analysts run large‑scale Monte Carlo simulations in Colab.

---

## What this project does

* **Validates** your Google Sheet has all required tabs/columns and basic data hygiene.
* **Simulates** N players progressing through multiple levels of a wheel.
* **Implements rules** for *Level Up* and *Jackpot* wedges (min/max forced spins, masking/forcing behavior).
* **Computes KPI tables** (means, medians, percentiles) by level and spin, plus cumulative trajectories.
* **Exports results** back to the same Google Sheet—each table to its own tab.

---

## Why Sheets + Colab?

* Designers can tweak wheel configs directly in Sheets.
* Analysts can run 100k+ player simulations reproducibly in Colab.
* No local environment setup; only a shareable Sheet and a Colab notebook.

---

## Prerequisites

* A Google account with access to the target Google Sheet (edit permission recommended).
* Google Colab runtime (Python) with internet access to your Sheet.

> **Packages used:** `gspread`, `google.colab`, `google-auth`, `numpy`, `pandas`, `matplotlib`, `ipywidgets` (installed in‑cell). Warnings are suppressed for a clean UX.

---

## Quick Start

1. **Open the Colab notebook** that contains this simulator code.
2. **Set `CONFIG_SHEET_INPUT`** to your Sheet URL *or* the Sheet key.
3. **Run all cells**. On first run, authorize Colab to access your Drive/Sheets.
4. If validation passes, the sim runs and outputs `score_data` + exports summary tables back to your Sheet.

**Tip:** You can paste either a full URL like

```
'sheet key'
```

or just the `<SHEET_KEY>`.

---

## Sheet Schema (Required Tabs & Columns)

The validator ensures your Sheet has the following **tabs** with **headers** (case/spacing normalized automatically):

### 1) `levels config`

* `level`
* `levelup_reward`
* `levelup_reward_amount`
* `levelup_min_spins`
* `levelup_max_spins`
* `wheel_id`

### 2) `jackpot config`

* `jackpot_level`
* `jackpot_reward`
* `jp_reward_amount`
* `jp_min_spins`
* `jp_max_spins`

> **Assumption:** Jackpot parameters are read from `jackpot_level == 1` unless you add your own mapping.

### 3) `wheels config`

* `wheel_id`
* `wedge_number`
* `wedge_reward`
* `wedge_reward_amount`
* `wedge_weight`
* `wedge_type`  (`levelup` | `jackpot` | other)

> **Completeness check:** Rows with a configured `wheel_id` must have values for all other fields. Rows with `wheel_id == 0` or `wedge_number == 0` are dropped.

### 4) `resource valuation`

* `reward`
* `spins_value`

> Used to convert wedge rewards into a normalized **spins_value** metric for comparisons and KPIs.

---

## How the Simulation Works (High‑Level)

* Players start at **level 1** with `spin_index = 1` and `spins_wo_jp = 0`.
* For each level:

  * Pull the associated `wheel_id` and construct the wheel from `wheels config` (ordered by `wedge_number`).
  * Apply **Jackpot rules** first:

    * **Mute** jackpot wedges when `spins_wo_jp < jp_min`.
    * **Force** jackpot at/after `jp_max` (all other weights zeroed for that spin).
  * Apply **Level Up rules** second:

    * **Mute** levelup wedges when `spin_index < levelup_min_spins`.
    * **Force** levelup at/after `levelup_max_spins` (unless a jackpot force already zeroed others).
  * Normalize remaining weights per player and **draw** a wedge.
  * After each spin:

    * If jackpot hit → `spins_wo_jp = 0`, player stays in level (unless also leveled up by design—typically not).
    * If levelup hit → player **exits** this level; on entering the next level, `spin_index` resets to 1.
* Continue until all players finish the last level.

> The draw uses per‑player masked weights with a numerically stable CDF sampler.

---

## Outputs (DataFrames)

* **`score_data`**: One row per player‑spin with full context: `player_id`, `level`, `spin`, `wheel_id`, `wedge_number`, `wedge_type`, `probability`, `spin_result`, plus min/max rule columns and chosen wedge weight.
* **`score_data_filtered`**: Merged with wheel definitions and `resource valuation` to compute `spins_value` for each spin.

### Summary Tables (also exported back to the Sheet)

1. **Overall Spins Value by Percentile** (transposed)
2. **Spins Value by Percentile per Level**
3. **Spins Value by Percentile per Level per Spin**
4. **Marginal Spin Value by Percentile per Spin**
5. **Cumulative Spin Value by Percentile per Cumulative Spins**
6. **Player Distribution by Wedge Reward per Spin per Level** (heatmap‑ready, pivoted with flattened multi‑index)

Tab names match the items above. Existing tabs with the same names are **cleared and overwritten**.

## Interactive Visualizations

These Colab widgets let you slice and explore simulation results without re‑running the model.

### 1) Cumulative Spins Value by Percentiles per Cumulative Spins (Interactive Bar)

**File/code block:** `Cumulative Spins Value by Percentiles per Cumulative Spins Chart`
**What it shows:** For each cumulative spin (x‑axis), the **cumulative spins_value** at a chosen statistic (mean, median, 25th/75th/90th/95th).
**Controls:** Dropdown to pick the statistic.
**Use it for:** Understanding the *trajectory* of value accumulation and how tails (90th/95th) differ from central tendencies.
**Notes:** Adds value labels; grid aids in comparing adjacent spins.

### 2) Spins to Complete by Level per Percentile (Interactive Bar)

**File/code block:** `Spins to Complete by Level per Percentile`
**What it shows:** Distribution summary of **spins required to hit Level Up** at each level: min, max, mean, and 25th/50th/75th percentiles.
**Controls:** Dropdown to select which statistic to visualize.
**Use it for:** Tuning `levelup_min_spins` / `levelup_max_spins` and wedge weights to keep progression bands within targets.
**Notes:** Values are computed from each player’s first `levelup` spin per level.

### 3) Distribution of Players by Spins to Complete Level (Interactive Bar)

**File/code block:** `Distribution of Players by Spins to Complete Level`
**What it shows:** For each level, a **percentage distribution** over the number of spins it took players to complete that level.
**Controls:** Level dropdown with **All** option to compare levels (hue) or focus on one.
**Use it for:** Spotting multi‑modal patterns (e.g., early vs. forced completions) and tail risk at or near `levelup_max_spins`.
**Notes:** Labels include `%`; totals per level sum to ~100%.

### 4) Spins Value per Spin by Level (Interactive Grouped Bar)

**File/code block:** `Spins Value per Spin by Level`
**What it shows:** **spins_value** per spin number, grouped by level, at a chosen statistic (mean/median/75th/90th/95th).
**Controls:** Statistic dropdown + Level filter (**All** or a single level).
**Use it for:** Comparing per‑spin value intensity across levels; confirming whether earlier/later spins are carrying value as expected.
**Notes:** Pivoted to show levels as series; includes bar labels and legend.

### 5) Wedge Reward Heatmap by Spin and Level (Player Distribution %)

**File/code block:** `Wedge Reward Heatmap by Spin and Level (Player Distribution %)`
**What it shows:** A heatmap of **player share (%)** hitting each `(level, wedge_number, wedge_reward, amount)` by spin.
**Controls:** Level dropdown with **All** option. When **All** is selected, gap columns visually separate levels.
**Use it for:** Verifying wedge reachability and balance per spin, auditing the effect of mute/force rules (jackpot/levelup) on player flow.
**Notes:** Dual x‑axes label **bottom:** `L<level> W<wedge>` and **top:** `<reward> (amount)`; annotations include `%`.

---

## Performance

* Vectorized NumPy operations + per‑level batching achieve high throughput (e.g., **100k players** in seconds on Colab).
* Forced/muted rules run as boolean masks; normalization avoids zero‑row traps.

**Tips**

* Reduce `N_PLAYERS` during config iteration, then scale up.
* Set `seed` for reproducible runs.

---

## Customization Hooks

* **Rule behavior:** Edit `apply_jackpot_rules` / `apply_levelup_rules` to change mute/force logic or priority.
* **Per‑level jackpot params:** Replace the fixed `jackpot_level == 1` lookup with a mapping by `level`.
* **Additional wedge types:** Treat them as normal rewards unless given special rules.
* **KPIs:** Extend the export section with new aggregations, plots, or sanity checks.

---

## Troubleshooting

* **❌ Spreadsheet not found or no access** → Check the Sheet is shared with the Colab account.
* **❌ Sheet validation failed** → The alert lists missing tabs/columns; add them and re‑run.
* **Wheel has no `levelup` wedge** → Add at least one `levelup` wedge per wheel; otherwise level completion is impossible.
* **Stuck players / no progression** → Confirm `levelup_max_spins` is set and reachable; verify wedge weights and types.
* **Non‑numeric cells** → The loader coerces numeric strings and treats blanks/`NA`/`—` as missing, then fills with 0 with a warning.

---

## Data Hygiene & Conventions

* Headers are normalized: lowercased, spaces → underscores.
* Reward names and types are lowercased/trimmed for consistent merges.
* Numeric parsing strips commas and whitespace.

---

## Security & Privacy

* The notebook accesses only the specified Sheet via your Google auth. No other external I/O by default.

---

## Folder Structure

All logic is inside the Colab notebook. Key sections:

* **Validation**: `validate_sheet_schema(...)`
* **Loading**: `load_configs(...)`
* **Core helpers**: weight masking, normalization, RNG draw
* **Runner**: `run_one_level(...)` and `simulate_multilevel(...)`
* **Exports**: `_df_to_values(...)`, `_get_or_create_ws(...)`, `export_tables_to_sheet(...)`

---

## Versioning & Reproducibility

* Use the `seed` parameter in `simulate_multilevel(...)` for deterministic draws.
* Keep a copy of the Sheet (File → Make a copy) per experiment.

---

## License

Internal use for the Pingo Light Wheel project unless otherwise specified.

---

## Acknowledgments

Built with ❤️ for rapid iteration between design (Sheets) and analysis (Colab), optimized for the **Pingo Light Wheel** use case.
