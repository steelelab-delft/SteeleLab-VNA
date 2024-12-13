# Git rules

## Commits:
- any commit that contains new code or updates existing code must also make relevant changes to the documentation.
- name commits by "#{Issue} {TYPES}: {changes made}" (for example: #1 DOCS: added rules)
- TYPES:
    - FEAT (feature)
    - TEST (test)
    - FIX (bug fix)
    - CHORE (maintenance / refactor / formatting)
    - DOCS (documentation in docs folder / docstrings)
    - REPORT (changes related to a report)
    - OTHER (e.g. notes / presentation / merge / cherry-pick)

## Branches:
- no pushing on main, only merge.
- make a new branch for new features / handling issues.

## Issues:
- issues must be labeled in the same way commits are.
- create an issue for all non-trivial work / bugfixes that must be done.

## Style:
- all modules must have a pylint score of at least 9.
- all modules must have been formatted with yapf using the provided [config/yapf_style.txt](config/yapf_style.txt)
  (use `yapf project tests -ir --style config/yapf_style.txt`)
- all functions will be provided with type hints.
- all functions except test functions must have docstrings describing their role.
