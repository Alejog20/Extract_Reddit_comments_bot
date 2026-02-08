# Reddit Data Extractor and Sentiment Analysis Project

This project provides a Python-based tool to extract posts and comments from Reddit based on user-defined search terms and subreddits. The extracted data includes various objective metrics about posts and comments and is saved into CSV files for further analysis. While initially designed for analyzing sentiments related to trade and tariffs, the tool is flexible enough to extract data on any topic.

## Current Functionality

The project currently consists of two main Python scripts:

### `main.py`
This file currently serves as a placeholder. When executed, it simply prints a welcome message:
```
Hello from analisis-sentimientos!
```
The primary execution logic for data extraction resides in `reddit_api_v2.py`.

### `reddit_api_v2.py`
This script is the core of the data extraction process. It handles authentication with the Reddit API and fetches posts and comments.

**Key Features:**
-   **Reddit API Authentication:** Uses OAuth2 to securely authenticate with Reddit using a Client ID and Client Secret.
-   **Configurable Search:** Allows users to specify multiple search terms and target specific subreddits (or search across all Reddit).
-   **Data Extraction:** Retrieves comprehensive data for Reddit posts (title, text, score, upvote ratio, creation time, number of comments, permalink, subreddit, author, etc.) and their associated comments (text, score, creation time, author, permalink, etc.).
-   **Objective Metrics:** Extracts various objective metrics for both posts and comments, such as text length, word count, upvote ratio, score, and controversiality, without performing subjective analysis.
-   **Text Cleaning:** Includes a utility function to clean extracted text by removing URLs and Reddit-specific formatting characters.
-   **Google Drive Integration (Optional):** Designed to integrate with Google Drive (particularly useful in Google Colab environments) to automatically save extracted CSV files to a specified path. Falls back to a local directory if Google Drive is not available or cannot be mounted.
-   **User-Friendly Input:** Prompts the user for necessary credentials, search parameters, and data limits via a command-line interface, offering default values and guidance.
-   **CSV Export:** Saves the extracted posts and comments into separate CSV files, timestamped for easy organization.

**How to Run `reddit_api_v2.py`:**

1.  **Prerequisites:**
    *   Python 3.x installed.
    *   **uv** package manager installed (`pip install uv`).
    *   Install required Python packages using `uv`:
        ```bash
        uv pip install -r requirements.txt
        # Or, to install based on pyproject.toml
        uv sync
        ```
        (Note: While `praw` is listed in `requirements.txt`, this script directly uses `requests` for API interactions. `uv sync` will install dependencies defined in `pyproject.toml` and `uv.lock`.)
2.  **Reddit API Credentials:**
    *   You need a Reddit application's Client ID and Client Secret. Follow these steps to obtain them:
        1.  Go to [https://www.reddit.com/prefs/apps](https://www.reddit.com/prefs/apps).
        2.  Scroll down and click on "create another app...".
        3.  Select "script" as the application type.
        4.  Fill in the "name" (e.g., "SentimentAnalysisTool"), "description", and set "redirect uri" to `http://localhost:8080` (or any valid URL, it's not used for this script type but is required).
        5.  Click "create app".
        6.  Your Client ID will be shown below the app name. Your Client Secret will be next to the "secret" label.
3.  **Execution:**
    *   Run the script from your terminal:
        ```bash
        python reddit_api_v2.py
        ```
    *   The script will then guide you through providing the Client ID, Client Secret, search terms, subreddits, and limits.
    *   Upon completion, CSV files containing the extracted posts and comments will be saved in the specified output directory (either Google Drive or a local `reddit_data` folder).

## Future Enhancements
This project is continuously evolving. Planned enhancements include:
- Removing emojis from print statements for a cleaner CLI output.
- Implementing advanced logging features for better traceability and debugging.
- Integrating modern CLI display libraries (e.g., progress bars, animations) for an improved user experience, especially in environments like Git Bash.
- Ensuring full script functionality and robustness.
- Developing comprehensive sentiment analysis capabilities using the extracted data.
- Improving error handling and user feedback.