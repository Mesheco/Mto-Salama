"""
Mto Salama - agent pipeline (Jac + byLLM + Claude).

The crossing and its community reports live on a GRAPH:
    Crossing --> Report, Report, ...
A walker (RiskCheck) travels the graph and runs four agents in order:

  1. Listener   (LLM)  classifies each community message      -> classify_report
  2. Fusion     (code) combines upstream rain + reports        -> fuse
  3. Skeptic    (code) checks data age and missing data        -> skeptic
  4. Messenger  (LLM)  drafts the bilingual alert              -> write_alert

Safety decisions (2, 3) are plain code on purpose: predictable, explainable,
and they still work when the AI is offline. If Claude can't be reached,
a simple keyword reader and alert templates take over.

Modes (set MTO_MODEL in .env):
  anthropic/claude-haiku-5-5  -> Claude reads messages and writes alerts
  mockllm                     -> free demo: keyword reader + templates, no key

From the terminal:   jac run agents.jac
From Python/app:     import jaclang; import agents; agents.run_check(...)
"""

import os;
import json;
import from dotenv { load_dotenv }
import from byllm.lib { Model }

with entry {
    load_dotenv();
}

glob MODEL_NAME = os.getenv("MTO_MODEL", "anthropic/claude-haiku-5-5"),
     USE_LLM = MODEL_NAME != "mockllm";

glob llm = Model(model_name=MODEL_NAME);

glob FOOTER_SW = "Fuata maonyo rasmi. Dharura: piga 1199.",
     FOOTER_EN = "Follow official warnings. Emergency: call 1199.";

# ---------------------------------------------------------------- types

enum ReportType {
    WATER_RISING,
    PEOPLE_CROSSING,
    INFRASTRUCTURE_DAMAGED,
    ALL_CLEAR,
    IRRELEVANT
}

sem ReportType = "What a short community SMS/WhatsApp message about a river crossing is reporting.";
sem ReportType.WATER_RISING = "River or drift water is rising, flowing fast, or flooding.";
sem ReportType.PEOPLE_CROSSING = "People, vehicles or animals are crossing or about to cross.";
sem ReportType.INFRASTRUCTURE_DAMAGED = "A bridge, drift, road or culvert is damaged or washed away.";
sem ReportType.ALL_CLEAR = "Water is low and normal; no danger seen.";
sem ReportType.IRRELEVANT = "Not about river conditions (greetings, spam, other topics).";

obj Alert {
    has swahili: str,
        english: str;
}

sem Alert.swahili = "Short alert in simple Kiswahili, under 160 characters.";
sem Alert.english = "The same alert in simple English, under 160 characters.";

obj Assessment {
    has status: str,
        reasons: list[str],
        confidence: str;
}

# ---------------------------------------------------------------- graph

node Crossing {
    has name: str,
        upstream_rain_3d_mm: float,   # rain in upstream hills, last 3 days; -1 = unknown
        data_age_hours: float,        # how old the weather data is
        ml_level: str = "",           # surge model: high / medium / low; "" = no model
        ml_prob: float = -1.0,        # surge model probability (0-1); -1 = no model
        ml_reasons: list[str] = [];   # surge model explanation
}

node Report {
    has text: str,
        kind: str = "",
        read_by: str = "";
}

# ---------------------------------------------------------------- agent 1: listener

def classify_report(message: str) -> ReportType by llm();

sem classify_report = "Classify a community message about a seasonal river crossing in Kenya. Messages may mix Kiswahili, Sheng and English.";

"""Free backup reader: simple keywords in Kiswahili, Sheng and English."""
def keyword_classify(message: str) -> str {
    t = message.lower();
    damaged = ["imeharibika", "imesombwa", "imevunjika", "broken", "washed away", "collapsed", "damaged"];
    rising = ["maji imejaa", "imejaa", "kujaa", "mafuriko", "inafurika", "nguvu", "rising", "flood", "swollen", "fast"];
    crossing = ["wanavuka", "anavuka", "kuvuka", "crossing", "boda", "gari", "lorry"];
    clear = ["maji iko chini", "maji kidogo", "shwari", "low water", "normal", "all clear"];
    for w in damaged { if w in t { return "INFRASTRUCTURE_DAMAGED"; } }
    for w in rising { if w in t { return "WATER_RISING"; } }
    for w in crossing { if w in t { return "PEOPLE_CROSSING"; } }
    for w in clear { if w in t { return "ALL_CLEAR"; } }
    return "IRRELEVANT";
}

# ---------------------------------------------------------------- agent 2: fusion

