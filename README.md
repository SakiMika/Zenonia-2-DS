# Zenonia 2 — NDS

A Nintendo DS / DSi runner for the supported native ARM WIPI version of **Zenonia 2: The Lost Memories**.

Game resources are loaded directly from `/zenonia2nds/` on the flashcard. The `.nds` contains the runner only; it does not embed the game or open ZIP/JAR files at runtime. Game files are not included.

## Key mapping

| DS Button | WIPI Button / Action |
| --- | --- |
| L + A | 1 |
| L + B | 3 |
| L + X | 7 |
| L + Y | 9 |
| R | # |
| A | OK |
| B | CLR |
| START | Call / quicksave |
| X | 0 |
| Y | * |
| SELECT | Show / hide the bottom-screen minimap |
| D-pad | Move |

Hold **L** while pressing the second button to use a combination. Active combinations do not also trigger the normal A, B, X or Y action.

**SELECT** switches the minimap between its native top-screen placement and the bottom-screen panel when available. It does not turn off the physical bottom screen.

Tap the **gear icon** on the bottom screen to open settings. Use the **SINGLE** and **COMBO** tabs to customize button mappings. START sends the WIPI Call key; the game decides when quicksave is available.

## Requirements

- Python **3.9 or later** for `preparegame.py`; no additional Python packages are required.
- Your own supported native ARM WIPI game, supplied as a standalone `.jar` or a `.zip` containing a JAR.
- A homebrew-capable flashcard/loader with working **DLDI/FAT** access.
- To compile the runner: **devkitPro/devkitARM**, **libnds**, **libfat** and the devkitPro NDS tools.

Java-only JARs and unrelated WIPI game layouts are not supported by this runner.

## Prepare the game

1. Extract the source package. Keep `preparegame.py` and the included `en/` folder together, beside `Makefile`.
2. Start the local tool:

   ```sh
   python preparegame.py
   ```

3. Keep the terminal open. The interface opens in your web browser and runs locally; files are not uploaded to an Internet service.
4. Click **Open WIPI File** and select your ZIP or JAR. If the ZIP contains multiple JARs, choose the correct one.
5. Choose a language under **Select Language**:
   - **KR:** use the original game resources. Translation validation is skipped.
   - **EN:** apply the editable English TXT package in `en/`.
   - **Custom package:** apply a translation created with **Create Translation**.
6. For EN or a custom translation, click **Check Error** to validate the TXT files. This does **not** create or update game output. If validation fails, details are written to `error.txt` beside the tool, or inside the directory specified by `--home`. Fix the reported errors and check again. A successful check removes the previous tool-generated error report.
7. Click **Create Game Folder** to create or update `zenonia2nds/`. EN/custom translations are validated again before output is replaced; KR is copied without translation validation. The optional **Offline compatibility profile** is applied separately when enabled.
8. Click **Open zenonia2nds** to locate the generated folder. Copy the **whole folder** to the root of your flashcard.

Opening a game or changing the selected language does not automatically export it. Always click **Create Game Folder** after changing your selection or editing a translation.

### Output directly to a flashcard

For a flashcard mounted as drive `E:` on Windows:

```sh
python preparegame.py --card-root "E:/"
```

The tool will write to `E:/zenonia2nds/` when you click **Create Game Folder**. Replace `E:/` with your actual card location. Existing game folders are backed up before replacement.

## Create a translation

1. Open the game in PrepareGame.
2. Enter a package name, such as `VI` or `ES`.
3. Choose a base:
   - **EN:** copy the editable TXT package from `en/`.
   - **KR:** dump text from the original imported game.
4. Click **Create**. The new package appears under **Select Language**; existing packages are not overwritten.
5. Select the package and click **Open TXT Folder**.
6. Edit the text after each record header's closing `]`. Preserve record indices, metadata, formatting placeholders and required escape sequences.
7. Run **Check Error**, then **Create Game Folder**.

TXT files use UTF-8, but the prepared game uses CP949. Fixed-slot limits are measured in **bytes**, not characters. Unverified RAW entries are read-only references. Naming a package `VI` does not add Vietnamese glyphs or font support.

Existing `en/` edits are preserved. If `en/` is missing, the tool restores its bundled English text seed on first launch.

## Build the runner

### Windows

With devkitPro/devkitARM and the required NDS libraries installed, run:

```bat
build.bat
```

### Command line

With the devkitPro environment configured, run:

```sh
make
```

The output ROM is **`Zenonia 2 DS Runner.nds`**. Its game code remains **`####`** for the existing homebrew/DLDI profile.

Game files are not required during compilation. Compatible translation changes only require regenerating and copying `zenonia2nds/`; rebuilding the `.nds` is not necessary.

## Flashcard layout

```text
/
├── Zenonia 2 DS Runner.nds
├── zenonia2nds/
│   ├── binary.mod
│   ├── data/
│   ├── menu/
│   ├── sound/
│   └── ...all other generated resources
└── ZKR1.sav                 # created by the runner when saving
```

Launch the `.nds` through your flashcard's homebrew-capable menu or loader. Keep an existing `ZKR1.sav` outside `zenonia2nds/`; replacing the game resource folder should not overwrite this save. Back up important saves before updating.

## melonDS testing

In melonDS DS mode, enable **DLDI (for homebrew)** and configure a writable SD image. If using **Sync SD to folder**, select a PC folder containing `zenonia2nds/` at its root. Restart the game after changing storage settings or resources.

The emulator must be able to access the complete game folder through its emulated storage. Merely placing `zenonia2nds/` next to the `.nds` on your PC is not sufficient unless that location is also configured as the emulated storage root.

## Troubleshooting

- **Missing `binary.mod` or missing resources:** check that the card contains `/zenonia2nds/binary.mod`, not `/zenonia2nds/zenonia2nds/binary.mod`, and that DLDI/FAT access is working.
- **Translation errors:** open `error.txt`, correct the listed files and run **Check Error** again. Invalid translations do not replace the last successful game output.
- **The old language is still shown:** select the desired package, click **Create Game Folder**, copy the updated folder and restart the game.
- **KR cannot be checked:** this is intentional. KR uses the original resources, so **Check Error** is disabled.
- **An older ROM still requests NitroFS:** rebuild the external-folder runner. Older NitroFS-based ROMs do not use this folder-loading workflow.

## Validation status

PrepareGame 2.1 passed 30 automated tool tests, local browser interaction tests and host-side runner regression checks. This release has not been fully compiled with devkitARM or verified as a new ROM on DS/DSi hardware or melonDS in the development environment.
