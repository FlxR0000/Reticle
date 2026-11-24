Reticle - Windows tray crosshair overlay
Coded by FlxR  |  Discord: fs.d  |  see LICENSE.txt

Run:    pip install -r requirements.txt  then  pythonw crosshair.py
Build:  double-click build.bat  ->  dist\Reticle.exe
Default hotkeys: F8 show/hide | F9/F10 prev/next preset | Ctrl+Alt+1..9 load preset N | Ctrl+Alt+Arrows nudge
All hotkeys can be changed: Settings > Hotkeys (click one, press the new combo, Esc cancels; duplicates are rejected;
"Reset hotkeys to defaults" is there too). Preset slots 1-9 share one modifier combo.
Settings/presets/log: %APPDATA%\Crosshair   (crosshair.log has errors)
Games must run in Borderless/Windowed mode for the overlay to show.

SETTINGS WINDOW
  Tray menu > "Settings window...": one window with tabs (Shape / Colors / Position / Resolution / Games / Hotkeys)
  and a live preview (hover it: the screen dims and the REAL crosshair/images show at their real size and place). Changes apply instantly; "Save changes" / "Save as new..." are on the right.
  The window is created only when opened and destroyed when closed (no cost while closed).
  The tray menu is unchanged and still has everything. Images/video/drawing stay in the tray menu.

TRAY MENU LAYOUT
  Presets | Crosshair (Shape / Colors / Dimensions / Dot) | Hand drawing | Images & video |
  Position & monitor | In-game | Settings | Exit
  The top of the menu shows "(modified)" when the current preset has unsaved edits;
  "Save changes to: X" saves them.

CROSSHAIR
  Shapes: cross, T cross, X, cross + circle, circle, square, diamond, triangle, chevron, dot.
  Rotation, outline color, separate dot color, wide length/thickness/gap ranges, opacity.
  Every color menu has "Custom color (any color)..." (RGB sliders, paste/type #hex or r,g,b,
  Windows palette, screen eyedropper, "+ Save color" into "Saved colors"), plus
  "Paste color code from clipboard".

IMAGES
  Two independent images (Image 1 / Image 2), each with its own size (up to 512 px), position,
  opacity, rotation, horizontal/vertical flip and color (original / black & white / any solid
  color, transparency is kept).

VIDEO / GIF
  Images & video > Video / GIF > Choose video / GIF (mp4, webm, mkv, avi, mov, gif). Loops, no audio.
  Position by drag, size up to 1024 px, opacity and "Hide black background".
  The video file is referenced by path (not embedded) - keep the file where it is.
  Without opencv-python-headless only GIF works. Note: opencv makes the exe ~50 MB larger.

MOVE MODE (crosshair / images / video)
  Drag with the mouse (live preview), arrows nudge 1 px (Shift = 10), mouse wheel resizes
  images/video, Enter or double-click = done, Esc or right-click = cancel (restores old place).

HAND DRAWING
  Hand drawing > Open drawing editor: paint / erase / line / fill, horizontal and vertical
  mirroring, undo (Ctrl+Z), grid size 11-41, right-click = eraser.

PRESETS
  Presets > Save as new... saves shape + drawing + both images.
  Switch: pick from the list, F9/F10, or Ctrl+Alt+1..9.
  If the current preset has unsaved edits, switching asks Save / Discard / Cancel.
  The menu also shows "Save changes to: X" to update the current preset in place.
  More: copy 6-char code, rename, import from file, open folder, delete.

PRESET CODES
  Presets > Copy preset code is automatic:
  - Shape only -> a 6-character code (letters+digits, case-sensitive) for shape, color, length,
    thickness, gap, outline, dot, rotation, opacity. Custom colors snap to the nearest of 16
    palette colors.
  - With hand drawing and/or images -> a full code (CH2) carrying the drawing + both images
    (images shrunk to their display size, WebP-compressed). Exact colors are kept.
  Paste preset code accepts both.

