#@title Wheel of Wonders Main Analysis

# =========================
# Colab: Simple & Readable Multi-Level Wheel Simulator (Google Sheets)
# =========================

import time, numpy as np
!pip -q install gspread

import gspread
from google.colab import auth
from google.auth import default
import re
from google.colab import output  # Colab-only; falls back to input() if not available
import gspread
import sys
import warnings
import ipywidgets as widgets
from ipywidgets import interact
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
warnings.filterwarnings("ignore")

CONFIG_SHEET_INPUT = ""  #@param {type:"string"}

def _extract_sheet_key(s: str) -> str | None:
    if not s:
        return None
    s = s.strip().strip('"').strip("'")
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", s)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9-_]{20,}", s):
        return s
    return None

SHEET_KEY = _extract_sheet_key(CONFIG_SHEET_INPUT)
if not SHEET_KEY:
  output.eval_js('alert("❌ Invalid or missing Google Sheet link/key. Please try again.")')
  sys.exit(1)  # stop execution
else:
    print("✅ Using sheet key:", SHEET_KEY)


# ---- Auth & sheet key (unchanged auth flow) ----

auth.authenticate_user()
creds, _ = default()
gc = gspread.authorize(creds)
print("gspread authorized.")


# ---------- Loading (robust to non-numeric cells) ----------
def _norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.astype(str).str.strip().str.lower().str.replace(" ", "_", regex=False)
    return df

def _coerce_num(s: pd.Series):
    s = s.astype(str).str.strip()
    bad_vals = {"": np.nan, "na": np.nan, "n/a": np.nan, "-": np.nan, "—": np.nan,
                "None": np.nan, "none": np.nan}
    s = s.replace(bad_vals)
    s = s.str.replace(",", "", regex=False).str.replace(r"\s+", "", regex=True)
    return pd.to_numeric(s, errors="coerce")

def _to_int_safe(s: pd.Series, colname: str) -> pd.Series:
    x = _coerce_num(s)
    n_bad = int(x.isna().sum())
    if n_bad:
        print(f"[WARN] Column '{colname}' had {n_bad} non-numeric/blank cell(s); filling with 0.")
        x = x.fillna(0)
    return x.astype(np.int32)

def _to_float_safe(s: pd.Series, colname: str) -> pd.Series:
    x = _coerce_num(s).fillna(0.0).astype(np.float32)
    return x

def _ws_df(sh, title):
    ws = sh.worksheet(title)
    data = ws.get_all_values()
    df = pd.DataFrame(data)
    df.columns = df.iloc[0].astype(str)
    df = df.drop(index=0).reset_index(drop=True)
    df = _norm_cols(df)
    # drop fully empty rows
    empty = df.apply(lambda r: (r.astype(str).str.strip() == "").all(), axis=1)
    df = df.loc[~empty].reset_index(drop=True)
    return df

# Normalize headers the same way your loader does
def _norm_cols_list(cols):
    return [str(c).strip().lower().replace(" ", "_") for c in cols]

# Define required tabs + columns (normalized)
REQUIRED_SCHEMA = {
    "levels config": _norm_cols_list([
        "level","levelup_reward","levelup_reward_amount",
        "levelup_min_spins","levelup_max_spins","wheel_id"
    ]),
    "jackpot config": _norm_cols_list([
        "jackpot_level","jackpot_reward","jp_reward_amount","jp_min_spins","jp_max_spins"
    ]),
    "wheels config": _norm_cols_list([
        "wheel_id","wedge_number","wedge_reward","wedge_reward_amount","wedge_weight","wedge_type"
    ]),
    "resource valuation": _norm_cols_list([
        "reward","spins_value"
    ]),
}

def _alert_and_abort(msg: str):
    # Show popup and stop execution
    output.eval_js(f'alert({msg!r})')
    sys.exit(1)

