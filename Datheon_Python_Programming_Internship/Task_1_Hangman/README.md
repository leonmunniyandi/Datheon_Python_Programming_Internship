# Hangman Word Guessing Game

A Python terminal game that chooses a random word from the supplied English
word list and asks the player to guess it one letter at a time.

## Features

- Masked word display, revealing every occurrence of a correct letter.
- Six unique incorrect guesses allowed.
- Seven ASCII gallows stages, including the initial empty stage.
- Guessed-letter tracking and duplicate-guess protection.
- Case-insensitive input and validation for single English letters.
- Clear win/loss messages and a replay prompt.
- Built-in backup words if the word list is unavailable.

## Requirements and run command

Python 3.9 or later. No external packages are required.

From this task's folder:

```bash
python hangman.py
```

Or from the main repository folder:

```bash
python Task_1_Hangman/hangman.py
```

Keep `google-10000-english-no-swears.txt` beside the script. It is loaded
relative to the script, and words shorter than three letters are excluded.

## How to play

1. Enter one letter from A to Z when prompted.
2. Correct guesses reveal letters without using an attempt.
3. Each new wrong letter adds one body part and uses an attempt.
4. Guess all letters before the sixth mistake to win.
5. Answer `y` to play again or `n` to exit.

Blank entries, numbers, multiple characters, and repeated guesses do not
remove attempts. EOF or Ctrl+C stops input gracefully.

## Files

- `hangman.py`: game program.
- `google-10000-english-no-swears.txt`: supplied English word list.
- `README.md`: instructions.
