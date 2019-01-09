# ACS Slicer
Basic slicer for accessing basic American Community Survey. Uses the [Plot.ly Dash](https://dash.plot.ly/) library for the visualization.

# Run
```
virtualenv -p python3 venv
source venv/bin/activate
pip install -r requirements.txt
gunicorn app:app
```
