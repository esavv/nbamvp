# NBA MVP Predictions

## Overview

This application predicts the [NBA MVP](https://en.wikipedia.org/wiki/NBA_Most_Valuable_Player) on a weekly basis as the NBA season progresses and shares results with users. For each active player, the app predicts how many MVP votes they'll receive at the end of the season.

---

## Scripts

- `predict_mvp.py`: Main entrypoint and coordinates all other scripts. Runs weekly.  
- `generate_data.py`: Pulls the latest NBA stats using the `basketball_reference_web_scraper` package.
- `mvp_model.py`: Trains the ML models used to make predictions.  
- `preprocess_data.py`: Prepares the data for model training.  
- `nba_email.py`: Emails results to users.
- `season_dates.py`: Manages fetching next season dates from Wikipedia after the current season ends.

---

## Acknowledgements

Big thanks to [basketball_reference_web_scraper](https://github.com/jaebradley/basketball_reference_web_scraper) and [Basketball Reference](https://www.basketball-reference.com/) for making this possible. Go Heat!