def validate_sheet_schema(sheet_key: str, gc):
    try:
        sh = gc.open_by_key(sheet_key)
    except gspread.exceptions.SpreadsheetNotFound:
        _alert_and_abort("❌ Spreadsheet not found or no access. Please check the link/key and sharing settings.")
    except Exception as e:
        _alert_and_abort(f"❌ Could not open spreadsheet: {e}")

    missing_tabs = []
    missing_cols_by_tab = {}

    # Collect present worksheet titles (case sensitive compare with expected)
    present_titles = {ws.title for ws in sh.worksheets()}

    # 1) Tabs present?
    for tab, expected_cols in REQUIRED_SCHEMA.items():
        if tab not in present_titles:
            missing_tabs.append(tab)
            continue

        # 2) Columns present?
        try:
            ws = sh.worksheet(tab)
            values = ws.get_all_values()  # first row is headers
        except Exception as e:
            missing_cols_by_tab[tab] = [f"(error reading sheet: {e})"]
            continue

        if not values or len(values) == 0:
            missing_cols_by_tab[tab] = expected_cols[:]  # everything missing
            continue

        headers_raw = values[0]
        headers_norm = set(_norm_cols_list(headers_raw))
        expected_set = set(expected_cols)
        missing = sorted(list(expected_set - headers_norm))

        if missing:
            missing_cols_by_tab[tab] = missing

    # Any problems? Build one alert with all issues and abort
    if missing_tabs or missing_cols_by_tab:
        lines = []
        if missing_tabs:
            lines.append("Missing tabs:\n- " + "\n- ".join(missing_tabs))
        if missing_cols_by_tab:
            parts = []
            for tab, cols in missing_cols_by_tab.items():
                parts.append(f"{tab}:\n  - " + "\n  - ".join(cols))
            lines.append("Missing/invalid columns:\n" + "\n".join(parts))
        full_msg = "❌ Sheet validation failed:\n\n" + "\n\n".join(lines) + \
                   "\n\nPlease fix the sheet (add tabs/columns) and re-run."
        _alert_and_abort(full_msg)

        # --- Extra validation: per-wheel row completeness in "wheels config" ---
    wheels_tab = "wheels config"
    if wheels_tab in present_titles and wheels_tab not in missing_cols_by_tab:
        try:
            ws_wheels = sh.worksheet(wheels_tab)
            values = ws_wheels.get_all_values()
            if values and len(values) > 1:
                headers_raw = values[0]
                rows_raw = values[1:]
                cols = _norm_cols_list(headers_raw)

                # Build a quick dict-based table (avoid full pandas dependency here)
                col_idx = {c: i for i, c in enumerate(cols)}
                required_cols = ["wheel_id","wedge_number","wedge_reward","wedge_reward_amount","wedge_weight","wedge_type"]
                if all(c in col_idx for c in required_cols):
                    issues_by_wheel = {}

                    def _cell(r, name):
                        i = col_idx[name]
                        if i >= len(r): return ""
                        return str(r[i]).strip()

                    def _is_blank(x):
                        return x == "" or x.lower() in {"na","n/a","none","—","-"}  # treat these as not configured

                    def _as_int_or_none(x):
                        # numeric-ish -> int, else None
                        try:
                            xx = x.replace(",", "").strip()
                            if xx == "": return None
                            return int(float(xx))
                        except Exception:
                            return None

                    for r in rows_raw:
                        wheel_raw = _cell(r, "wheel_id")
                        wheel_id = _as_int_or_none(wheel_raw)
                        # Only validate rows where wheel_id is actually configured
                        if wheel_id is None:
                            continue

                        missing_fields = []
                        # Check each required field except wheel_id (already present)
                        for name in ["wedge_number","wedge_reward","wedge_reward_amount","wedge_weight","wedge_type"]:
                            val = _cell(r, name)
                            if _is_blank(val):
                                missing_fields.append(name)

                        if missing_fields:
                            issues_by_wheel.setdefault(wheel_id, set()).update(missing_fields)

                    if issues_by_wheel:
                        lines = ["❌ Sheet validation failed:\n",
                                 "Rows in 'wheels config' have a configured wheel_id but are missing fields:"]
                        for wid in sorted(issues_by_wheel):
                            miss = ", ".join(sorted(issues_by_wheel[wid]))
                            lines.append(f"- wheel_id {wid}: missing {miss}")
                        lines.append("\nPlease fill the missing cells and re-run.")
                        _alert_and_abort("\n".join(lines))
                # else: columns were already reported by the earlier column validation
        except Exception as e:
            _alert_and_abort(f"❌ Error while validating wheels completeness: {e}")

    print("✅ Sheet schema looks good.")

