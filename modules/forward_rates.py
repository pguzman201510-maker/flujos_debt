import pandas as pd
import logging

logger = logging.getLogger(__name__)

def get_forward_rate(df_tasas, index_name, target_date):
    """
    Finds the closest forward rate in df_tasas for the given index and date.
    Returns the rate as a float, or 0.0 if not found.
    """
    if df_tasas is None or df_tasas.empty:
        return 0.0

    index_str = str(index_name).strip()

    if index_str not in df_tasas.columns:
        logger.debug(f"Index {index_str} not found in forward rates columns.")
        return 0.0

    if 'Fecha' not in df_tasas.columns:
        logger.error("'Fecha' column missing in forward rates.")
        return 0.0

    target = pd.to_datetime(target_date)

    # Calculate absolute difference in days
    diff = (df_tasas['Fecha'] - target).abs()

    # Find index of minimum difference
    closest_idx = diff.idxmin()

    if pd.isna(closest_idx):
        return 0.0

    rate = df_tasas.loc[closest_idx, index_str]

    try:
        return float(rate)
    except:
        return 0.0