def fuse(
    rain_mm: float,
    kinds: list[str],
    ml_level: str,
    ml_prob: float,
    ml_reasons: list[str]
) -> Assessment {
    reasons: list[str] = [];
    rising = kinds.count("WATER_RISING") + kinds.count("INFRASTRUCTURE_DAMAGED");
    status = "SAFE-LOOKING";

    # Machine signal: the trained surge model when available, simple rain rules otherwise.
    if ml_level in ["high", "medium", "low"] {
        if ml_level == "high" {
            status = "DO NOT CROSS";
        } elif ml_level == "medium" {
            status = "CAUTION";
        }
        reasons.append(f"Surge model: {ml_prob:.0%} chance the river surges by tomorrow.");
        for r in ml_reasons {
            reasons.append(r);
        }
    } elif rain_mm >= 40.0 {
        status = "DO NOT CROSS";
        reasons.append(f"{rain_mm:.0f} mm of rain fell upstream in the last 3 days.");
    } elif rain_mm >= 20.0 {
        status = "CAUTION";
        reasons.append(f"{rain_mm:.0f} mm of rain fell upstream in the last 3 days.");
    } elif rain_mm >= 0.0 {
        reasons.append(f"Only {rain_mm:.0f} mm of rain upstream in the last 3 days.");
    }

    # Trust rule: community reports alone need 2+ to reach DO NOT CROSS.
    if rising >= 2 {
        status = "DO NOT CROSS";
        reasons.append(f"{rising} community reports say the water is rising or the drift is damaged.");
    } elif rising == 1 and status == "SAFE-LOOKING" {
        status = "CAUTION";
        reasons.append("1 community report says the water is rising, but rain data does not confirm it. Check before crossing.");
    } elif rising == 1 {
        reasons.append("A community report confirms rising water.");
    }

    if kinds.count("PEOPLE_CROSSING") > 0 and status != "SAFE-LOOKING" {
        reasons.append("People are reported to be crossing now - urgent.");
    }
    return Assessment(status=status, reasons=reasons, confidence="medium");
}

# ---------------------------------------------------------------- agent 3: skeptic

def skeptic(
    a: Assessment,
    rain_mm: float,
    data_age_hours: float,
    kinds: list[str],
    ml_level: str
) -> Assessment {
    rising = kinds.count("WATER_RISING") + kinds.count("INFRASTRUCTURE_DAMAGED");
    machine_says_low = ml_level == "low" or (ml_level == "" and rain_mm >= 0.0 and rain_mm < 20.0);
    if machine_says_low and rising >= 1 {
        a.reasons.append(
            "Rain data and community reports disagree. Reports from the river are trusted here, "
            + "because rain in a small catchment can be missed by the weather model."
        );
        a.confidence = "low";
    }
    if rain_mm < 0.0 {
        if a.status == "SAFE-LOOKING" {
            a.status = "CAUTION";
        }
        a.reasons.insert(0, "Upstream rain data is unavailable - treat as Caution, never as safe.");
        a.confidence = "low";
    } elif data_age_hours > 6.0 {
        if a.status == "SAFE-LOOKING" {
            a.status = "CAUTION";
        }
        a.reasons.append(f"Weather data is {data_age_hours:.0f} hours old - treat with caution.");
        a.confidence = "low";
    }
    if a.status == "SAFE-LOOKING" {
        a.reasons.append("Low risk is not zero risk: look at the water before crossing.");
    }
    return a;
}

def check_wording(alert: Alert) -> Alert {
    banned = ["guaranteed", "100%", "completely safe", "no risk", "salama kabisa", "hakuna hatari"];
    for word in banned {
        if word in alert.english.lower() or word in alert.swahili.lower() {
            return template_alert("CAUTION", "the crossing");
        }
    }
    return alert;
}

# ---------------------------------------------------------------- agent 4: messenger

def write_alert(crossing_name: str, status: str, reasons: list[str]) -> Alert by llm();

sem write_alert = "Write a calm, clear SMS alert for villagers who use this river crossing. State the status and the main reason. Never say a crossing is guaranteed or completely safe.";

"""Free backup messenger: fixed bilingual templates per status."""
def template_alert(status: str, crossing_name: str, rain_heavy: bool = True) -> Alert {
    if status == "DO NOT CROSS" and rain_heavy {
        return Alert(
            swahili=f"TAHADHARI: Usivuke {crossing_name} leo. Mvua kubwa imenyesha juu ya mto. Subiri maji yapungue.",
            english=f"WARNING: Do not cross {crossing_name} today. Heavy rain fell upstream. Wait for the water to go down."
        );
    }
    if status == "DO NOT CROSS" {
        return Alert(
            swahili=f"TAHADHARI: Usivuke {crossing_name} leo. Wakazi wanaripoti maji yanaongezeka. Subiri maji yapungue.",
            english=f"WARNING: Do not cross {crossing_name} today. Residents report rising water. Wait for the water to go down."
        );
    }
    if status == "CAUTION" {
        return Alert(
            swahili=f"ANGALIA: Kuwa mwangalifu {crossing_name}. Maji yanaweza kuongezeka ghafla. Usivuke maji yanayotiririka.",
            english=f"CAUTION: Take care at {crossing_name}. Water may rise suddenly. Do not cross flowing water."
        );
    }
    return Alert(
        swahili=f"Hali ya {crossing_name} inaonekana tulivu, lakini angalia maji kabla ya kuvuka.",
        english=f"{crossing_name} looks calm, but check the water before crossing."
    );
}