validate_sheet_schema(SHEET_KEY, gc)

def load_configs(sheet_key: str):
    sh = gc.open_by_key(sheet_key)
    levels  = _ws_df(sh, "levels config")
    jackpot = _ws_df(sh, "jackpot config")
    wheels  = _ws_df(sh, "wheels config")
    resource = _ws_df(sh, "resource valuation")

    # levels
    levels = levels[["level","levelup_reward","levelup_reward_amount",
                     "levelup_min_spins","levelup_max_spins","wheel_id"]].copy()
    levels["level"]              = _to_int_safe(levels["level"], "level")
    levels["wheel_id"]           = _to_int_safe(levels["wheel_id"], "wheel_id")
    levels["levelup_min_spins"]  = _to_int_safe(levels["levelup_min_spins"], "levelup_min_spins")
    levels["levelup_max_spins"]  = _to_int_safe(levels["levelup_max_spins"], "levelup_max_spins")
    levels["levelup_reward_amount"] = (
    pd.to_numeric(levels["levelup_reward_amount"], errors="coerce")
    .fillna(0.0)
    .astype(np.float32)
    )

    # jackpot (we’ll use jackpot_level==1 unless you map by level)
    jackpot = jackpot[["jackpot_level","jackpot_reward","jp_reward_amount","jp_min_spins","jp_max_spins"]].copy()
    jackpot["jackpot_level"] = _to_int_safe(jackpot["jackpot_level"], "jackpot_level")
    jackpot["jp_min_spins"]  = _to_int_safe(jackpot["jp_min_spins"], "jp_min_spins")
    jackpot["jp_max_spins"]  = _to_int_safe(jackpot["jp_max_spins"], "jp_max_spins")
    jackpot["jp_reward_amount"] = _to_float_safe(jackpot["jp_reward_amount"], "jp_reward_amount")

    # wheels
    wheels = wheels[["wheel_id","wedge_number","wedge_reward","wedge_reward_amount","wedge_weight","wedge_type"]].copy()
    wheels["wheel_id"]           = _to_int_safe(wheels["wheel_id"], "wheel_id")
    wheels["wedge_number"]       = _to_int_safe(wheels["wedge_number"], "wedge_number")
    wheels["wedge_weight"]       = _to_int_safe(wheels["wedge_weight"], "wedge_weight")
    wheels["wedge_reward_amount"]= _to_float_safe(wheels["wedge_reward_amount"], "wedge_reward_amount")
    wheels["wedge_type"]         = wheels["wedge_type"].astype(str).str.strip().str.lower()
    wheels["wedge_reward"]       = wheels["wedge_reward"].astype(str).str.strip().str.lower()

    # resource
    resource = resource[["reward", "spins_value"]].copy()
    resource["reward"] = resource["reward"].astype(str).str.strip().str.lower()
    resource["spins_value"] = pd.to_numeric(resource["spins_value"], errors="coerce") \
                                  .fillna(0.0).astype(np.float32)


    # Optional: drop rows where wheel_id or wedge_number is 0 (likely junk)
    before = len(wheels)
    wheels = wheels[~((wheels["wheel_id"] == 0) | (wheels["wedge_number"] == 0))].reset_index(drop=True)
    if len(wheels) < before:
        print(f"[INFO] Dropped {before - len(wheels)} wheels rows with wheel_id==0 or wedge_number==0")

    return levels, jackpot, wheels, resource

