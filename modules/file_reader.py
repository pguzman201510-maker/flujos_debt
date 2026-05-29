import pandas as pd
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def read_file(filepath):
    if not os.path.exists(filepath):
        logging.error(f"File not found: {filepath}")
        return None

    filename = os.path.basename(filepath)
    is_xls = filename.lower().endswith('.xls')

    if is_xls:
        delimiters = ['\t', ';', ',']
        encodings = ['utf-8', 'latin-1', 'cp1252']

        for delim in delimiters:
            for enc in encodings:
                try:
                    df = pd.read_csv(filepath, sep=delim, encoding=enc, on_bad_lines='skip', engine='python', index_col=False)
                    if len(df.columns) > 1:
                        logging.info(f"Successfully read {filename} as delimited CSV (delimiter: '{delim}', encoding: '{enc}')")
                        return df
                except Exception:
                    pass

    # Try as normal excel
    try:
        df = pd.read_excel(filepath)
        logging.info(f"Successfully read {filename} as Excel")
        return df
    except Exception as e:
        logging.error(f"Failed to read {filename} as Excel: {str(e)}")

    logging.error(f"Could not read {filename} with any method.")
    return None
