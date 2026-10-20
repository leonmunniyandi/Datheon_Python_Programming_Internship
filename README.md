# Datheon Python Programming Internship

This repository contains all four completed Python tasks from the internship
syllabus. Each task has its own source code, supporting files, and README.

## Projects

| Task | Project | Folder | Main program |
| --- | --- | --- | --- |
| 1 | Hangman Word Guessing Game | [Task_1_Hangman](Task_1_Hangman/) | `hangman.py` |
| 2 | Stock Portfolio Performance Tracker | [Task_2_Stock_Portfolio](Task_2_Stock_Portfolio/) | `portfolio.py` |
| 3 | Automated File Organizer | [Task_3_File_Organizer](Task_3_File_Organizer/) | `organizer.py` |
| 4 | Rule-Based Terminal Chatbot | [Task_4_Chatbot](Task_4_Chatbot/) | `chatbot.py` |

## Repository structure

```text
Datheon_Python_Programming_Internship/
|-- README.md
|-- .gitignore
|-- Task_1_Hangman/
|   |-- hangman.py
|   |-- google-10000-english-no-swears.txt
|   `-- README.md
|-- Task_2_Stock_Portfolio/
|   |-- portfolio.py
|   |-- constituents.txt
|   |-- portfolio_summary.csv
|   |-- requirements.txt
|   |-- test_portfolio.py
|   |-- README.md
|   `-- .gitignore
|-- Task_3_File_Organizer/
|   |-- organizer.py
|   |-- shutil.html
|   |-- test_organizer.py
|   |-- README.md
|   `-- .gitignore
`-- Task_4_Chatbot/
    |-- chatbot.py
    |-- sample_faq.json
    |-- test_chatbot.py
    |-- README.md
    `-- .gitignore
```

## Requirements

Install Python 3.9 or later, then download or clone this repository. Open a
terminal in its root folder. All four projects have standard-library-only
operation. Online market prices for Task 2 require the optional yfinance
dependency and internet access.

The commands below assume your Python 3 interpreter is available as `python`.
On systems using `python3` instead, substitute that command.

## Run the projects

### Task 1: Hangman

```bash
python Task_1_Hangman/hangman.py
```

Guess the hidden word one letter at a time. Six unique incorrect guesses cause
a loss. ASCII gallows update after each wrong guess; duplicate and invalid
guesses do not deduct another attempt. Words come from the adjacent supplied
English word list. Replay is supported.

### Task 2: Stock portfolio tracker

```bash
python Task_2_Stock_Portfolio/portfolio.py
```

Enter stock tickers, buy prices, and share quantities. Type `done`, then supply
current prices. The program displays invested capital, market value, gains or
losses, and capital-weighted percentage returns, then appends a CSV snapshot.

For optional online prices:

```bash
python -m pip install -r Task_2_Stock_Portfolio/requirements.txt
python Task_2_Stock_Portfolio/portfolio.py --live
```

Online mode uses the latest available one-minute closing price and shows its
timestamp; prices may be delayed. `constituents.txt` contains stock/company
metadata, not prices. The included CSV contains fictional demonstration
values, as explained in the task README.

### Task 3: File organizer

```bash
python Task_3_File_Organizer/organizer.py
```

Enter a specific folder to organize. Review the move preview, then type `YES`
to apply it. Files are grouped into Documents, Images, Videos, Archives, Code,
Audio, and Other. Naming collisions receive numbered suffixes. Moves and
errors are recorded in `organizer_log.csv` inside the selected folder.

To preview without changing files:

```bash
python Task_3_File_Organizer/organizer.py "C:\path\to\test-folder" --dry-run
```

`--recursive` also organizes eligible nested files into categories at the
selected root. `shutil.html` is the supplied reference documentation.

### Task 4: FAQ chatbot

```bash
python Task_4_Chatbot/chatbot.py
```

Type `help` for the available questions, ask about multiple topics, or use
`repeat` for the last answer. The chatbot handles greetings, follow-up context,
unrecognized input, and clean exits with `bye`, `exit`, or `quit`.

Responses come from the supplied `sample_faq.json`; the included topics are
business hours, internship project submissions, and certificates. This is a
rule-based program, and its sample answers are not independently verified
business policies.

## Verification

The portfolio, organizer, and chatbot include 38 automated tests in total.
Run them from this repository's root:

```bash
python -m unittest discover -s Task_2_Stock_Portfolio -v
python -m unittest discover -s Task_3_File_Organizer -v
python -m unittest discover -s Task_4_Chatbot -v
```

Hangman was checked for word loading, repeated-letter masking, duplicate
guesses, successful wins, and loss after six unique wrong guesses. Organizer
tests use temporary fixtures rather than existing user folders.

Further usage instructions and limitations appear in each task's README.
