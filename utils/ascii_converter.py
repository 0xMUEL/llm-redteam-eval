"""
ASCII art converter.
Converts text keywords into ASCII art representations using pyfiglet.
"""

import re

try:
    import pyfiglet
except ImportError:
    pyfiglet = None


class ASCIIConverter:
    """Converts sensitive keywords to ASCII art for the ArtPrompt strategy."""

    # Fallback simple block-letter mapping if pyfiglet not installed
    BLOCK_MAP = {
        "A": [" ## ", "#  #", "####", "#  #", "#  #"],
        "B": ["### ", "#  #", "### ", "#  #", "### "],
        "C": [" ###", "#   ", "#   ", "#   ", " ###"],
        "D": ["### ", "#  #", "#  #", "#  #", "### "],
        "E": ["####", "#   ", "### ", "#   ", "####"],
        "F": ["####", "#   ", "### ", "#   ", "#   "],
        "G": [" ###", "#   ", "# ##", "#  #", " ## "],
        "H": ["#  #", "#  #", "####", "#  #", "#  #"],
        "I": ["###", " # ", " # ", " # ", "###"],
        "J": ["  ##", "  # ", "  # ", "# # ", " #  "],
        "K": ["#  #", "# # ", "##  ", "# # ", "#  #"],
        "L": ["#   ", "#   ", "#   ", "#   ", "####"],
        "M": ["#   #", "## ##", "# # #", "#   #", "#   #"],
        "N": ["#   #", "##  #", "# # #", "#  ##", "#   #"],
        "O": [" ## ", "#  #", "#  #", "#  #", " ## "],
        "P": ["### ", "#  #", "### ", "#   ", "#   "],
        "Q": [" ## ", "#  #", "#  #", " ## ", "  ##"],
        "R": ["### ", "#  #", "### ", "# # ", "#  #"],
        "S": [" ###", "#   ", " ## ", "   #", "### "],
        "T": ["#####", "  #  ", "  #  ", "  #  ", "  #  "],
        "U": ["#  #", "#  #", "#  #", "#  #", " ## "],
        "V": ["#   #", "#   #", " # # ", " # # ", "  #  "],
        "W": ["#   #", "#   #", "# # #", "## ##", "#   #"],
        "X": ["#   #", " # # ", "  #  ", " # # ", "#   #"],
        "Y": ["#   #", " # # ", "  #  ", "  #  ", "  #  "],
        "Z": ["#####", "   # ", "  #  ", " #   ", "#####"],
    }

    def __init__(self, font: str = "banner3"):
        self.font = font
        self._figlet = None
        if pyfiglet:
            try:
                self._figlet = pyfiglet.Figlet(font=font)
            except pyfiglet.FontNotFound:
                self._figlet = pyfiglet.Figlet(font="banner")

    def convert(self, word: str) -> str:
        """
        Convert a word to ASCII art.

        Args:
            word: The word to convert.

        Returns:
            Multi-line ASCII art string.
        """
        if self._figlet:
            return self._figlet.renderText(word).rstrip()

        # Fallback: manual block letters
        return self._manual_convert(word.upper())

    def _manual_convert(self, word: str) -> str:
        """Fallback ASCII art using the built-in block map."""
        rows = [""] * 5
        for char in word:
            if char in self.BLOCK_MAP:
                for i, row in enumerate(self.BLOCK_MAP[char]):
                    rows[i] += row + "  "
            elif char == " ":
                for i in range(5):
                    rows[i] += "    "
            else:
                # Unknown char — render as placeholder
                for i in range(5):
                    rows[i] += "? "
        return "\n".join(rows)

    def replace_marked_keywords(self, text: str) -> str:
        """
        Find all [[keyword]] markers in text and replace with ASCII art.

        Args:
            text: Text with [[keyword]] markers.

        Returns:
            Text with markers replaced by ASCII art blocks.
        """
        def replacer(match):
            keyword = match.group(1)
            ascii_art = self.convert(keyword)
            return f"\n```\n{ascii_art}\n```\n"

        return re.sub(r"\[\[(\w+)\]\]", replacer, text)

    def list_fonts(self) -> list[str]:
        """List available pyfiglet fonts."""
        if pyfiglet:
            return sorted(pyfiglet.FigletFont.getFonts())
        return ["(pyfiglet not installed — using built-in block letters)"]
