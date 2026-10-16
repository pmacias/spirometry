// Field guide v2: page style, the number function, v1's boxes, figures and tables.
// Every number in the text comes from numbers.json (python -m spirometry.numbers) through
// #n("key"); a key that isn't there stops the compile. The build (python -m spirometry.writeup
// build) also lints the chapters for hand-typed digits.

#let data = json("numbers.json")
#let numbers = data.numbers
#let build-info = data.build

// The formatted text of a numbers.json key. A missing key fails the compile.
#let n(key) = {
  if key not in numbers {
    panic("numbers.json has no key '" + key + "' (add it to spirometry.numbers)")
  }
  numbers.at(key).text
}

// ---------------------------------------------------------------------------- colours

#let ink = luma(25)
#let muted = luma(95)
#let accent = rgb("#b5532f")     // chapter labels, stop-and-check
#let c-plain = rgb("#2f6f8f")    // in plain words
#let c-project = rgb("#5a7d2a")  // in your project
#let c-watch = rgb("#a33b3b")    // watch out
#let c-skill = rgb("#6b4f9a")    // skill
#let c-picture = rgb("#8a6d1f")  // a picture to hold on to

// ---------------------------------------------------------------------------- boxes

#let _box(label, colour, body) = block(
  width: 100%,
  inset: (left: 12pt, right: 10pt, y: 9pt),
  fill: colour.lighten(92%),
  stroke: (left: 2.5pt + colour),
  breakable: false,
  above: 1.1em,
  below: 1.1em,
  {
    text(size: 7.5pt, weight: "bold", tracking: 0.08em, fill: colour, upper(label))
    v(0.35em, weak: true)
    body
  },
)

// v1's boxes. `picture` holds the everyday analogy; `words` the terms with their meanings.
#let picture(body) = _box("A picture to hold on to", c-picture, body)
#let words(body) = _box("The words", muted, body)
#let project(body) = _box("In your project", c-project, body)
#let plain(body) = _box("In plain words", c-plain, body)
#let watch(body) = _box("Watch out", c-watch, body)
// New in v2: the general data-science skill a section exercises.
#let skill(body) = _box("Skill", c-skill, body)

// The one-line subtitle under a chapter title (v1's style).
#let lead(body) = block(above: -0.6em, below: 1.3em, text(size: 12pt, fill: muted, body))

// Inline labels for what SPIROMETRY.md / PLAN.md mark as open.
#let unverified(body) = text(fill: c-watch)[#body #super[(unverified)]]
#let pending(body) = text(fill: c-watch)[#body #super[(pending)]]

// ------------------------------------------------------------------ stop and check

// #check(([question], [answer]), ...): numbered chapter.question; the answers are collected
// by #answer-key() in Appendix A, so they never sit next to the questions.
#let _qcount = counter("check-question")

#let check(..items) = _box(
  "Stop and check: answer out loud before moving on (answers in Appendix A)",
  accent,
  {
    for item in items.pos() {
      let (q, a) = item
      _qcount.step()
      context {
        let num = str(counter(heading).get().first() - 1) + "." + str(_qcount.get().first())
        block(above: 0.6em, below: 0.6em)[*#num* #h(0.4em) #q #metadata((num: num, a: a)) <answer>]
      }
    }
  },
)

#let answer-key() = context {
  for m in query(<answer>) {
    block(above: 0.5em, below: 0.5em)[*#m.value.num* #h(0.4em) #m.value.a]
  }
}

// ------------------------------------------------------------------------ figures

// The build passes the figure files that exist (writeup/figures/<name>.png) as
// sys.inputs.figures; any other figure prints a labelled placeholder, so the guide compiles
// before scripts/writeup/figures.py has been run.
#let _available = sys.inputs.at("figures", default: "").split(",").filter(s => s != "")

