# Noisense
Visualising sound sensor data.

## General description
Noisense is a web-based visualisation of sound sensor data retrieved from two sensors located in the Netherlands. It is meant as an artistic approach for communicating and discussing issues around sound pollution, and as a prototype for visualising these types of data.

The main page highlights the number of peaks in noise, and how often these are above certain noise levels, with a red line indicating 70 dB, marking a high-exposure bracket where people experience serious annoyance and disruption. You can choose either an existing dataset to load and view, or you can collect live data. If you chose an existing dataset, you can speed up the visualisation with the slider on the right.

On the top left you can switch to a different view, showing all of the existing datasets for one sensor. This allows a quick overview and comparison between different days. On the top right you can select the sensor and how many columns you want the grid to have. Clicking on one of the images allows a closer view.


## Data collection
Original plan: the data is fetched from the sensor API every five minutes and stored online at JSONBin for max 24h, at midnight this JSON is copied to a local file and emptied. However, JSONBin has a limited number of actions in the free version, so to have this running permanently this will add costs.

Current prototype: the live feed stores the data directly in the browser, but the datafiles are static. These were previously retrieved by a task scheduler on a local server using the fetch_data_locally.py that can be found in the src folder. The manifest.json in the data folder contains a list of the data-files that can be selected.



