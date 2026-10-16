// Field guide v2: "What Did the Patch Do?". Build: python -m spirometry.writeup build
// (numbers -> digit lint -> privacy -> figures -> typst compile to writeup/build/).
#import "style.typ": *

#show: setup

#title-page()

#outline(title: [Contents], depth: 1, indent: auto)

#include "chapters/00_project.typ"
#include "chapters/01_data.typ"
#include "chapters/02_confounding.typ"
#include "chapters/03_counting.typ"
#include "chapters/04_noise.typ"
#include "chapters/05_did.typ"
#include "chapters/06_regression.typ"
#include "chapters/07_checks.typ"
#include "chapters/08_placebo.typ"
#include "chapters/09_results.typ"
#include "chapters/10_dose.typ"
#include "chapters/11_rulers.typ"
#include "chapters/12_explanations.typ"
#include "chapters/13_wins.typ"
#include "chapters/14_open.typ"

// Appendices: lettered.
#counter(heading).update(0)
#set heading(numbering: "A", supplement: [Appendix])

#include "chapters/a_answers.typ"
#include "chapters/b_glossary.typ"
#include "chapters/c_numbers.typ"
#include "chapters/d_open.typ"
