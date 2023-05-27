import re
import shutil
import sys
from pathlib import Path
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
        print("COPYING FILES:")
        for old_file in set(self._resolved_files):
            print(old_file)
            new_file = new_vault_path.joinpath(old_file.relative_to(self.vault_path))
            new_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(old_file, new_file)

    def _resolve(self):
        """
        Resolves all Markdown links and wikilinks
        """

        self._vault_files = [vault_file for vault_file in self.vault_path.rglob("*") if vault_file.is_file()]
        self._vault_notes_to_copy = []
        self._find_files_to_copy()
        self._resolved_files = []

        self._resolve_wikilinks()
        self._resolve_markdown_links()

    def _find_files_to_copy(self):
        """
        Finds all notes marked with OBSIDIAN_COPY_TAG
        """
        for note_file in self._filter_note_files(self._vault_files):
            if OBSIDIAN_COPY_TAG in note_file.read_text():
                self._vault_notes_to_copy.append(note_file)

    def _resolve_wikilinks(self):
        """
        Resolve all wikilinks in the Obsidian vault as file paths
        """
        print("PROCESSING WIKILINKS:\n")
        for note_file in self._vault_notes_to_copy:
            self._do_resolve_note_wikilinks(note_file)
        print("\n\n")

    def _resolve_markdown_links(self):
        """
        Resolve all Markdown links in the Obsidian vault as file paths
        """
        print("PROCESSING MARKDOWN LINKS:\n")
        for note_file in self._vault_notes_to_copy:
            self._do_resolve_note_markdown_links(note_file)
        print("\n\n")

    def _do_resolve_note_wikilinks(self, note_file: Path):
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
                self._resolved_files.append(linked_file)
                new_linked_files.append(linked_file)

        new_linked_notes = self._filter_note_files(new_linked_files)
        for linked_note in new_linked_notes:
            self._do_resolve_note_wikilinks(linked_note)

    def _do_resolve_note_markdown_links(self, note_file: Path):
        note_text = note_file.read_text()
        markdown_links = [match.group(2) for match in re.finditer(r"\[(.+?)]\((.+?)\)", note_text)]
        markdown_internal_paths = filter(lambda link: "://" not in link, markdown_links)

        new_linked_files = []
        for markdown_path in markdown_internal_paths:
            print(f"Processing markdown link {markdown_path} in note {note_file}")
            decoded_path = unquote(markdown_path).strip("/")
            decoded_file = self.vault_path.joinpath(Path(decoded_path)) if not decoded_path.startswith(".") else note_file.parent.joinpath(Path(decoded_path))

            if not decoded_file.suffix:
                decoded_file = decoded_file.with_suffix(".md") # remember, links to markdown don't need to have extension

            linked_file = None
            if decoded_file.exists():
                linked_file = next(
                    (vault_file for vault_file in self._vault_files if vault_file.samefile(decoded_file)),
                    None
                )

            if linked_file and linked_file not in self._resolved_files:
                self._resolved_files.append(linked_file)
                new_linked_files.append(linked_file)

        new_linked_notes = self._filter_note_files(new_linked_files)
        for linked_note in new_linked_notes:
            self._do_resolve_note_markdown_links(linked_note)

    @staticmethod
    def _filter_note_files(files: list[Path]) -> list[Path]:
        return list(filter(lambda file: file.name.endswith(".md"), files))


if __name__ == '__main__':
    source_vault = sys.argv[1]
    destination_vault = sys.argv[2]

    ObsidianCopy(Path(source_vault)).copy(Path(destination_vault))
