# Schackprogram med Stockfish

Ett grafiskt schackprogram i Python där användaren flyttar pjäser med musen i ett GUI.
Du kan spela mot Stockfish (med valbar svårighetsgrad) eller använda analysläge där
du spelar båda sidor och får dragförslag.

## Gruppmedlemmar

- Filip Mölne

## Vad programmet gör

- Visar schackbrädet i ett grafiskt fönster.
- Tar emot drag från användaren med mus (klicka pjäs, klicka målruta).
- Kontrollerar att draget är lagligt.
- Uppdaterar brädet efter varje giltigt drag.
- Kan låta Stockfish spela motståndare i olika svårighetsgrader.
- Kan ge dragförslag i analysläge.
- Visar senaste draget med färgmarkering på brädet.
- Visar materialöversikt (förlorade pjäser och poäng) för båda sidor.
- Spelar ljud vid drag, slag och notiser.
- Fortsätter tills partiet är slut eller användaren avslutar.

## Använda Pythonbibliotek

- `python-chess`
- `playsound`

## GUI och resurser

- GUI:t är byggt med `tkinter` (ingår i Pythons standardbibliotek).
- Schacklogik och motorstyrning använder `python-chess`.
- Extern schackmotor: Stockfish (körbar binär, t.ex. `stockfish-windows-x86-64-avx2.exe`).
- Ljudresurser i `sounds/`, kommer från (https://www.chess.com/forum/view/general/chessboard-sound-files):
  - `move-self.mp3`
  - `capture.mp3`
  - `notify.mp3`

## Övrigt som behövs för att köra

- Python 3.10+ (rekommenderat)
- Stockfish installerat eller nedladdat lokalt
- En körbar Stockfish-binär (`.exe` på Windows)

## Installation

1. Installera beroenden:
   ```bash
   pip install -r requirements.txt
   ```

2. Ladda ner Stockfish 18 och placera den i projektmappen:

   - Gå till [Stockfish Download](https://stockfishchess.org/download/)
   - Ladda ner en Windows-version (x64) som passar din CPU (t.ex. AVX2)
   - Extrahera zip-filen
   - Kopiera `stockfish-... .exe` till projektets rotmapp (samma mapp som `start.bat`)

3. (Valfritt) Sätt sökvägen till Stockfish manuellt:

   `STOCKFISH_PATH` behövs bara om auto-detektering inte hittar din motor.

   PowerShell:
   ```powershell
   $env:STOCKFISH_PATH = "C:\path\to\stockfish\stockfish-windows-x86-64-avx2.exe"
   ```

   Bash:
   ```bash
   export STOCKFISH_PATH="/path/to/stockfish"
   ```

4. Kör programmet:
   ```bash
   python main.py
   ```

## Snabbstart i Windows (.bat)

- Installera beroenden:
  ```bat
  install.bat
  ```
- Starta programmet:
  ```bat
  start.bat
  ```
- `start.bat` startar alltid GUI-läget.

Om `STOCKFISH_PATH` inte är satt fortsätter `start.bat` med auto-detektering.
Vid fel i vanlig `start.bat` pausas fönstret automatiskt så att du hinner läsa felet.
`start.bat` försöker också hitta Stockfish automatiskt:
- `stockfish.exe` i samma mapp som skriptet, eller
- `stockfish*.exe` i projektets undermappar, eller
- `stockfish.exe` i systemets PATH.

### Debug-läge

Om startfönstret stängs för snabbt kan du köra:

```bat
start.bat --debug
```

Det visar extra information (Python-version, `STOCKFISH_PATH`, exakt startkommando) och avslutar med `pause` så att du hinner läsa felet.

Vid start i GUI kan du välja:
- spelläge (mot Stockfish eller analysläge),
- färg (vit/svart) om du spelar mot Stockfish,
- svårighetsgrad (lätt, medel, svår, mycket svår).

## GUI med musstyrning

Du kan spela genom att klicka med musen:

1. Starta GUI:
   ```bash
   python main.py
   ```
2. Klicka först på pjäsen du vill flytta.
3. Klicka sedan på målrutan.

I GUI kan du välja:
- läge (spela mot Stockfish eller analysläge),
- färg (vit/svart),
- svårighetsgrad.

Knappen `Nytt parti` startar om med de val du har gjort.
Knappen `Tips` visar ett rekommenderat drag från Stockfish för sidan som står på tur.

### Ljud i GUI

GUI:t spelar ljud automatiskt från mappen `sounds/`:
- `move-self.mp3` vid vanligt drag
- `capture.mp3` vid slag
- `notify.mp3` vid schack och när partiet slutar

Om filerna saknas eller inte kan spelas fortsätter spelet utan ljud.

## Snabb test (för examinator)

1. Kör `install.bat`
2. Kör `start.bat`
3. Starta ett parti och gör några drag
4. Bekräfta att:
   - pjäser kan flyttas med musen
   - Stockfish spelar motdrag i läget "Spela mot Stockfish"
   - `Tips` visar ett rekommenderat drag
