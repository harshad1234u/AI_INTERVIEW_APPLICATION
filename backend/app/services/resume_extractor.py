"""Deterministic resume processing: PDF bytes -> text -> heuristic sections -> candidate facts.

Resume content is untrusted *data*. It is only split and pattern-matched here, never evaluated or
followed. Every extracted fact is a verbatim substring of one resume line (kept as source_text);
nothing is inferred, summarised or invented. Facts are stored as PENDING_REVIEW and only an
explicit candidate action can approve them.

This stays the default path on every upload, AI or not. The optional ProfileAgent
(app/ai/profile_agent.py) emits the same ExtractedFact shape through the same PENDING_REVIEW path.
"""

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from io import BytesIO
from typing import Any

import pypdf
from pypdf import PdfReader

from app.models.resume import FACT_MAX_LENGTH, FactCategory, ResumeStatus

logger = logging.getLogger(__name__)

# ponytail: parsing runs inside the request; a crafted PDF can still cost seconds of CPU within
# these caps. Move it to a sandboxed worker with a timeout before this is exposed publicly.
MAX_PAGES = 10
MAX_TEXT_CHARS = 100_000
MAX_FACTS = 200
MIN_TEXT_CHARS = 20  # fewer letters/digits than this is not a readable resume

FAILURE_MESSAGES = {
    "unreadable": "We couldn't reliably read this file. Please upload a text-based PDF or enter "
    "your information manually.",
    "no_text": "We couldn't reliably read this resume. Please upload a text-based PDF or enter "
    "your information manually.",
    "too_long": f"This PDF is too long to process as a resume (maximum {MAX_PAGES} pages). "
    "Please upload just your resume.",
}
NO_FACTS_MESSAGE = (
    "We read your resume but couldn't automatically find skills, projects, experience, education "
    "or certifications. Headings are matched by simple rules, so some layouts aren't recognised."
)
TRUNCATED_MESSAGE = f"Only the first {MAX_FACTS} items were extracted for review."

# Section headings, lower-case with "&" and "/" read as "and". A heading is a whole line; leading
# numbering or markers ("01.", "#", "▸") and trailing punctuation (":", "——") are ignored, and a
# letter-spaced heading ("S K I L L S") is read as one word.
# None = a recognised section that only ends the previous one; no facts come from it (its text is
# still kept in parsed_json, so nothing the candidate wrote is silently dropped).
HEADINGS: dict[str, FactCategory | None] = {
    **dict.fromkeys(
        ["skills", "technical skills", "key skills", "core skills", "skills and tools",
         "technologies", "tech stack", "tools and technologies", "programming languages",
         "languages", "technical competencies", "core competencies", "competencies",
         "areas of expertise", "technical expertise", "expertise", "skill set", "skillset",
         "technical proficiencies", "tools"],
        FactCategory.SKILL,
    ),
    **dict.fromkeys(
        ["projects", "academic projects", "personal projects", "key projects", "project work",
         "selected projects", "selected work", "portfolio", "open source",
         "open source contributions", "open source projects", "side projects"],
        FactCategory.PROJECT,
    ),
    **dict.fromkeys(
        ["experience", "work experience", "professional experience", "internships", "internship",
         "internship experience", "employment history", "work history", "employment",
         "research", "research experience", "volunteer work", "volunteer experience",
         "volunteering", "industry experience", "relevant experience", "career history"],
        FactCategory.EXPERIENCE,
    ),
    **dict.fromkeys(
        ["education", "academic background", "academics", "educational qualifications",
         "academic qualifications", "qualifications", "education and training"],
        FactCategory.EDUCATION,
    ),
    **dict.fromkeys(
        ["certifications", "certificates", "certification", "licenses and certifications",
         "courses and certifications", "certifications and training", "licenses",
         "certifications and courses", "training and certifications"],
        FactCategory.CERTIFICATION,
    ),
    **dict.fromkeys(
        ["summary", "professional summary", "profile", "objective", "career objective",
         "about me", "achievements", "awards", "honors and awards", "hobbies", "interests",
         "extracurricular activities", "activities", "positions of responsibility", "leadership",
         "publications", "references", "declaration", "contact",
         "personal details", "personal information", "honors", "honours", "awards and honors",
         "achievements and awards", "awards and achievements", "coursework", "relevant coursework",
         "extra curricular activities", "co curricular activities", "patents", "presentations",
         "talks", "languages known", "spoken languages", "hobbies and interests", "about",
         "career summary", "executive summary", "overview"],
        None,
    ),
}
# The last word of a short heading that is not listed above ("Major Projects", "Teaching
# Experience", "Soft Skills"): what it names decides the category.
HEAD_NOUNS: dict[str, FactCategory | None] = {
    **dict.fromkeys(["skills", "competencies", "technologies"], FactCategory.SKILL),
    **dict.fromkeys(["projects"], FactCategory.PROJECT),
    **dict.fromkeys(["experience", "internships", "employment"], FactCategory.EXPERIENCE),
    **dict.fromkeys(["education"], FactCategory.EDUCATION),
    **dict.fromkeys(["certifications", "certificates"], FactCategory.CERTIFICATION),
    **dict.fromkeys(["publications", "awards", "achievements", "activities", "interests",
                     "honors", "honours", "summary", "references", "coursework"], None),
}
# "Skills: Python, SQL" on one line, outside any section that yields facts (a one-line resume,
# or a summary): only these unambiguous labels, so "Tech Stack: React" inside a project stays a
# project detail.
INLINE_HEADINGS = {"skills", "technical skills", "key skills", "core skills", "education",
                   "certifications", "certification", "projects", "experience",
                   "work experience"}
