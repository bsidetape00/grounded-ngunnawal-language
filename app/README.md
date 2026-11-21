# Yarn Ngunnawal (phone app, working version)

A phone-first learning app built only from the two established sources in this repository:

- Louise Baird, Ngunnawal XML dictionary, 4 October 2022
- Louise Baird, A Sketch Grammar of Ngunnawal (AIATSIS, 2019), Appendix C 17.3 word list, pages 117 to 139

No words have been added. Language authority: Cheyne Halloran.

## What is in it

- `words.json`: 1,453 entries. Each one is marked:
  - `ok`: same headword and matching meaning in both sources (842). Lessons, quizzes and word of the day use only these.
  - `chk`: same headword but the meanings do not line up (42). Needs checking.
  - `b`: Baird 2022 dictionary only (443).
  - `s`: sketch grammar word list only (126).
- 15 personal names from the dictionary are left out.
- Lessons also leave out ceremony, death, rude and racial terms, and anything marked uncertain with `?`. Those stay in the dictionary.
- Word groups (Animals, Body and so on) come from the English meanings only. They are for browsing, not a language claim.
- The verb page uses the ngubu 'to beat, to hit' paradigm from the sketch grammar, Appendix B, pages 87 to 90.
- No audio. There are no recordings in the source files.

## Notes from the language authority

`authority_notes.json` holds notes from Cheyne Halloran, recorded word for word. The build attaches each note to every entry with that headword. If a note confirms a sketch grammar meaning (`confirms`), that meaning is no longer flagged as a conflict.

## Run it

The page loads `words.json`, so open it through a web server, not as a file:

    cd app && python3 -m http.server 8000

Then open http://localhost:8000 on the same network.

## Rebuild the word list

Needs `beautifulsoup4` and `pdftotext` (poppler-utils).

    python3 app/build_words.py ngunnawal_language_database_package.zip app

## Known limits

- The earlier `03_consolidation/sketch_exact_matches.csv` matched spellings only. Some of those pairs have different meanings (for example bula is "two" in Baird 2022). This build compares meanings as well.
- The meaning check is automatic word overlap. It will miss some true matches worded differently (for example "swan" against "large bird with a long neck"). Those show as `chk`.
