import re
import shutil
import sys
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote

OBSIDIAN_COPY_TAG = "#obsidian-copy"


class ObsidianCopy:
    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        assert vault_path.is_dir()

        self._vault_files: list[Path] = []
        self._vault_notes_to_copy: list[Path] = []
        self._resolved_files: list[Path] = []

    def copy(self, new_vault_path: Path):
        self._resolve()
        print("\nCOPYING FILES:")
        for old_file in set(self._resolved_files):
            print(old_file)
            new_file = new_vault_path.joinpath(old_file.relative_to(self.vault_path))
            new_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(old_file, new_file)

    def _resolve(self):
        """
        Prepare list of files to copy. Constructs this list from wikilinks and Markdown links
        """

        self._vault_files = [vault_file for vault_file in self.vault_path.rglob("*") if vault_file.is_file()]
        self._vault_notes_to_copy = [
            note_file for note_file in self._filter_note_files(self._vault_files)
            if OBSIDIAN_COPY_TAG in note_file.read_text()
        ]
        self._resolved_files = []

        for note_file in self._vault_notes_to_copy:
            self._resolve_note(note_file)
            self._resolved_files.append(note_file)

    def _resolve_note(self, note_file: Path):
        new_wikilinks_files = self._resolve_note_wikilinks(note_file)
        new_markdown_files = self._resolve_note_markdown_links(note_file)
        new_linked_files = set(new_wikilinks_files + new_markdown_files)

        self._resolved_files.extend(new_linked_files)

        for linked_note in self._filter_note_files(new_linked_files):
            self._resolve_note(linked_note)

    def _resolve_note_wikilinks(self, note_file: Path) -> list[Path]:
        """
        Resolve wikilinks to files for the given note.
        :return: list of linked files that haven't been resolved yet
        """
        note_text = note_file.read_text()
        wiki_links = [match.group(1) for match in re.finditer(r"\[\[(.+?)(#.+?)?(\|.+?)?]]", note_text)]

        new_linked_files = []
        for wiki_link in wiki_links:
            print(f"Processing wikilink {wiki_link} in note {note_file}")
            linked_file = next(
                (
                    vault_file for vault_file in self._vault_files
                    # links to markdown files (notes) don't necessarily need to have extensions
                    if (vault_file.suffix == ".md" and str(vault_file.with_suffix("")).endswith(wiki_link)) or \
                    str(vault_file).endswith(wiki_link)
                ),
                None
            )

            if linked_file and linked_file not in self._resolved_files:
                new_linked_files.append(linked_file)

        return new_linked_files

    def _resolve_note_markdown_links(self, note_file: Path) -> list[Path]:
        """
        Resolve Markdown links to files for the given note.
        :return: list of linked files that haven't been resolved yet
        """
        note_text = note_file.read_text()
        markdown_links = [match.group(2) for match in re.finditer(r"\[(.+?)]\((.+?)\)", note_text)]
        markdown_internal_paths = filter(lambda link: "://" not in link, markdown_links)

        new_linked_files = []
        for markdown_path in markdown_internal_paths:
            print(f"Processing markdown link {markdown_path} in note {note_file}")
            decoded_file = Path(unquote(markdown_path).strip("/"))

            if not decoded_file.suffix:
                decoded_file = decoded_file.with_suffix(".md")  # remember, links to markdown don't need to have extension

            linked_file = None
            relative_note_dir_file = note_file.parent.joinpath(decoded_file)
            relative_vault_file = self.vault_path.joinpath(decoded_file)

            if relative_note_dir_file.exists():  # first check if this file is relative to the note dir
                linked_file = next(
                    (vault_file for vault_file in self._vault_files if vault_file.samefile(relative_note_dir_file)),
                    None
                )
            elif relative_vault_file.exists():  # if not check if it is relative to the vault dir
                linked_file = next(
                    (vault_file for vault_file in self._vault_files if vault_file.samefile(relative_vault_file)),
                    None
                )

            if linked_file and linked_file not in self._resolved_files:
                new_linked_files.append(linked_file)

        return new_linked_files

    @staticmethod
    def _filter_note_files(files: Iterable[Path]) -> list[Path]:
        return list(filter(lambda file: file.name.endswith(".md"), files))


if __name__ == '__main__':
    source_vault = sys.argv[1]
    destination_vault = sys.argv[2]

    ObsidianCopy(Path(source_vault)).copy(Path(destination_vault))