NOT_A_HEADING = object()
SMALL_WORDS = {"and", "of", "in", "the", "for", "to", "on", "at", "with"}
LEADING_MARK = re.compile(r"^(?:\d{1,2}[.)]|[#§▸►▪■●•◆◇*>\-–—|]+)\s*")
TRAILING_MARK = re.compile(r"[\s:.\-–—_|=~*]+$")
# A date, or a date range, at the end of a project or experience line ("Acme Mar 2022 – Present").
MONTH = (r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?"
         r"|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?")  # never "Juniper"
WHEN = rf"(?:(?:{MONTH}\s+)?(?:19|20)\d{{2}}|present|current|now|ongoing)"
TRAILING_DATE = re.compile(rf"[\s,(]+{WHEN}(?:\s*(?:[–—-]|to)\s*{WHEN})?\)?$", re.IGNORECASE)

BULLET = re.compile(r"^[•‣⁃∙▪●◦·*>\-–—]\s*")
LIST_SEPARATORS = ",;|•·"
# Where a project title ends: "TrustLens — ...", "TrustLens | ...", "TrustLens: ...", "TrustLens (..."
TITLE_END = re.compile(r"\s+[—–-]\s+|\s*\|\s*|:\s+|\s*\(")
URL = re.compile(r"https?://|www\.|github\.com|linkedin\.com", re.IGNORECASE)
DATE_ONLY = re.compile(
    r"(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?|present|current|\d{1,4}"
    r"|[\s/.,'\-–—])+",
    re.IGNORECASE,
)
# Non-bulleted detail lines inside a project entry, e.g. "Tech Stack: React, FastAPI".
DETAIL_LABELS = {"tech stack", "technologies", "technology", "tools", "stack", "tech", "link",
                 "links", "github", "role", "description"}


@dataclass(frozen=True)
class ExtractedFact:
    category: FactCategory
    fact: str
    section: str  # the heading as written in the resume
    source_text: str  # the full resume line the fact was taken from


@dataclass
class Section:
    heading: str
    category: FactCategory | None
    page: int
    lines: list[str] = field(default_factory=list)


@dataclass
class ProcessedResume:
    status: ResumeStatus
    raw_text: str | None
    parsed_json: dict[str, Any]
    facts: list[ExtractedFact]


