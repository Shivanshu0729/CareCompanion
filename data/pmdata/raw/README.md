Place unzipped PMData participant folders here.

Expected layout:

```
data/pmdata/raw/
  p01/fitbit/*.json
  p01/fitbit/sleep_score.csv
  p02/fitbit/...
```

Download the dataset from https://datasets.simula.no/pmdata/ or Kaggle (`vlbthambawita/pmdata-a-sports-logging-dataset`).

Raw Fitbit exports are large and must not be committed to Git. After copying files locally, run:

```
python scripts/process_pmdata.py
```

Processed summaries are written to `data/pmdata/processed/`.
