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

# Section headings, lower-case with "&" read as "and". A heading must be a whole line (an optional
# trailing ":" is allowed), so "Languages: Python" inside a section stays content.
# None = a recognised section that only ends the previous one; no facts come from it.
HEADINGS: dict[str, FactCategory | None] = {
    **dict.fromkeys(
        ["skills", "technical skills", "key skills", "core skills", "skills and tools",
         "technologies", "tech stack", "tools and technologies", "programming languages",
         "languages"],
        FactCategory.SKILL,
    ),
    **dict.fromkeys(
        ["projects", "academic projects", "personal projects", "key projects", "project work"],
        FactCategory.PROJECT,
    ),
    **dict.fromkeys(
        ["experience", "work experience", "professional experience", "internships", "internship",
         "internship experience", "employment history", "work history"],
        FactCategory.EXPERIENCE,
    ),
    **dict.fromkeys(
        ["education", "academic background", "academics", "educational qualifications"],
        FactCategory.EDUCATION,
    ),
    **dict.fromkeys(
        ["certifications", "certificates", "certification", "licenses and certifications",
         "courses and certifications"],
        FactCategory.CERTIFICATION,
    ),
    **dict.fromkeys(
        ["summary", "professional summary", "profile", "objective", "career objective",
         "about me", "achievements", "awards", "honors and awards", "hobbies", "interests",
         "extracurricular activities", "activities", "positions of responsibility", "leadership",
         "volunteering", "publications", "references", "declaration", "contact",
         "personal details", "personal information"],
        None,
    ),
}

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


def _heading_key(line: str) -> str:
    return " ".join(line.removesuffix(":").replace("&", " and ").lower().split())


def detect_sections(pages: list[str]) -> list[Section]:
    sections: list[Section] = []
    for page_no, page in enumerate(pages, 1):
        for line in page.splitlines():
            if not line:
                continue
            key = _heading_key(line)
            if key in HEADINGS:
                sections.append(Section(line.removesuffix(":").strip(), HEADINGS[key], page_no))
            elif sections:
                sections[-1].lines.append(line)
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


def _projects(line: str) -> list[str]:
    text = _entry_line(line)
    if text is None:
        return []
    title = TITLE_END.split(text, maxsplit=1)[0].strip()
    ok = title.lower() not in DETAIL_LABELS and _usable(title, max_len=60, max_words=8)
    return [title] if ok else []


def _experience(line: str) -> list[str]:
    text = _entry_line(line)
    return [text] if text is not None and _usable(text, max_words=20) else []


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
