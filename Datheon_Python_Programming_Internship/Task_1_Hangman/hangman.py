"""A terminal-based Hangman game.

Place ``google-10000-english-no-swears.txt`` in the same folder as this
script to play with the supplied word list.  The game remains usable with a
small built-in list if that file is unavailable.
"""

from __future__ import annotations

from pathlib import Path
from random import choice
from string import ascii_lowercase
from typing import Callable, Optional, Set, Tuple


MAX_MISTAKES = 6
WORD_LIST_PATH = Path(__file__).with_name("google-10000-english-no-swears.txt")
FALLBACK_WORDS = (
    "python",
    "console",
    "programming",
    "keyboard",
    "variable",
    "function",
    "computer",
    "challenge",
)

GALLOW_STAGES = (
    """
  +---+
  |   |
      |
      |
      |
      |
=========
""",
    """
  +---+
  |   |
  O   |
      |
      |
      |
=========
""",
    """
  +---+
  |   |
  O   |
  |   |
      |
      |
=========
""",
    """
  +---+
  |   |
  O   |
 /|   |
      |
      |
=========
""",
    """
  +---+
  |   |
  O   |
 /|\\  |
      |
      |
=========
""",
    """
  +---+
  |   |
  O   |
 /|\\  |
 /    |
      |
=========
""",
    """
  +---+
  |   |
  O   |
 /|\\  |
 / \\  |
      |
=========
""",
)


def load_words(path: Path = WORD_LIST_PATH) -> Tuple[list[str], bool]:
    """Return playable words from *path* and whether the file was loaded."""
    try:
        words = [
            line.strip().lower()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip().isalpha() and len(line.strip()) >= 3
        ]
    except (OSError, UnicodeDecodeError):
        return list(FALLBACK_WORDS), False

    return (words, True) if words else (list(FALLBACK_WORDS), False)


def masked_word(secret_word: str, guessed_letters: Set[str]) -> str:
    """Make the word display, revealing every occurrence of guessed letters."""
    return " ".join(letter if letter in guessed_letters else "_" for letter in secret_word)


def show_status(
    secret_word: str,
    guessed_letters: Set[str],
    wrong_letters: Set[str],
    mistakes: int,
    output_func: Callable[[str], None] = print,
) -> None:
    """Print the current gallows, masked word, guesses, and remaining turns."""
    output_func(GALLOW_STAGES[mistakes])
    output_func(f"Word: {masked_word(secret_word, guessed_letters)}")
    output_func(
        "All guesses: "
        + (", ".join(sorted(guessed_letters)).upper() if guessed_letters else "None")
    )
    output_func(
        "Wrong guesses: "
        + (", ".join(sorted(wrong_letters)).upper() if wrong_letters else "None")
    )
    output_func(f"Remaining attempts: {MAX_MISTAKES - mistakes}")


def get_guess(
    guessed_letters: Set[str],
    input_func: Callable[[str], str] = input,
    output_func: Callable[[str], None] = print,
) -> Optional[str]:
    """Read one new English letter, returning ``None`` if the game is stopped."""
    while True:
        try:
            guess = input_func("\nGuess a letter: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            output_func("\nGame stopped. Thanks for playing!")
            return None

        if len(guess) != 1 or guess not in ascii_lowercase:
            output_func("Please enter exactly one letter (A-Z).")
        elif guess in guessed_letters:
            output_func("You already guessed that letter. Try a different one.")
        else:
            return guess


def play_round(
    secret_word: str,
    input_func: Callable[[str], str] = input,
    output_func: Callable[[str], None] = print,
) -> Optional[bool]:
    """Play one round and return True (win), False (loss), or None (stopped)."""
    guessed_letters: Set[str] = set()
    wrong_letters: Set[str] = set()
    mistakes = 0

    while mistakes < MAX_MISTAKES:
        show_status(secret_word, guessed_letters, wrong_letters, mistakes, output_func)
        guess = get_guess(guessed_letters, input_func, output_func)
        if guess is None:
            return None

        guessed_letters.add(guess)
        if guess in secret_word:
            output_func("Correct!")
            if all(letter in guessed_letters for letter in secret_word):
                show_status(secret_word, guessed_letters, wrong_letters, mistakes, output_func)
                output_func("\nCongratulations — you won!")
                return True
        else:
            wrong_letters.add(guess)
            mistakes += 1
            output_func("Incorrect.")

    show_status(secret_word, guessed_letters, wrong_letters, mistakes, output_func)
    output_func(f"\nGame over. The word was: {secret_word.upper()}")
    return False


def ask_to_play_again(
    input_func: Callable[[str], str] = input,
    output_func: Callable[[str], None] = print,
) -> bool:
    """Ask whether to begin a new round."""
    while True:
        try:
            answer = input_func("\nPlay again? (y/n): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False

        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        output_func("Please answer y or n.")


def main() -> None:
    """Run Hangman until the player chooses to exit."""
    words, loaded_from_file = load_words()

    print("=" * 40)
    print("          HANGMAN WORD GAME")
    print("=" * 40)
    if loaded_from_file:
        print(f"Loaded {len(words):,} playable words from {WORD_LIST_PATH.name}.")
    else:
        print("Word list was not found; using the built-in backup words.")

    while True:
        play_round(choice(words))
        if not ask_to_play_again():
            print("\nThanks for playing Hangman!")
            break


if __name__ == "__main__":
    main()