# ---------- Core helpers ----------
def build_wheel_view(wheels_df: pd.DataFrame, wheel_id: int):
    w = wheels_df.loc[wheels_df["wheel_id"] == wheel_id].sort_values("wedge_number").reset_index(drop=True)
    if w.empty:
        raise ValueError(f"No wheel rows for wheel_id={wheel_id}")
    wedge_numbers = w["wedge_number"].to_numpy(np.int32)
    base_weights  = w["wedge_weight"].to_numpy(np.float64)
    wedge_types   = w["wedge_type"].to_numpy(object)
    idx_levelup   = np.where(wedge_types == "levelup")[0]
    idx_jackpot   = np.where(wedge_types == "jackpot")[0]
    if idx_levelup.size == 0:
        raise ValueError(f"Wheel {wheel_id} has no 'levelup' wedge. Add one in config.")
    return wedge_numbers, base_weights, wedge_types, idx_levelup, idx_jackpot

def apply_jackpot_rules(weights, spins_wo_jp_row, jp_min, jp_max, idx_jackpot, jp_exists_row):
    if idx_jackpot.size == 0:  # wheel without jackpot wedge
        return
    # mute below min
    mute_mask  = (spins_wo_jp_row < jp_min) & jp_exists_row
    if mute_mask.any():
        r = np.where(mute_mask)[0]
        weights[np.ix_(r, idx_jackpot)] = 0.0
    # force at/after max (priority over levelup)
    force_mask = (spins_wo_jp_row >= jp_max) & jp_exists_row
    if force_mask.any():
        r = np.where(force_mask)[0]
        weights[r, :] = 0.0
        # put positive mass on JP wedges; normalization happens later
        if idx_jackpot.size == 1:
            weights[r, idx_jackpot[0]] = 1.0
        else:
            weights[np.ix_(r, idx_jackpot)] = 1.0

def apply_levelup_rules(weights, spin_index_row, lvl_min, lvl_max, idx_levelup, lv_exists_row):
    # mute below min
    mute_mask  = (spin_index_row < lvl_min) & lv_exists_row
    if mute_mask.any():
        r = np.where(mute_mask)[0]
        weights[np.ix_(r, idx_levelup)] = 0.0
    # force at/after max (but only if JP didn’t already zero others this spin)
    force_mask = (spin_index_row >= lvl_max) & lv_exists_row
    if force_mask.any():
        r_all = np.where(force_mask)[0]
        r = r_all[weights[r_all].sum(axis=1) > 0]
        if r.size:
            weights[r, :] = 0.0
            if idx_levelup.size == 1:
                weights[r, idx_levelup[0]] = 1.0
            else:
                weights[np.ix_(r, idx_levelup)] = 1.0

def normalize_and_draw(weights, rng):
    sums = weights.sum(axis=1)
    z = np.where(sums == 0.0)[0]
    if z.size:
        pos = weights[z] > 0
        counts = pos.sum(axis=1).clip(min=1)
        weights[z] = pos / counts[:, None]
        sums = weights.sum(axis=1)
    probs = weights / sums[:, None]
    cdf   = np.cumsum(probs, axis=1)
    cdf[:, -1] = 1.0
    u = rng.random(len(weights))
    picked = (u[:, None] <= cdf).argmax(axis=1)
    prob_to   = cdf[np.arange(len(weights)), picked]
    prob_from = prob_to - probs[np.arange(len(weights)), picked]
    chosen_p  = probs[np.arange(len(weights)), picked]
    return picked, prob_from, prob_to, chosen_p, u