# Claude returns typed objects; accept text too.
def as_kind(x: object) -> str {
    return str(x).strip().strip('"').split(".")[-1];
}

def as_alert(x: object) -> Alert {
    if isinstance(x, Alert) {
        return x;
    }
    d = dict(json.loads(str(x)));
    return Alert(swahili=str(d.get("swahili", "")), english=str(d.get("english", "")));
}

# ---------------------------------------------------------------- walker

walker RiskCheck {
    has result: dict[str, object] = {},
        trace: list[str] = [];

    can assess with Crossing entry {
        kinds: list[str] = [];
        report_rows: list[dict[str, str]] = [];
        for r in [here -->][?:Report] {
            r.read_by = "keywords";
            r.kind = keyword_classify(r.text);
            if USE_LLM {
                try {
                    r.kind = as_kind(classify_report(r.text));
                    r.read_by = "Claude";
                } except Exception {
                    r.read_by = "keywords (AI offline)";
                }
            }
            kinds.append(r.kind);
            report_rows.append({"text": r.text, "kind": r.kind, "read_by": r.read_by});
            self.trace.append(f"Listener: '{r.text}' -> {r.kind} ({r.read_by})");
        }

        if here.ml_level {
            self.trace.append(f"Surge model (ML): {here.ml_prob:.0%} chance of surge -> {here.ml_level} risk");
        } else {
            self.trace.append("Surge model (ML): not available -> simple rain rules used");
        }
        a = skeptic(
            fuse(here.upstream_rain_3d_mm, kinds, here.ml_level, here.ml_prob, here.ml_reasons),
            here.upstream_rain_3d_mm,
            here.data_age_hours,
            kinds,
            here.ml_level
        );
        self.trace.append(f"Fusion + Skeptic: {a.status} ({a.confidence} confidence)");

        rain_driven = here.ml_level == "high" or here.upstream_rain_3d_mm >= 40.0;
        alert = template_alert(a.status, here.name, rain_driven);
        written_by = "template";
        if USE_LLM {
            try {
                alert = check_wording(as_alert(write_alert(here.name, a.status, a.reasons)));
                written_by = "Claude";
            } except Exception {
                written_by = "template (AI offline)";
            }
        }
        self.trace.append(f"Messenger: alert written by {written_by}");

        self.result = {
            "crossing": here.name,
            "status": a.status,
            "confidence": a.confidence,
            "reasons": a.reasons,
            "reports": report_rows,
            "alert_sw": f"{alert.swahili} {FOOTER_SW}",
            "alert_en": f"{alert.english} {FOOTER_EN}",
            "alert_by": written_by,
            "model": MODEL_NAME,
            "ml_level": here.ml_level,
            "ml_prob": here.ml_prob,
            "trace": self.trace
        };
    }
}

"""Run the full agent chain for one crossing. Used by the app."""
def run_check(
    crossing_name: str,
    rain_3d_mm: float,
    data_age_hours: float,
    messages: list[str],
    ml: dict[str, object] = {}
) -> dict[str, object] {
    # Fresh graph each time (not linked to root, so nothing is saved between runs).
    c = Crossing(
        name=crossing_name,
        upstream_rain_3d_mm=rain_3d_mm,
        data_age_hours=data_age_hours
    );
    if ml.get("available") {
        c.ml_level = str(ml.get("level", ""));
        c.ml_prob = float(str(ml.get("probability", -1.0)));
        c.ml_reasons = [str(r) for r in list(ml.get("reasons", []))];
    }
    for m in messages {
        if m.strip() {
            c ++> Report(text=m.strip());
        }
    }
    w = c spawn RiskCheck();
    return w.result;
}

# ---------------------------------------------------------------- terminal demo

with entry:__main__ {
    print(f"Model: {MODEL_NAME}\n");
    print("Scenario: sunny at the crossing, heavy rain upstream overnight.\n");
    res = run_check(
        "Mto Kavuthu drift",
        52.0,
        1.0,
        [
            "Maji imeanza kujaa kwa drift, inakuja na nguvu",
            "watu wanavuka na boda saa hii",
            "Habari za asubuhi wote"
        ]
    );
    trace_lines: list = list(res["trace"]);
    for line in trace_lines {
        print(f"  {line}");
    }
    print(f"\nSTATUS: {res['status']}");
    reason_lines: list = list(res["reasons"]);
    for reason in reason_lines {
        print(f"  - {reason}");
    }
    print(f"\nSW: {res['alert_sw']}");
    print(f"EN: {res['alert_en']}");
    print("\nChief must approve before anything is sent.");
}