def process_pdf(data: bytes) -> ProcessedResume:
    """Never raises: every outcome, including parser failure, is a ProcessedResume."""
    meta: dict[str, Any] = {"parser": "pypdf", "parser_version": pypdf.__version__}
    try:
        reader = PdfReader(BytesIO(data))
        meta["pages"] = len(reader.pages)
        if meta["pages"] > MAX_PAGES:
            return _not_processed(ResumeStatus.UNSUPPORTED, meta, "too_long")
        pages = [normalize_text(page.extract_text() or "") for page in reader.pages]
    except Exception as exc:  # malformed PDFs can raise almost anything inside the parser
        # Class name only: parser messages can quote file content.
        logger.warning("Resume PDF could not be parsed (%s)", type(exc).__name__)
        return _not_processed(ResumeStatus.FAILED, meta, "unreadable")

    raw_text = "\n\n".join(p for p in pages if p)
    if sum(c.isalnum() for c in raw_text) < MIN_TEXT_CHARS:
        return _not_processed(ResumeStatus.UNSUPPORTED, meta, "no_text")
    if len(raw_text) > MAX_TEXT_CHARS:
        return _not_processed(ResumeStatus.UNSUPPORTED, meta, "too_long")

    sections = detect_sections(pages)
    facts = extract_facts(sections)
    meta |= {
        "section_detection": "heuristic",
        "fact_extraction": "heuristic",
        "sections": [
            {"heading": s.heading, "category": s.category, "page": s.page, "text": "\n".join(s.lines)}
            for s in sections
        ],
        "facts_extracted": min(len(facts), MAX_FACTS),
        "facts_truncated": len(facts) > MAX_FACTS,
    }
    return ProcessedResume(ResumeStatus.PROCESSED, raw_text, meta, facts[:MAX_FACTS])


def status_message(parsed_json: dict[str, Any]) -> str | None:
    if failure := parsed_json.get("failure"):
        return FAILURE_MESSAGES[failure]
    if parsed_json.get("facts_extracted") == 0:
        return NO_FACTS_MESSAGE
    if parsed_json.get("facts_truncated"):
        return TRUNCATED_MESSAGE
    return None


def _not_processed(status: ResumeStatus, meta: dict[str, Any], failure: str) -> ProcessedResume:
    return ProcessedResume(status, None, {**meta, "failure": failure}, [])


# Typographic ligatures (ﬁ ﬂ ﬀ ...) are a font rendering artefact: "Certiﬁed" is "Certified".
LIGATURES = {cp: unicodedata.normalize("NFKC", chr(cp)) for cp in range(0xFB00, 0xFB07)}


def normalize_text(text: str) -> str:
    """Whitespace cleanup, ligatures expanded and NULs dropped (PostgreSQL text cannot store
    them). Words are never otherwise changed."""
    text = text.replace("\x00", "").translate(LIGATURES)
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _heading_text(line: str) -> str:
    """The heading as written, without numbering, markers or trailing punctuation."""
    return TRAILING_MARK.sub("", LEADING_MARK.sub("", line.strip())).strip()


def _heading_key(text: str) -> str:
    words = text.replace("&", " and ").replace("/", " and ").replace("-", " ").lower().split()
    if len(words) >= 3 and all(len(w) == 1 for w in words):  # "S K I L L S"
        words = ["".join(words)]
    if words and words[0] == "my":  # "My Projects"
        words = words[1:]
    return " ".join(words)


def heading_category(line: str) -> object:
    """The category of a heading line (None for a non-fact section), or NOT_A_HEADING."""
    text = _heading_text(line)
    if not text or len(text) > 50 or BULLET.match(line) or any(c.isdigit() for c in text):
        return NOT_A_HEADING
    key = _heading_key(text)
    if key in HEADINGS:
        return HEADINGS[key]
    words = key.split()
    # "Awards and Certifications", "Skills and Interests": the first part decides.
    if " and " in key:
        first = key.split(" and ")[0]
        if first in HEADINGS:
            return HEADINGS[first]
    # Only for heading-like lines: Title Case or capitals, never a sentence ("Built projects.").
    styled = text.isupper() or all(w[0].isupper() for w in text.split() if w.isalpha()
                                   and w.lower() not in SMALL_WORDS)
    sentence = line.rstrip().endswith((".", "!", "?", ","))
    if 1 < len(words) <= 4 and words[-1] in HEAD_NOUNS and styled and not sentence:
        return HEAD_NOUNS[words[-1]]
    return NOT_A_HEADING