# ---------- Single-level runner (reused by the levels loop) ----------
def run_one_level(level_idx: int,
                  levels_df: pd.DataFrame,
                  wheels_df: pd.DataFrame,
                  jp_min: int, jp_max: int,
                  player_ids: np.ndarray,
                  level: np.ndarray,
                  spin_index: np.ndarray,
                  spins_wo_jp: np.ndarray,
                  active_at_level: np.ndarray,
                  rng) -> list[dict]:
    """
    Runs the wheel until players at this level hit 'levelup'.
    Returns list of rows (dicts). Mutates spin_index, spins_wo_jp, and active_at_level in place.
    """
    lvl_row = levels_df.loc[levels_df["level"] == level_idx]
    if lvl_row.empty:
        raise ValueError(f"No 'levels config' row for level={level_idx}")
    wheel_id = int(lvl_row["wheel_id"].iloc[0])
    lvl_min, lvl_max = int(lvl_row["levelup_min_spins"].iloc[0]), int(lvl_row["levelup_max_spins"].iloc[0])

    wedge_numbers, base_weights, wedge_types, idx_levelup, idx_jackpot = build_wheel_view(wheels_df, wheel_id)
    W = len(base_weights)

    # Availability mask for players at this level
    remaining = np.ones((active_at_level.sum(), W), dtype=bool)

    # Map: compact rows -> absolute player index
    abs_idx = np.where(active_at_level)[0]   # absolute indices into player arrays

    out_rows = []
    # Upper bound: each spin removes exactly one wedge for still-active players
    for _ in range(W):
        if remaining.shape[0] == 0:
            break

        w = np.where(remaining, base_weights, 0.0).astype(np.float64, copy=False)

        # Existence flags
        jp_exists = (w[:, idx_jackpot].sum(axis=1) > 0.0) if idx_jackpot.size else np.zeros(remaining.shape[0], bool)
        lv_exists = (w[:, idx_levelup].sum(axis=1) > 0.0)

        # Pull per-player state for these compact rows
        spins_row = spins_wo_jp[abs_idx]
        spins_ix  = spin_index[abs_idx]

        # Apply rules
        apply_jackpot_rules(w, spins_row, jp_min, jp_max, idx_jackpot, jp_exists)
        apply_levelup_rules(w,  spins_ix,  lvl_min, lvl_max, idx_levelup, lv_exists)

        # Draw & emit
        picked, prob_from, prob_to, chosen_p, u = normalize_and_draw(w, rng)

        for i in range(remaining.shape[0]):
            p_abs = abs_idx[i]
            wn   = int(wedge_numbers[picked[i]])
            wtyp = str(wedge_types[picked[i]])
            out_rows.append({
                "player_id": int(player_ids[p_abs]),
                "level": int(level[p_abs]),
                "jackpot_level": 1,  # using jackpot level 1 (can map if you like)
                "spin": int(spin_index[p_abs]),
                "spins_wo_jp": int(0 if wtyp == "jackpot" else spins_wo_jp[p_abs]),
                "wheel_id": int(wheel_id),
                "levelup_min_spins": int(lvl_min),
                "levelup_max_spins": int(lvl_max),
                "jp_min_spins": int(jp_min),
                "jp_max_spins": int(jp_max),
                "wedge_number": wn,
                "wedge_type": wtyp,
                "original_wedge_weight": int(base_weights[wn-1] if 0 <= wn-1 < W else 0),
                "wedge_weight": float(w[i, picked[i]]),
                "spin_result": float(u[i]),
                "prob_from": float(prob_from[i]),
                "prob_to": float(prob_to[i]),
                "probability": float(chosen_p[i]),
            })

        # Update state
        remaining[np.arange(remaining.shape[0]), picked] = False
        was_jp  = (wedge_types[picked] == "jackpot")
        was_lv  = (wedge_types[picked] == "levelup")

        spins_wo_jp[abs_idx] = np.where(was_jp, 0, spins_wo_jp[abs_idx] + 1)

        # Players who leveled up: mark them done for THIS level
        done_mask = was_lv
        if done_mask.any():
            # remove those rows from this level's remaining
            keep = ~done_mask
            remaining = remaining[keep]
            # increment spin index only for those who stay
            spin_index[abs_idx[keep]] += 1
            # shrink abs_idx to those who stay at this level
            abs_idx = abs_idx[keep]
        else:
            # nobody leveled this spin: everyone increments spin index
            spin_index[abs_idx] += 1

        # If nobody remains at this level, break
        if remaining.shape[0] == 0:
            break

    return out_rows