#let fig(name, caption) = {
  if name in _available {
    figure(image("figures/" + name + ".png", width: 100%), caption: caption)
  } else {
    figure(
      block(
        width: 100%,
        height: 4.5cm,
        fill: luma(244),
        stroke: (paint: luma(160), dash: "dashed"),
        align(center + horizon, text(size: 9pt, fill: muted)[
          Figure not drawn yet: #raw(name) \
          (scripts/writeup/figures.py writes #raw("writeup/figures/" + name + ".png"))
        ]),
      ),
      caption: caption,
    )
  }
}

// ------------------------------------------------------------------------- tables

// A flexible column width for ftable, so chapter files carry no digits.
#let rest = 1fr

#let ftable(..args) = table(
  stroke: (x, y) => if y == 0 { (bottom: 0.6pt + ink) } else { (bottom: 0.3pt + luma(205)) },
  inset: (x: 6pt, y: 5pt),
  align: left,
  ..args,
)

// A table in slightly smaller type (glossary, numbers on one page).
#let small-table(..args) = {
  set text(size: 9.5pt)
  ftable(..args)
}

// Appendix E: one interview question and its short answer.
#let qa(q, a) = block(above: 1em, below: 0.4em, breakable: false)[*#q* \ #a]

// ---------------------------------------------------------------------- page setup

// Chapters are numbered from zero, as in v1; sections are not numbered.
#let chapter-numbering(..nums) = {
  let n = nums.pos()
  if n.len() == 1 { str(n.first() - 1) }
}

#let setup(doc) = {
  set document(title: "What Did the Patch Do?")
  set page(
    paper: "a4",
    margin: (x: 2.3cm, top: 2.2cm, bottom: 2.4cm),
    footer: context {
      if counter(page).get().first() > 1 {
        set text(size: 8pt, fill: muted)
        [Spirometry: What Did the Patch Do? #h(1fr) #counter(page).display()]
      }
    },
  )
  set text(size: 10.5pt, fill: ink)
  set par(leading: 0.68em, spacing: 1.05em)
  set heading(numbering: chapter-numbering, supplement: [Chapter])
  show heading.where(level: 1): it => {
    pagebreak(weak: true)
    _qcount.update(0)
    block(below: 1.4em, {
      if it.numbering != none {
        context text(size: 8.5pt, weight: "bold", tracking: 0.1em, fill: accent,
          upper(it.supplement) + " " + counter(heading).display(it.numbering))
        v(0.2em)
      }
      text(size: 19pt, weight: "bold", it.body)
    })
  }
  show heading.where(level: 2): it => block(above: 1.5em, below: 0.7em,
    text(size: 12.5pt, weight: "bold", it.body))
  show heading.where(level: 3): it => block(above: 1.1em, below: 0.5em,
    text(size: 10.5pt, weight: "bold", it.body))
  doc
}

// ------------------------------------------------------------------------- title page

#let title-page() = {
  set page(footer: none)
  v(18%)
  text(size: 11pt, weight: "bold", tracking: 0.2em, fill: accent, "SPIROMETRY")
  v(0.4em)
  text(size: 30pt, weight: "bold", "What Did the Patch Do?")
  v(0.6em)
  text(size: 12pt, fill: muted, "A field guide to the statistics behind your results")
  if build-info.at("sample", default: false) {
    v(1.5em)
    block(fill: c-watch.lighten(85%), inset: 8pt, stroke: 1pt + c-watch,
      text(weight: "bold", fill: c-watch,
        "SAMPLE DATA: built from synthetic outputs; no number here is a result."))
  }
  v(1fr)
  set text(size: 9pt, fill: muted)
  grid(
    columns: (auto, auto),
    column-gutter: 1.2em,
    row-gutter: 0.5em,
    [Run tables built], n("build.tables_built_at"),
    [Snapshot], [#n("snapshot.pages") pages, #n("snapshot.records") records],
    [Play dates], [#n("snapshot.start_date") to #n("snapshot.end_date")],
    [Parser], n("build.parser_version"),
  )
  pagebreak()
}
