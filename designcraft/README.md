# designcraft

Tools and field notes from setting a 336-page book, start to finish, in
[DesignCraft](https://github.com/storytold/designcraft) 0.18.0.

Two things live here: a small Tk application that applies parent pages by
paragraph style, and the list of things that cost me days, written down so the
next person setting a long book loses less time than I did.

Part of [Tessellae](../).

---

## Caveats — read these first

**Tested against DesignCraft 0.18.0 only**, Windows 11 x64, `.msi` build,
November 2026. The project ships fast — roughly eighteen minor versions in five
weeks at the time of writing. Anything below may be fixed, moved or renamed by
the time you read it.

**Not maintained.** A snapshot of one book, not a living document. Upstream is
the authority.

**Observed, not documented.** Everything here comes from watching the
application, not from a specification. Where I filed an issue, I link it. Where
I could not reproduce something, I say so rather than leaving it in.

**The tool's interface is in French.** The code is ASCII and readable; the
buttons are not translated. Patches welcome.

---

## `gabarits.pyw`

Applies parent pages ("gabarits") according to the paragraph style at the top of
each page — or to empty pages, even pages, odd pages, a range, or all of them.

DesignCraft runs neither ExtendScript nor UXP, so existing scripts for that
other application do not transfer; this is a rewrite over the JSON control
channel.

### Running it

Start DesignCraft with its control channel open:

```
designcraft.exe --control 7979
```

or use `designcraft-control.bat`. Open your document, then run
`gabarits-lancer.bat` (or `pythonw gabarits.pyw`). Needs Python 3 with Tk; no
third-party packages.

### How it goes

1. **Connecter** — fills the style and parent-page lists from the open document.
2. **Balayer le document** — about two minutes for 336 pages. Records, for every
   page, the paragraph style at the top and whether the page holds any text.
3. Tick the rules you want and pick a parent page for each.
4. **Aperçu** — page-by-page list; an arrow marks the ones that would change.
5. **Appliquer** — applies, then re-reads the document and verifies.

Rules stack from top to bottom and the last one wins: all pages, range, even,
odd, empty, character style, paragraph style.

The sweep has to be redone after any edit to the text, since pagination moved.

Presets are saved in `gabarits_presets.json`, next to the script.

### Three things in the code worth borrowing

`document.inspect` is called **once**, for geometry, and never inside the loop —
see the notes below for why. Per-frame reads go through `text.selectAt` and
`type.selectionAttrs`.

Page indices are converted to 0-based **at send time**, in `appliquer()`, never
in the working list.

After applying, the document is re-read and pages that did not change are
reported. `layout.pages.applyParent` answers `{"ok": true}` whether or not it
did anything, so verifying is the only way to know.

---

## `designcraft-control.bat`

Starts DesignCraft with the control channel open.

```
designcraft-control.bat
designcraft-control.bat 7979
designcraft-control.bat 7979 "C:\path\to\book.idml"
```

Port defaults to 7979. Set `DESIGNCRAFT_EXE` if the application is installed
where the script does not look. Dropping a document on the file opens it.

On macOS and Linux this is just `designcraft --control 7979`; the batch file
exists because Windows makes that tedious.

Protocol: one JSON request per line, one response per line, on
`127.0.0.1:<port>`.

```json
{"id": 1, "method": "engine.execute",
 "params": {"command": "layout.pages.delete", "params": {"pages": [0, 1, 2]}}}
```

`designcraft-cli commands` lists every command the build knows. The `Canal`
class at the top of `gabarits.pyw` is about thirty lines and is all you need to
talk to it.

---

## Field notes

### Page indices are 0-based in `layout.pages.*`

`layout.pages.delete` and `layout.pages.applyParent` count from 0. Neighbouring
commands do not: `layout.pageSize` is 1-based. An out-of-range index returns
`{"ok": true}` and does nothing.

Deleting "pages 336 to 379" of a 380-page document removes 337 to 380. The final
page count is identical either way, so nothing tells you.

Convert at send time, never in your working list.

Filed upstream: issue #2446.

### Delete pages in descending order

Renumbering shifts every index after the one you removed. Walk backwards.

### Turn off Smart Text Reflow before deleting pages

Preferences ▸ Type. Otherwise they come back.

### Never call `document.inspect` in a loop

It serializes the whole document: 229 KB on a 336-page book, against about
31 ms for a command returning a constant. For the selection,
`type.selectionAttrs` gives `paragraphStyle` and `characterStyle` in 5.9 KB.

Neither reports which frame or page a position is on, which is the one thing a
pagination script needs — hence the geometry pass in `gabarits.pyw`, which
matches frame centres against page rectangles by hand.

### `text.exitToFrame` returns the first frame of the story

Not the frame containing the selection.

### Find/Change fields interpret no escape sequences

Typing `\x{202F}` into the graphical Find/Change inserts those characters
literally. Go through the control channel, where JSON resolves the escape before
the command sees it.

### The nested-style delimiter *can* be typed — the field is hidden

I filed an issue saying a nested style could only end on a category from the
dropdown. Wrong: pick `chars` in that dropdown and a text field appears beside
it. Type `,` there and the run ends at the first comma; type `,.;` and it ends
at whichever comes first. Over the control channel the rule is
`{"kind": "chars", "chars": ","}`.

Kept here because the field does not exist until you guess the entry that
reveals it.

### Hidden characters do not mark U+202F

Ordinary space and U+00A0 are marked; the narrow no-break space is not, which
makes French punctuation spacing impossible to check by eye. Workaround: a loud
character style applied by GREP style over
`\x{00A0}|\x{202F}|\x{2008}|\x{2009}`, switched off before export.

### Optical margin alignment is a story-level setting

Window ▸ Type & Tables ▸ Story. One frame sets it for the whole story — but
notes, captions and back matter are separate stories, each needing its own.

### The Scripts panel cannot loop or branch

Window ▸ Utilities ▸ Scripts runs the same command language in a shortened form,
and the whole script collapses into **one undo step**, which is genuinely
useful. But there is no control flow: any logic lives outside, over the channel.

### Splitting a paragraph costs a full recomposition

Roughly fifteen seconds each on a 336-page document, because the whole story
recomposes. Work in descending position order so earlier offsets stay valid, and
make each unit atomic so an interrupted run can be restarted.

### Not reproducible, recorded so nobody chases it

One session showed `ui.inspect` at 4508 ms and `engine.commands` at 5055 ms on
the 336-page document. An hour later, same methods, same document: 91 ms and
502 ms. I never reproduced it and filed nothing. If you hit it, that is a real
observation and deserves better evidence than I had.

---

## Upstream

Bug reports and feature requests belong at
<https://github.com/storytold/designcraft>, not here.

---

*MIT, like everything in Tessellae. The notes are observations; check them
against the version you are running.*
