# obsidian-copy

Minimalistic python script that copies part of your Obsidian vault with all linked notes and files while preserving folder structure.

## How to
This script has zero dependencies, so you should be able to launch it with built-in Python (if your system has any):
```shell
python3 obsidian_copy.py "<source vault folder>" "<destination vault folder (might not exists)>"
```

To mark notes that you want to copy, simply add tag `#obsidian-copy`. The script will try to determine linked files, 
linked files for these linked files, and so on. You can use another tag by changing `OBSIDIAN_COPY_TAG` variable at
the top of the script.