IN-GAME
  Expand crosshair while firing (left mouse), aim-down-sights preset (right mouse),
  "Bind to game" (show only while that game is active),
  per-game presets (save the preset first): "Link current preset to an open game..." and
  "Link by choosing the game file (.exe)..." store the FULL PATH of the exe, so two different
  games (or copies) with the same exe name never clash. "Link by typing the path or name..."
  accepts a full path, or a bare name like valorant.exe (legacy; matches that name in any folder).
  An exact full-path link always wins over a name link. Same rule for "Bind to game". The preset switches automatically when that game's window
  becomes active. Remove links from "Linked games".
  "Hide crosshair outside linked games" shows the crosshair only while a linked game is in front.

RESOLUTION
  Tray menu > Resolution (or Settings window > Resolution tab). Applies to the monitor chosen in Position & monitor.
  - Type any size: 1280x960, 1280 960, 1920x1080@144 (optional refresh rate). Or pick from the list of modes your
    monitor/driver supports, or change only the refresh rate.
  - Modes the monitor does not report but the graphics driver does (for example 4:3 on a 16:9 screen) are tried too
    and marked with * in the lists; as a last resort the GPU is asked to stretch the picture. If nothing works the
    message lists the nearest supported sizes. Details of every refusal go to crosshair.log.
  - Like Windows, a manual change asks "Keep this resolution?" and goes back by itself after 10 s (no black-screen trap).
  - Reticle remembers the ORIGINAL resolution and puts it back when you quit (tray > Exit). If Reticle is killed or
    crashes, the next start restores it (only if the screen is still in the mode Reticle set).
  - Per-game resolution: link a game (open game / choose .exe / type path or name, same matching rules as game
    presets). The resolution switches when that game comes to the front. Optional "Go back when I leave the game"
    (after 3 s outside the game).
  - After every switch the crosshair is centered on the new screen. Reticle remembers the crosshair offset per
    resolution, so going back to a resolution brings your old position back. Overlay windows are re-placed
    automatically (also when a game or Windows changes the resolution on its own).
  - Games must run Borderless/Windowed. Windows rearranges desktop icons on any resolution change.

LOOK
  Name/icon: app is called Reticle (icon.ico is generated by make_icon.py; preview in icon_preview.png).
  Settings folder stays %APPDATA%\Crosshair so old presets keep working.
  Theme: dark warm black + crimson accent. Colors are the constants BG/PANEL/BTN/FG/ACC/MUTE
  at the top of crosshair.py.
  Tray icon mirrors the current crosshair (grey when hidden); tooltip shows preset + state.
  Tray menu is custom-drawn (dark red, multi-column for long lists). Esc or click outside closes it.
  If it ever fails to hook, the normal Windows menu is used (see crosshair.log).

ADAPTIVE COLOR
  Crosshair > Colors > "Adapt shape color to the background" (also in Settings window > Colors).
  About 3 times a second a small ring of screen pixels just outside the crosshair is read (in a background
  thread). If the background looks like the crosshair color it flips to the opposite color (or white/black if
  that is also too close) and goes back when the background changes. Shape color only (not hand drawing/images).
  Images or video sitting around the crosshair are read too. Some anti-cheats may dislike screen reading.

UPDATES  (GitHub Releases, repo set in crosshair.py: GITHUB_REPO = "FlxR0000/Reticle")
  To publish an update:
    1) in crosshair.py raise VERSION (e.g. "31"), run build.bat
    2) github.com/FlxR0000/Reticle > Releases > Draft a new release
       Tag: v31 (same number as VERSION) > drag dist\Reticle.exe onto the page > Publish release
  Everyone running Reticle (v30 or newer) sees "Update available" at the top of the tray menu within 6 hours
  (or on start). They click it > Update; Reticle downloads the exe, checks it, swaps itself and restarts.
  Tray > Settings > "Check for updates now" / "Check for updates automatically". The repo must be public.
  Running from .py: the update item just opens the download link.