def _inline_heading(line: str) -> tuple[str, FactCategory, str] | None:
    label, sep, rest = line.partition(":")
    key = _heading_key(_heading_text(label))
    if sep and rest.strip() and key in INLINE_HEADINGS and HEADINGS[key] is not None:
        return label.strip(), HEADINGS[key], rest.strip()
    return None


def detect_sections(pages: list[str]) -> list[Section]:
    sections: list[Section] = []
    current: Section | None = None
    for page_no, page in enumerate(pages, 1):
        for line in page.splitlines():
            if not line:
                continue
            category = heading_category(line)
            if category is not NOT_A_HEADING:
                current = Section(_heading_text(line), category, page_no)
                sections.append(current)
                continue
            inline = _inline_heading(line) if current is None or current.category is None else None
            if inline:
                # A one-line section; the lines after it still belong where they were.
                sections.append(Section(inline[0], inline[1], page_no, [inline[2]]))
            elif current is not None:
                current.lines.append(line)
            # Lines before the first heading (name, contact details) belong to no section.
    return sections


def extract_facts(sections: list[Section]) -> list[ExtractedFact]:
    facts: list[ExtractedFact] = []
    seen: set[tuple[FactCategory, str]] = set()
    for section in sections:
        if section.category is None:
            continue
        for line in section.lines:
            for value in EXTRACTORS[section.category](line):
                key = (section.category, value.lower())
                if key not in seen:
                    seen.add(key)
                    facts.append(ExtractedFact(section.category, value, section.heading, line))
    return facts


def _strip_bullet(line: str) -> tuple[bool, str]:
    match = BULLET.match(line)
    return (True, line[match.end():]) if match else (False, line)


def _usable(value: str, max_len: int = FACT_MAX_LENGTH, max_words: int | None = None) -> bool:
    return (
        0 < len(value) <= max_len
        and (max_words is None or len(value.split()) <= max_words)
        and any(c.isalpha() for c in value)
        and not URL.search(value)
        and not DATE_ONLY.fullmatch(value)
    )


def _split_list(text: str) -> list[str]:
    """Split on , ; | • · but not inside brackets: "SQL (MySQL, PostgreSQL)" stays one item."""
    items, depth, start = [], 0, 0
    for i, ch in enumerate(text):
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(depth - 1, 0)
        elif ch in LIST_SEPARATORS and depth == 0:
            items.append(text[start:i])
            start = i + 1
    items.append(text[start:])
    return [item.strip() for item in items]


def _skills(line: str) -> list[str]:
    text = _strip_bullet(line)[1]
    # "Languages: Python, Java" -> drop the sub-label, but keep "Python: 2 years" whole.
    label, sep, rest = text.partition(": ")
    if sep and len(label) <= 30 and len(_split_list(rest)) > 1:
        text = rest
    return [
        item for item in _split_list(text)
        if _usable(item, max_len=50, max_words=5)
        and item[-1] not in ".!?:"  # sentences are not skills
        and item.lower() != "etc"
    ]


def _entry_line(line: str) -> str | None:
    """Project/experience entries are non-bulleted lines; bullets are details about them."""
    bullet, text = _strip_bullet(line)
    return None if bullet or text.endswith(".") else text


def _without_date(text: str) -> str:
    """'Library System 2024' -> 'Library System': the dates stay in the source line."""
    return TRAILING_DATE.sub("", text).rstrip(" ,;|–—-")


def _projects(line: str) -> list[str]:
    text = _entry_line(line)
    if text is None:
        return []
    title = _without_date(TITLE_END.split(text, maxsplit=1)[0].strip())
    ok = title.lower() not in DETAIL_LABELS and _usable(title, max_len=60, max_words=8)
    return [title] if ok else []


def _experience(line: str) -> list[str]:
    text = _entry_line(line)
    text = _without_date(text) if text is not None else None
    return [text] if text and _usable(text, max_words=20) else []


def _whole_line(line: str) -> list[str]:
    text = _strip_bullet(line)[1]
    return [text] if _usable(text) else []


EXTRACTORS = {
    FactCategory.SKILL: _skills,
    FactCategory.PROJECT: _projects,
    FactCategory.EXPERIENCE: _experience,
    FactCategory.EDUCATION: _whole_line,
    FactCategory.CERTIFICATION: _whole_line,
}
