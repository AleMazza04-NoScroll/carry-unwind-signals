# Data

Bloomberg data cannot be redistributed, so this folder holds only the list of series.

1. On a Bloomberg terminal, export the daily history (field PX_LAST, from 1 January 2000 to the present) of every ticker in `tickers.csv`, one series per `.xlsx` file, with the standard history export (HP or the Excel add-in).
2. Put all files in one folder. File names do not matter: each series is identified by the `Security` cell of the export.
3. Run `python run_analysis.py --data-dir "path/to/that folder"`.

Series marked as optional are read if present and are not required by the main results.