# ---------- Multi-level simulation ----------
def simulate_multilevel(levels_cfg: pd.DataFrame,
                        jackpot_cfg: pd.DataFrame,
                        wheels_cfg: pd.DataFrame,
                        N_PLAYERS=100_000, seed=None) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    # Player state
    player_ids = np.arange(1, N_PLAYERS + 1, dtype=np.int32)
    level      = np.full(N_PLAYERS, 1, dtype=np.int32)          # start at level 1
    spin_index = np.ones(N_PLAYERS, dtype=np.int32)              # spin counter resets per level ON ENTRY
    spins_wo_jp= np.zeros(N_PLAYERS, dtype=np.int32)             # persists across levels; reset only on jackpot

    # Jackpot parameters: using jackpot_level == 1 (adjust if you have mapping by level)
    jp_row = jackpot_cfg.loc[jackpot_cfg["jackpot_level"] == 1]
    if jp_row.empty:
        raise ValueError("No 'jackpot config' row with jackpot_level == 1")
    jp_min = int(jp_row["jp_min_spins"].iloc[0])
    jp_max = int(jp_row["jp_max_spins"].iloc[0])

    # Iterate levels in ascending order, starting from 1
    level_list = sorted(levels_cfg["level"].unique().astype(int))
    if 1 not in level_list:
        raise ValueError("levels config must include level == 1")

    all_rows = []

    # Track which players are still progressing (i.e., have not finished the last level yet)
    still_playing = np.ones(N_PLAYERS, dtype=bool)

    for lvl in level_list:
        # select players currently at this level
        at_level = still_playing & (level == lvl)
        if not at_level.any():
            continue

        # Run this level until they level up
        rows = run_one_level(
            level_idx=lvl,
            levels_df=levels_cfg,
            wheels_df=wheels_cfg,
            jp_min=jp_min, jp_max=jp_max,
            player_ids=player_ids,
            level=level,
            spin_index=spin_index,
            spins_wo_jp=spins_wo_jp,
            active_at_level=at_level,
            rng=rng
        )
        all_rows.extend(rows)

        # Everyone who was at this lvl and played it now either leveled up or (pathologically) exhausted all wedges.
        # We treat “finished this level” as “advance to next level if it exists”, otherwise they’re done.
        next_level = lvl + 1
        has_next = next_level in level_list
        if has_next:
            level[at_level] = next_level
            spin_index[at_level] = 1  # reset spin counter on entering the next level
        else:
            still_playing[at_level] = False  # done with last level

    # Build score_data
    score = pd.DataFrame(all_rows).sort_values(["player_id","level","spin"]).reset_index(drop=True)
    return score

# ---------- Run ----------

levels_cfg, jp_cfg, wheels_cfg, resource_df = load_configs(SHEET_KEY)
print("Configs loaded:",
      f"levels={levels_cfg.shape}, jackpot={jp_cfg.shape}, wheels={wheels_cfg.shape}")

t0 = time.time()
score_data = simulate_multilevel(levels_cfg, jp_cfg, wheels_cfg, N_PLAYERS=100_000, seed=None)
t1 = time.time()
print(f"score_data rows: {len(score_data):,}")
print(f"Elapsed: {t1 - t0:.2f}s")

# Quick sanity: every player should have a levelup per level, and no rows after levelup within each level
lvlup_first = (score_data[score_data["wedge_type"]=="levelup"]
               .groupby(["player_id","level"], as_index=False)["spin"].min()
               .rename(columns={"spin":"lvlup_spin"}))
m = score_data.merge(lvlup_first, on=["player_id","level"], how="left")
off = m[(m["lvlup_spin"].notna()) & (m["spin"] > m["lvlup_spin"])]
print(f"[CHECK] Rows after levelup within level: {len(off)}")

score_data_filtered = score_data[['player_id','level','spin','wheel_id','wedge_number','wedge_type','levelup_min_spins','levelup_max_spins']]
score_data_filtered = pd.merge(score_data_filtered, wheels_cfg[['wheel_id','wedge_number','wedge_reward','wedge_reward_amount']], on=['wheel_id','wedge_number'], how='left')
score_data_filtered = pd.merge(score_data_filtered, resource_df, left_on='wedge_reward', right_on='reward', how='left')
score_data_filtered['spins_value'] = round(score_data_filtered['spins_value'] * score_data_filtered['wedge_reward_amount'],2)
