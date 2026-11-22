"""
Kikamba (Kamba) reader for river reports - BETA, needs checking by native speakers.

Makueni, Machakos and Kitui are Kamba-speaking counties, so people at a crossing may
report in Kikamba. Our NLP model was trained on Kiswahili/Sheng/English only, so this
small word list helps it recognise the most important Kikamba reports.

Words come from published sources (not invented), checked 22 Nov 2026:
  [PC]  Peace Corps Kikamba Self-Instruction Manual
        https://www.livelingua.com/peace-corps/Kikamba/Kikamba%20manual.pdf
  [LY]  Lugha Yangu Kamba dictionary  https://lughayangu.com/kamba
  [BL]  Bastin, Coupez & Mann 1999, Bantu lexicon, Kamba (E55)
        https://www.africamuseum.be/lexico_bantu/E/E55_kamba.pdf

  kĩw'ũ / kiwu      water                      [PC][LY][BL]
  usi / ũsi         river                      [PC][LY]
  mbua              rain;  kua = to rain       [PC][BL]
  kĩao              bridge                     [PC][LY]
  kũĩnga            to cross                   [PC]  ("twakĩla kĩao" = we crossed the bridge [LY])
  nzĩa              path / way                 [PC][BL]
  -ingĩ             much / many                [PC][BL]
  -nene             big                        [BL]
  mĩtukĩ            quickly / fast             [PC]
  kwongela          to add / increase          [PC]
  andũ / mũndũ      people / person            [PC][BL]
  syana / mwana     children / child           [PC]
  ng'ombe, mbũi     cow, goat                  [PC]
  mũtokaa, ngalĩ    car, vehicle               [PC]
  kĩsululu          bicycle                    [PC]
  -nini             small / a little           [PC]
  "usi wausia kiwu ndukilika" = "it's impossible to cross a river when it overflows"  [LY]
  Corrected by a Kikamba speaker for the report page (2026-11-22):
  "usi wausua kiwu" = water is rising / overflowing; "andũ nimekuinga usi" = people are crossing;
  "kindu kingi" = something else

Rules are deliberately cautious: a Kikamba message is only labelled when it clearly
matches; anything else stays "unsure" so a person (or Claude, if set up) reads it.
"""

import re
import unicodedata

WATER = {"kiwu", "usi", "usii"}
RAIN = {"mbua"}
BRIDGE = {"kiao", "kiaoni"}
PEOPLE = {"andu", "mundu", "syana", "mwana", "ngombe", "mbui", "mutokaa", "ngali",
          "kisululu", "boda", "pikipiki", "matatu", "lori"}
MARKERS = WATER | RAIN | BRIDGE | PEOPLE | {"nzia", "umunthi", "yu", "mituki", "kwongela"}


def normalise(text: str) -> list[str]:
    """Lower case, drop accents and apostrophes (kĩw'ũ -> kiwu), split into words."""
    t = unicodedata.normalize("NFKD", text.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"['’‘‛‟`]", "", t)
    return re.findall(r"[a-z]+", t)


def _much(tok: str) -> bool:      # kingi, mingi, ingi, kinene, munene ...
    return tok.endswith("ingi") or tok.endswith("nene")


def _overflow(tok: str) -> bool:  # wausia (overflowed), ndukilika (cannot be crossed)
    # "ausia" ending only: avoids Kiswahili words like usiache / usiangalie ("don't ...")
    return tok.endswith(("ausia", "ausua")) or tok == "ndukilika"


def _crossing(tok: str) -> bool:  # kuinga, ikuinga, kwinga, maiinga, nimaiinga ...
    return any(stem in tok for stem in ("iinga", "kuinga", "kwinga"))


def kikamba_classify(text: str) -> tuple[str, list[str]]:
    """Return (label or "", matched Kikamba words). Labels match the main NLP model."""
    toks = normalise(text)
    found = [t for t in toks if t in MARKERS or _much(t) or _overflow(t) or _crossing(t)]
    water = any(t in WATER for t in toks)
    rain = any(t in RAIN for t in toks)
    much = any(_much(t) for t in toks)
    rising = any(_overflow(t) for t in toks) or any(t in {"mituki", "kwongela"} or "ongela" in t for t in toks)

    if (water and (much or rising)) or (rain and much) or any(_overflow(t) for t in toks):
        return "WATER_RISING", found
    if any(t in PEOPLE for t in toks) and any(_crossing(t) for t in toks):
        return "PEOPLE_CROSSING", found
    if water and any(t.endswith("nini") for t in toks):
        return "ALL_CLEAR", found
    return "", found


def looks_kikamba(text: str) -> bool:
    return any(t in MARKERS for t in normalise(text))
