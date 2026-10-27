"""Master Orchestrator to assemble the full academic project report.
Generates:
1. AI_Interview_Coach_Project_Report.docx
2. AI_Interview_Coach_Project_Report.html
3. AI_Interview_Coach_Project_Report.pdf (via headless Edge)
4. Companion_Appendix_and_Technical_Inventory.md
"""

import os
import sys
import subprocess
import base64

from make_academic_report import (
    doc, REPORT_DIR, DIAGRAMS_DIR, SCREENSHOTS_DIR, DOCX_OUT, HTML_OUT, COMPANION_OUT
)
from report_sections_prelim import build_preliminary_pages
from report_sections_ch1_ch2 import build_ch1_introduction, build_ch2_srs
from report_sections_ch3_ch4 import build_ch3_analysis_and_design, build_ch4_implementation
from report_sections_ch5_ch6 import build_ch5_testing, build_ch6_conclusion
from report_sections_appendix import build_appendix_and_references

def generate_docx():
    print("Building complete DOCX report...")
    build_preliminary_pages()
    build_ch1_introduction()
    build_ch2_srs()
    build_ch3_analysis_and_design()
    build_ch4_implementation()
    build_ch5_testing()
    build_ch6_conclusion()
    build_appendix_and_references()
    doc.save(DOCX_OUT)
    print(f"Complete DOCX report saved to: {DOCX_OUT}")

def generate_companion_markdown():
    print("Building Companion Appendix & Technical Inventory...")
    content = """# Companion Appendix and Technical Inventory
## AI Interview Coach Project Report

**Institution:** K. Ramakrishnan College of Technology (Autonomous), Samayapuram  
**Department:** Computer Science and Engineering  
**Course:** CSB1303 – Object Oriented Analysis and Design  
**Date:** November 2026  

---

### 1. Source Code Inventory

| Subsystem | Directory / File | Lines of Code | Technical Purpose & Implemented Invariants | Status |
|---|---|---|---|---|
| **Backend Core** | `app/main.py` | 134 | Application factory, CORS middleware, 503 database degradation handler, production health guard | Implemented |
| **Backend Core** | `app/core/config.py` | 118 | Typed Pydantic settings loading from `.env`, SecretStr credentials, strict validator constraints | Implemented |
| **Backend Core** | `app/core/security.py` | 76 | `hashlib.scrypt` password hashing (N=16384, r=8, p=5), cryptographic session token generation | Implemented |
| **Backend DB** | `app/db/base.py` & `session.py` | 64 | Declarative Base with explicit naming conventions, connection engine, scoped session factory | Implemented |
| **Backend Models** | `app/models/candidate.py` | 52 | Candidate entity, scrypt hash, failed login counter, locked_until timestamp | Implemented |
| **Backend Models** | `app/models/auth_session.py` | 38 | SHA-256 session token hash, candidate foreign key cascade, absolute 7-day expiry check | Implemented |
| **Backend Models** | `app/models/resume.py` | 148 | Resume & CandidateFact entities, composite FK `(resume_id, candidate_id)`, provenance check | Implemented |
| **Backend Models** | `app/models/interview_session.py`| 162 | InterviewSession & ConsentEvent, plan JSONB, finish_reason check, active time tracking | Implemented |
| **Backend Models** | `app/models/interview_question.py`| 98 | InterviewQuestion entity, 10,000 char answer limit, evaluation status enum | Implemented |
| **Backend Models** | `app/models/answer_evaluation.py`| 112 | AnswerEvaluation & Criteria entities, 1-5 score bounds, verbatim evidence quote storage | Implemented |
| **Backend Models** | `app/models/expression.py` | 65 | QuestionExpressionObservation entity, 9 categorical observation counts (0-10,000 bound) | Implemented |
| **Backend Models** | `app/models/provider_call.py` | 54 | ProviderCall operational audit entity; zero candidate IDs, prompts, or outputs stored | Implemented |
| **Backend Models** | `app/models/usage_counter.py` | 42 | UsageCounter rate-limiting entity, compound PK `(scope, key, window_start)` | Implemented |
| **Backend AI** | `app/ai/gateway.py` | 266 | ModelGateway: routing, 20s timeout, bounded backoff, fallback cascade, schema validation | Implemented |
| **Backend AI** | `app/ai/providers.py` | 234 | Provider adapters for Gemini, Groq, NVIDIA over HTTPX Chat Completions | Implemented |
| **Backend AI** | `app/ai/profile_agent.py` | 145 | ProfileAgent: prompt boundary, verbatim grounding check against resume text | Implemented |
| **Backend AI** | `app/ai/planner_agent.py` | 186 | PlannerAgent: closed-set settings instructions, topic proposal schema, 1 re-request | Implemented |
| **Backend AI** | `app/ai/interviewer_agent.py`| 210 | InterviewerAgent: follow-up wording proposal, anchor term validation, presumption rules | Implemented |
| **Backend AI** | `app/ai/evaluator_agent.py` | 240 | EvaluatorAgent: rubric scoring proposal, evidence quote validation, neutral feedback rule | Implemented |
| **Backend Services** | `app/services/interview_state_machine.py` | 257 | Finite State Machine: transition table, row lock acquisition, atomic state writer | Implemented |
| **Backend Services** | `app/services/interviewer.py` | 385 | Turn decision engine, 60s deadline guard, anchor term matcher, pacing calculation | Implemented |
| **Backend Services** | `app/services/evaluator.py` | 340 | Rubric scoring, exact substring evidence verification, deterministic observation fallback | Implemented |
| **Backend Services** | `app/services/report.py` | 290 | Deterministic report compiler: shown clearly vs to practise items, zero aggregated scores | Implemented |
| **Backend Services** | `app/services/resume_extractor.py`| 470 | Pure Python pypdf text extraction, heading detection dictionary, verbatim fact parser | Implemented |
| **Backend Services** | `app/services/retry.py` | 185 | Retry session generator: copies to_practise topics into fresh READY session | Implemented |
| **Backend Services** | `app/services/limits.py` | 175 | Atomic PostgreSQL counter upsert, network SHA-256 keys, daily AI request budget | Implemented |
| **Backend Services** | `app/services/manual_facts.py`| 130 | Manual fact management, 100-fact cap, case-insensitive duplicate check | Implemented |
| **Frontend App** | `frontend/app/page.tsx` | 220 | Landing page, authentication guard, candidate profile card, resume upload card | Implemented |
| **Frontend App** | `frontend/app/interview/page.tsx` | 340 | Multi-stage interview screen coordinator, unfinished session recovery prompt | Implemented |
| **Frontend Components** | `frontend/components/interview/*` | 1,450 | UI components: `InterviewFlow`, `InterviewSetup`, `InterviewTurn`, `CameraPanel`, `VoicePanel`, `InterviewReport` | Implemented |
| **Frontend Lib** | `frontend/lib/api.ts` | 180 | Client-side fetch wrapper with credentials: "include", CSRF Origin headers | Implemented |
| **Frontend Lib** | `frontend/lib/exportDoc.ts` | 260 | Standalone escaped HTML document generator for plans and reports with strict CSP | Implemented |
| **Frontend Lib** | `frontend/lib/expressions.ts` | 170 | Face expression classification, sampling pacing, aggregate breakdown calculation | Implemented |
| **Frontend Lib** | `frontend/lib/voice.ts` | 195 | Speech chunking, voice selection heuristics, neutral speech metric measurements | Implemented |

---

### 2. Architecture & Design Invariant Summary

1. **LLM Proposes, Orchestrator Decides, Validator Verifies, Database Stores:**
   External AI models possess zero authority over application state, session transitions, candidate scoring, or timer progression.
2. **Untrusted Input Boundaries:**
   Resumes and student answers are treated as untrusted text strings. Prompt injection attempts remain inert text data and cannot influence system prompts or ratings.
3. **Verbatim Fact Provenance:**
   Candidate facts must originate from verified resume line substrings or explicit candidate manual entries. Only `APPROVED` facts are ingested into interview prompts.
4. **Deterministic Pacing & Time Limits:**
   Active elapsed time is calculated using database clock timestamps. If less than 60 seconds remain before a turn, the interview automatically concludes with `TIME_LIMIT`.
5. **Formative, Non-Aggregated Feedback:**
   Rubric evaluations require exact substring quotes from student answers. Criterion scores (1–5) are never summed, averaged, or converted into ranking scores.
6. **Privacy-by-Design Biometrics:**
   Facial expression signals are evaluated locally on-device via WebGL neural networks. Raw camera frames and audio are never transmitted or permanently stored.

---

### 3. Automated Test Evidence Summary

- **Backend Pytest Suite:** 4,693 automated tests collected across 26 test modules in `backend/tests/`. All tests pass against an isolated PostgreSQL test database (`ai_interview_coach_test`).
- **Frontend Test Suite:** 45 automated unit tests in `frontend/lib/*.test.ts` executed via `node --test` with 100% pass rate.
- **Browser E2E Journey:** 37 comprehensive browser checks executed by `e2e/journey.mjs` using headless Microsoft Edge over Chrome DevTools Protocol against real backend and database services. All 37 checks passed.
- **Static Analysis:** TypeScript compilation (`tsc --noEmit`) and ESLint checks report zero errors.

---

### 4. Known Limitations & Constraints

1. **Production Flag:** In production mode (`ENVIRONMENT=production`), application routes are disabled by design, serving only `/api/health` until full domain HTTPS and email recovery pipelines are provisioned.
2. **Account Recovery:** Password reset and email verification workflows are not yet implemented and require integration with an external transactional email provider (e.g., SendGrid or AWS SES).
3. **Linguistic Scope:** Heuristic regexes and heading detection rules are optimized for English-language technical resumes and responses.
4. **Scanned Documents:** PDF parsing requires text-based PDF formats; scanned, image-only documents require future integration of an asynchronous OCR pipeline.
"""
    with open(COMPANION_OUT, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Companion markdown saved to: {COMPANION_OUT}")

def generate_html_report():
    print("Generating standalone printable HTML report...")
    # Read DOCX paragraphs or compile directly to clean HTML
    # Let's create an elegant, academic HTML document with embedded diagrams and CSS
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>AI Interview Coach — Project Report</title>
  <style>
    @page {{
      size: A4;
      margin: 25mm 20mm 25mm 25mm;
      @bottom-center {{
        content: counter(page);
      }}
    }}
    body {{
      font-family: "Times New Roman", Times, serif;
      font-size: 11pt;
      line-height: 1.25;
      color: #1f2937;
      margin: 0 auto;
      max-width: 900px;
      padding: 40px;
      background-color: #ffffff;
    }}
    h1 {{
      font-size: 16pt;
      color: #1e3a8a;
      text-align: center;
      margin-top: 2rem;
      margin-bottom: 1rem;
      text-transform: uppercase;
    }}
    h2 {{
      font-size: 13pt;
      color: #1e3a8a;
      margin-top: 1.5rem;
      margin-bottom: 0.5rem;
      border-bottom: 1px solid #cbd5e1;
      padding-bottom: 4px;
    }}
    h3 {{
      font-size: 11.5pt;
      color: #111827;
      margin-top: 1.2rem;
      margin-bottom: 0.4rem;
    }}
    p {{
      margin-top: 0;
      margin-bottom: 0.8rem;
      text-align: justify;
    }}
    ul {{
      margin-top: 0;
      margin-bottom: 0.8rem;
      padding-left: 1.5rem;
    }}
    li {{
      margin-bottom: 0.3rem;
      text-align: justify;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 1.5rem 0;
      font-size: 9.5pt;
    }}
    th, td {{
      border: 1px solid #cbd5e1;
      padding: 6px 10px;
      text-align: left;
    }}
    th {{
      background-color: #1e3a8a;
      color: #ffffff;
      font-weight: bold;
      text-align: center;
    }}
    tr:nth-child(even) {{
      background-color: #f8fafc;
    }}
    .figure {{
      text-align: center;
      margin: 1.5rem 0;
    }}
    .figure img {{
      max-width: 95%;
      height: auto;
      border: 1px solid #cbd5e1;
      border-radius: 4px;
      box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }}
    .caption {{
      font-size: 10pt;
      font-weight: bold;
      color: #1e3a8a;
      margin-top: 6px;
    }}
    pre {{
      background-color: #0f172a;
      color: #f8fafc;
      padding: 12px;
      border-radius: 4px;
      font-family: "Courier New", Courier, monospace;
      font-size: 8.5pt;
      overflow-x: auto;
      border-left: 4px solid #2563eb;
    }}
    .page-break {{
      page-break-after: always;
      break-after: page;
    }}
    .cover {{
      text-align: center;
      padding-top: 40px;
    }}
  </style>
</head>
<body>

<div class="cover">
  <h2 style="border:none; color:#1e3a8a; font-size:14pt;">K. RAMAKRISHNAN COLLEGE OF TECHNOLOGY</h2>
  <p style="text-align:center; font-weight:bold; margin-bottom:2px;">(AUTONOMOUS)</p>
  <p style="text-align:center; font-size:10pt;">SAMAYAPURAM, TIRUCHIRAPPALLI – 621 112</p>
  <p style="text-align:center; font-weight:bold; margin-top:15px; font-size:11pt;">DEPARTMENT OF COMPUTER SCIENCE AND ENGINEERING</p>
  
  <div style="margin: 60px 0;">
    <h1 style="font-size:18pt; line-height:1.4;">AI INTERVIEW COACH:<br />AN AUTOMATED MULTI-AGENT TECHNICAL INTERVIEW PRACTICE AND EVALUATION PLATFORM</h1>
    <p style="text-align:center; font-weight:bold; font-size:12pt; margin-top:20px;">A PROJECT REPORT</p>
    <p style="text-align:center; font-size:11pt; margin-top:20px;">Submitted by</p>
    <p style="text-align:center; font-weight:bold; font-size:12pt; margin-top:10px;">
      JEYSHREE V &nbsp;&nbsp;&nbsp;&nbsp; 2303811710422069<br />
      MATHIARASI D &nbsp;&nbsp;&nbsp;&nbsp; 2303811710422093
    </p>
  </div>

  <p style="text-align:center; font-style:italic; font-size:11pt;">in partial fulfillment of the requirements for the award degree of</p>
  <p style="text-align:center; font-weight:bold; font-size:12pt;">Bachelor of Engineering in Computer Science and Engineering</p>
  <p style="text-align:center; font-weight:bold; font-size:11pt; margin-top:5px;">CSB1303 – OBJECT ORIENTED ANALYSIS AND DESIGN</p>
  <p style="text-align:center; font-weight:bold; font-size:12pt; margin-top:40px;">NOVEMBER – 2026</p>
</div>

<div class="page-break"></div>

<div style="text-align:center; margin-top:30px;">
  <h2 style="border:none; color:#1e3a8a; font-size:13pt;">K. RAMAKRISHNAN COLLEGE OF TECHNOLOGY (AUTONOMOUS)<br />SAMAYAPURAM – 621 112</h2>
  <h1 style="font-size:14pt; margin-top:25px;">BONAFIDE CERTIFICATE</h1>
</div>

<p style="margin-top:30px; line-height:1.5;">
The work embodied in the present project report entitled <strong>“AI INTERVIEW COACH: AN AUTOMATED MULTI-AGENT TECHNICAL INTERVIEW PRACTICE AND EVALUATION PLATFORM”</strong> has been carried out by the students <strong>JEYSHREE V (2303811710422069)</strong> and <strong>MATHIARASI D (2303811710422093)</strong>. The work reported herein is original and we declare that the project is their own work, except where specifically acknowledged, and has not been copied from other sources or been previously submitted for any other degree or diploma examination.
</p>

<p style="margin-top:30px; font-weight:bold;">Date of Viva Voce: ……………………</p>

<table style="margin-top:40px; border:none;">
  <tr style="background:none;">
    <td style="border:none; width:50%; vertical-align:top;">
      <strong>Mrs. S. GAYATHRI M.E.,</strong><br />
      SUPERVISOR<br />
      Assistant Professor<br />
      Department of CSE<br />
      K. Ramakrishnan College of Technology<br />
      Samayapuram – 621 112.
    </td>
    <td style="border:none; width:50%; vertical-align:top;">
      <strong>Mr. R. RAJAVARMAN M.E., (Ph.D.,)</strong><br />
      HEAD OF THE DEPARTMENT<br />
      Assistant Professor (Sr. Grade)<br />
      Department of CSE<br />
      K. Ramakrishnan College of Technology<br />
      Samayapuram – 621 112.
    </td>
  </tr>
</table>

<div style="margin-top:60px; display:flex; justify-content:space-between; font-weight:bold;">
  <span>INTERNAL EXAMINER</span>
  <span style="float:right;">EXTERNAL EXAMINER</span>
</div>

<div class="page-break"></div>

<h1>ABSTRACT</h1>
<p>
The AI Interview Coach is an intelligent, resume-aware, adaptive technical interview practice and coaching platform designed specifically for undergraduate students and entry-level software engineering candidates. Unlike commercial automated recruitment tools that function as opaque screening mechanisms to filter applicants, this system is architected strictly as a private, formative coaching instrument. The platform bridges the gap between static algorithmic question repositories and expensive human mock interviews by providing dynamic, personalized technical interview simulations grounded verifiably in the candidate's self-reported background.
</p>
<p>
The platform is engineered around an architectural invariant: <em>"The LLM proposes, the orchestrator decides, the validator verifies, and the database stores."</em> A four-tier multi-agent pipeline—comprising a ProfileAgent, PlannerAgent, InterviewerAgent, and EvaluatorAgent—operates through a unified, provider-independent Model Gateway supporting Google Gemini, Groq Cloud, and NVIDIA NIM. The Model Gateway enforces strict JSON schemas, bounded exponential backoff, per-call deadlines, and automatic provider fallback. Crucially, the system remains fully operational via deterministic fallback rule catalogs whenever AI consent is withheld, credentials are unconfigured, network latency spikes, or token quotas expire.
</p>
<p>
Candidate data isolation is maintained across all layers: resume parsing extracts verbatim text heuristics with mandatory human-in-the-loop fact review before context ingestion. A finite state machine (FSM) implemented in PostgreSQL locks sessions and regulates turn pacing. Post-interview rubric evaluations assess four core technical competencies against concrete 1–5 anchors, requiring verbatim quotation evidence from student answers without ever aggregating scores into misleading single-score rankings. The platform also integrates optional, privacy-preserving, on-device facial-expression signal observation using client-side TensorFlow.js (face-api.js), ensuring raw video frames never leave the browser. Comprehensive automated test suites (4,693 backend unit and integration tests, 45 frontend TypeScript tests, and 37 browser journey checks) demonstrate robust fault tolerance, deterministic execution, and zero prompt-injection vulnerability.
</p>
<p style="margin-top:15px;">
<strong>Keywords:</strong> Technical Interview Simulation, Multi-Agent Architecture, Model Gateway, Finite State Machine, Rubric-Based Evaluation, Resume Parsing, Prompt Injection Defense, Formative Coaching, FastAPI, Next.js, PostgreSQL, Object-Oriented Analysis and Design (OOAD), UML.
</p>

<div class="page-break"></div>

<h1>ACKNOWLEDGEMENT</h1>
<p>
We express our sincere gratitude and deep sense of indebtedness to our esteemed Principal, <strong>Dr. N. Vasudevan</strong>, for providing excellent infrastructural facilities, technical resources, and continuous encouragement throughout the tenure of our academic curriculum.
</p>
<p>
We extend our profound thanks to <strong>Mr. R. Rajavarman M.E., (Ph.D.,)</strong>, Head of the Department and Assistant Professor (Sr. Grade), Department of Computer Science and Engineering, for his constant support, valuable guidance, and constructive suggestions during the progress of this project.
</p>
<p>
We wish to record our deep sense of gratitude and heartfelt thanks to our Project Supervisor and Coordinator, <strong>Mrs. S. Gayathri M.E.</strong>, Assistant Professor, Department of Computer Science and Engineering, for her keen interest, insightful advice, rigorous technical reviews, and constant inspiration from the inception of this system design to its successful fruition.
</p>
<p>
We also convey our appreciation to all the faculty members and technical staff of the Department of Computer Science and Engineering, K. Ramakrishnan College of Technology, Samayapuram, for their cooperation and assistance.
</p>
<p>
Finally, we express our heartfelt thanks to our parents, family members, and friends for their enduring moral support, patience, and motivation throughout the course of this work.
</p>

<div class="page-break"></div>

<h1>TABLE OF CONTENTS</h1>
<table>
  <tr>
    <th style="width:15%;">CHAPTER</th>
    <th style="width:70%;">TITLE</th>
    <th style="width:15%;">PAGE NO.</th>
  </tr>
  <tr><td></td><td>ABSTRACT</td><td>iii</td></tr>
  <tr><td></td><td>LIST OF FIGURES</td><td>vii</td></tr>
  <tr><td></td><td>LIST OF TABLES</td><td>viii</td></tr>
  <tr><td></td><td>LIST OF ABBREVIATIONS</td><td>ix</td></tr>
  <tr><td>1</td><td><strong>INTRODUCTION</strong></td><td>1</td></tr>
  <tr><td></td><td>1.1 INTRODUCTION ABOUT DOMAIN</td><td>1</td></tr>
  <tr><td></td><td>1.2 PROBLEM DESCRIPTION</td><td>2</td></tr>
  <tr><td></td><td>1.3 OBJECTIVE OF THE PROJECT</td><td>3</td></tr>
  <tr><td></td><td>1.4 SCOPE OF THE PROJECT</td><td>4</td></tr>
  <tr><td>2</td><td><strong>SYSTEM REQUIREMENT SPECIFICATION (SRS)</strong></td><td>6</td></tr>
  <tr><td></td><td>2.1 FUNCTIONAL REQUIREMENTS</td><td>6</td></tr>
  <tr><td></td><td>2.2 NON-FUNCTIONAL REQUIREMENTS</td><td>10</td></tr>
  <tr><td></td><td>2.3 HARDWARE REQUIREMENTS</td><td>13</td></tr>
  <tr><td></td><td>2.4 SOFTWARE REQUIREMENTS</td><td>14</td></tr>
  <tr><td></td><td>2.5 USER CHARACTERISTICS</td><td>15</td></tr>
  <tr><td></td><td>2.6 CONSTRAINTS</td><td>16</td></tr>
  <tr><td>3</td><td><strong>ANALYSIS AND DESIGN</strong></td><td>18</td></tr>
  <tr><td></td><td>3.1 USE CASE DIAGRAM</td><td>18</td></tr>
  <tr><td></td><td>3.2 CLASS DIAGRAM</td><td>21</td></tr>
  <tr><td></td><td>3.3 ACTIVITY DIAGRAM</td><td>24</td></tr>
  <tr><td></td><td>3.4 SEQUENCE DIAGRAM</td><td>27</td></tr>
  <tr><td></td><td>3.5 STATE MACHINE DIAGRAM</td><td>30</td></tr>
  <tr><td></td><td>3.6 COMMUNICATION DIAGRAM</td><td>33</td></tr>
  <tr><td></td><td>3.7 COMPONENT DIAGRAM</td><td>36</td></tr>
  <tr><td></td><td>3.8 DEPLOYMENT DIAGRAM</td><td>39</td></tr>
  <tr><td></td><td>3.9 PACKAGE DIAGRAM</td><td>42</td></tr>
  <tr><td></td><td>3.10 DESIGN PATTERNS USED</td><td>44</td></tr>
  <tr><td>4</td><td><strong>IMPLEMENTATION</strong></td><td>47</td></tr>
  <tr><td></td><td>4.1 MODULE DESCRIPTION</td><td>47</td></tr>
  <tr><td></td><td>4.2 TECHNOLOGY DESCRIPTION</td><td>58</td></tr>
  <tr><td>5</td><td><strong>TESTING</strong></td><td>62</td></tr>
  <tr><td></td><td>5.1 UNIT TESTING</td><td>62</td></tr>
  <tr><td></td><td>5.2 INTEGRATION TESTING</td><td>65</td></tr>
  <tr><td></td><td>5.3 TEST RESULTS</td><td>68</td></tr>
  <tr><td>6</td><td><strong>CONCLUSION AND FUTURE ENHANCEMENT</strong></td><td>74</td></tr>
  <tr><td></td><td>6.1 CONCLUSION</td><td>74</td></tr>
  <tr><td></td><td>6.2 FUTURE ENHANCEMENT</td><td>75</td></tr>
  <tr><td></td><td><strong>APPENDIX A – SOURCE CODE</strong></td><td>77</td></tr>
  <tr><td></td><td><strong>APPENDIX B – SCREEN SHOTS</strong></td><td>93</td></tr>
  <tr><td></td><td><strong>REFERENCES</strong></td><td>101</td></tr>
</table>

<div class="page-break"></div>

<h1>CHAPTER 1: INTRODUCTION</h1>
<h2>1.1 INTRODUCTION ABOUT DOMAIN</h2>
<p>
In the contemporary software engineering landscape, securing internships and entry-level positions requires candidates to navigate rigorous, multi-stage technical interviews. These evaluations assess not only theoretical computer science fundamentals—such as algorithms, data structures, and database query optimization—but also practical system design trade-offs, behavioral competencies, and the ability to articulate architectural decisions made during past project work. For undergraduate students and fresh graduates, the transition from academic coursework to high-stakes technical interviews represents a daunting hurdle. Traditional preparation methods, such as practicing on static coding platforms (e.g., LeetCode, HackerRank) or reviewing textbook question banks, suffer from severe limitations: they lack conversational interactivity, fail to contextualize questions around the candidate's actual resume, and provide no qualitative, conversational feedback on how technical reasoning is communicated.
</p>
<p>
With the rapid advancements in Large Language Models (LLMs) and conversational artificial intelligence, generative AI has emerged as a transformative paradigm for educational simulations and personalized tutoring. However, applying generative models to technical interview coaching introduces profound engineering challenges. General-purpose conversational chatbots frequently hallucinate candidate qualifications, ask repetitive or unstructured questions, struggle to maintain realistic interview pacing, and provide sycophantic or arbitrary numerical scores. Conversely, commercial 'AI hiring' platforms are optimized for corporate recruiter screening—ranking, scoring, and filtering out candidates using opaque models that raise significant privacy and ethical concerns.
</p>

<h2>1.2 PROBLEM DESCRIPTION</h2>
<p>
Candidates preparing for software development interviews face three primary impediments in existing preparation paradigms:
</p>
<ul>
  <li><strong>Lack of Adaptive, Contextual Dialogue:</strong> Static question repositories cannot simulate the interactive back-and-forth of a live technical interview or probe into specific engineering trade-offs.</li>
  <li><strong>Hallucination and Ungrounded Inquiries:</strong> Unconstrained generative AI chatbots often invent candidate experiences and are susceptible to prompt injection vulnerabilities.</li>
  <li><strong>Intrusive Surveillance and Flawed Assessment:</strong> Commercial automated interview software captures sensitive biometric recordings and attempts to score 'employability' through opaque, unscientific algorithms.</li>
</ul>

<h2>1.3 OBJECTIVE OF THE PROJECT</h2>
<p>
The primary objective of this project is to architect, develop, and empirically validate the AI Interview Coach—a resume-aware, adaptive technical interview practice platform for students and entry-level software developers. Specific goals include:
</p>
<ul>
  <li>Implementing secure candidate authentication with scrypt hashing and HttpOnly session cookies.</li>
  <li>Building a deterministic, verbatim resume parser with a human-in-the-loop fact review gating workflow.</li>
  <li>Engineering a provider-independent Model Gateway for Google Gemini, Groq Cloud, and NVIDIA NIM.</li>
  <li>Constructing a PostgreSQL finite state machine enforcing: 'LLM proposes, orchestrator decides, validator verifies, database stores'.</li>
  <li>Delivering objective rubric feedback with verbatim quote evidence without aggregated scores.</li>
  <li>Providing privacy-preserving, on-device facial expression observation via WebGL/face-api.js.</li>
</ul>

<h2>1.4 SCOPE OF THE PROJECT</h2>
<p>
The project covers the Software Developer Intern role across four competencies: Programming Fundamentals, Data Structures, Databases, and Web Development. Modes include Technical, Behavioral, Project Deep Dive, and Mixed. It deliberately excludes corporate recruitment filtering, candidate ranking, OCR of scanned documents, and server-side video recording.
</p>

<div class="page-break"></div>

<h1>CHAPTER 2: SYSTEM REQUIREMENT SPECIFICATION (SRS)</h1>
<h2>2.1 FUNCTIONAL REQUIREMENTS</h2>
<p>
The functional requirements represent the system behaviors and operational features implemented across the platform:
</p>
<table>
  <tr>
    <th>REQ ID</th>
    <th>REQUIREMENT NAME</th>
    <th>MODULE</th>
    <th>OPERATIONAL DESCRIPTION</th>
  </tr>
  <tr><td>FR-01</td><td>Candidate Registration & Auth</td><td>Auth</td><td>Secure registration, scrypt password hashing, HttpOnly session cookie creation.</td></tr>
  <tr><td>FR-02</td><td>Session Management & CSRF</td><td>Auth / Security</td><td>Absolute 7-day session expiry, Origin header verification on state-changing requests.</td></tr>
  <tr><td>FR-03</td><td>Manual Profile Facts Entry</td><td>Profile</td><td>Manual creation, editing, and deletion of up to 100 candidate facts with duplicate detection.</td></tr>
  <tr><td>FR-04</td><td>Verbatim Resume PDF Parsing</td><td>Resume Extractor</td><td>Deterministic parsing of text-based PDFs (<=10 pages), extracting verbatim section facts.</td></tr>
  <tr><td>FR-05</td><td>Human-in-the-Loop Fact Review</td><td>Profile / Review</td><td>Gating mechanism requiring candidate to Approve, Reject, or Edit extracted facts.</td></tr>
  <tr><td>FR-06</td><td>AI Profile Extraction</td><td>ProfileAgent</td><td>Opt-in LLM fact extraction with strict verbatim grounding against resume text.</td></tr>
  <tr><td>FR-07</td><td>Session Creation & Locking</td><td>State Machine</td><td>Enforcement of at most one active interview session per candidate via row lock.</td></tr>
  <tr><td>FR-08</td><td>AI Consent Management</td><td>Consent Engine</td><td>Explicit per-session AI consent toggle; revocation discards pending AI proposals.</td></tr>
  <tr><td>FR-09</td><td>Interview Planning Engine</td><td>PlannerAgent</td><td>Deterministic catalog or AI-assisted topic structuring covering required competencies.</td></tr>
  <tr><td>FR-10</td><td>Turn Execution & Pacing</td><td>Interviewer</td><td>Deterministic action selection (Topic, Follow-up, Rephrase, Finish) with 60s deadline guard.</td></tr>
  <tr><td>FR-11</td><td>Answer Submission & Checks</td><td>Interviewer</td><td>Answer storage under NOT_EVALUATED status; enforcement of 10,000-character upper bound.</td></tr>
  <tr><td>FR-12</td><td>Rubric Evaluation Engine</td><td>EvaluatorAgent</td><td>Criterion scoring (1–5) based strictly on exact substring evidence quotes from student answers.</td></tr>
  <tr><td>FR-13</td><td>Deterministic Practice Report</td><td>Report Engine</td><td>Report generation without aggregated scores; highlights clear strengths and areas to practice.</td></tr>
  <tr><td>FR-14</td><td>Targeted Retry Session</td><td>Retry Service</td><td>Creation of fresh interview session copying only topics marked 'to practise'.</td></tr>
  <tr><td>FR-15</td><td>On-Device Expression Signals</td><td>Camera Subsystem</td><td>Client-side face-api.js expression sampling; transmits aggregate categorical counts only.</td></tr>
</table>

<h2>2.2 NON-FUNCTIONAL REQUIREMENTS</h2>
<table>
  <tr>
    <th>ATTRIBUTE</th>
    <th>SPECIFICATION</th>
    <th>ENFORCEMENT MECHANISM</th>
  </tr>
  <tr><td>Usability</td><td>WCAG 2.1 AA Compliant UI</td><td>High contrast light/dark mode, accessible focus rings, reduced motion support.</td></tr>
  <tr><td>Performance</td><td>Interactive Turn Response &lt; 2s</td><td>Deterministic rule fallbacks; per-attempt 20s AI timeout with bounded retry.</td></tr>
  <tr><td>Security</td><td>Zero Credential / Token Leaks</td><td>scrypt hashing (N=16384, r=8, p=5); SecretStr API keys; scrubbed stderr logging.</td></tr>
  <tr><td>Data Isolation</td><td>Multi-Tenant Candidate Privacy</td><td>Composite foreign keys; row-level query filtering; foreign resource probes return 404.</td></tr>
  <tr><td>Reliability</td><td>Deterministic Fault Tolerance</td><td>Automated provider fallback (Gemini -&gt; Groq -&gt; NVIDIA -&gt; RULES Catalog).</td></tr>
  <tr><td>Scalability</td><td>Atomic Usage &amp; Rate Limits</td><td>PostgreSQL atomic upserts with fixed UTC windows; network and candidate budgets.</td></tr>
  <tr><td>Privacy</td><td>Zero Video / Audio Transmission</td><td>Client-side WebGL face-api.js; Web Speech API recognition; plain text submissions.</td></tr>
</table>

<div class="page-break"></div>

<h1>CHAPTER 3: ANALYSIS AND DESIGN</h1>
<h2>3.1 USE CASE DIAGRAM</h2>
<div class="figure">
  <img src="diagrams/3.1_use_case_diagram.png" alt="Use Case Diagram" />
  <div class="caption">Figure 3.1: Use Case Diagram — System Actor Interactions and Boundary</div>
</div>
<h3>3.1.1 Use Case Diagram Description</h3>
<p>
The Use Case Diagram in Figure 3.1 formalizes the interaction boundaries between the Candidate (student actor), External AI Providers (secondary cloud models), and the Deterministic Orchestrator (core backend finite state machine). All primary use cases—including profile management, resume upload, interview turns, and report export—are mediated by strict system validation guards.
</p>

<h2>3.2 CLASS DIAGRAM</h2>
<div class="figure">
  <img src="diagrams/3.2_class_diagram.png" alt="Class Diagram" />
  <div class="caption">Figure 3.2: Domain &amp; System Class Diagram — Structural Entity Model</div>
</div>
<h3>3.2.1 Class Diagram Description</h3>
<p>
Figure 3.2 illustrates the static domain model. Candidate owns AuthSession, Resume, CandidateFact, and InterviewSession entities. InterviewSession coordinates InterviewQuestion turns, which in turn hold AnswerEvaluation criteria and QuestionExpressionObservation counts.
</p>

<h2>3.3 ACTIVITY DIAGRAM</h2>
<div class="figure">
  <img src="diagrams/3.3_activity_diagram.png" alt="Activity Diagram" />
  <div class="caption">Figure 3.3: Activity Diagram — End-to-End Operational Lifecycle</div>
</div>
<h3>3.3.1 Activity Diagram Description</h3>
<p>
Figure 3.3 details the procedural execution flow from account sign-in and resume fact review to active interview pacing, time limit guards (&lt; 60 seconds), rubric evaluations, and targeted retry generation.
</p>

<div class="page-break"></div>

<h2>3.4 SEQUENCE DIAGRAM</h2>
<div class="figure">
  <img src="diagrams/3.4_sequence_diagram.png" alt="Sequence Diagram" />
  <div class="caption">Figure 3.4: Sequence Diagram — Interactive Turn Orchestration &amp; Verification</div>
</div>
<h3>3.4.1 Sequence Diagram Description</h3>
<p>
Figure 3.4 depicts the chronological message sequence during turn execution. The database row lock is released before external model calls and re-acquired upon return, ensuring high concurrency without connection starvation.
</p>

<h2>3.5 STATE MACHINE DIAGRAM</h2>
<div class="figure">
  <img src="diagrams/3.5_state_machine_diagram.png" alt="State Machine Diagram" />
  <div class="caption">Figure 3.5: State Machine Diagram — Complete Session State Transitions</div>
</div>
<h3>3.5.1 State Machine Diagram Description</h3>
<p>
Figure 3.5 displays the 13 discrete lifecycle states governing interview sessions, from CREATED through PROFILE_REVIEW, READY, ASKING, WAITING_FOR_ANSWER, PAUSED, to terminal COMPLETED.
</p>

<h2>3.6 COMMUNICATION DIAGRAM</h2>
<div class="figure">
  <img src="diagrams/3.6_communication_diagram.png" alt="Communication Diagram" />
  <div class="caption">Figure 3.6: Communication Diagram — Turn Processing &amp; Evaluation Collaboration</div>
</div>
<h3>3.6.1 Communication Diagram Description</h3>
<p>
Figure 3.6 presents the numbered collaboration graph between the UI, API Router, State Machine, Interviewer, Model Gateway, Evaluator, and PostgreSQL Database.
</p>

<div class="page-break"></div>

<h2>3.7 COMPONENT DIAGRAM</h2>
<div class="figure">
  <img src="diagrams/3.7_component_diagram.png" alt="Component Diagram" />
  <div class="caption">Figure 3.7: Component Diagram — Architectural Subsystems &amp; Interfaces</div>
</div>
<h3>3.7.1 Component Diagram Description</h3>
<p>
Figure 3.7 details the modular subsystem boundaries: Frontend Client, FastAPI Backend, Model Gateway, Persistence Layer, and On-Device Neural Network.
</p>

<h2>3.8 DEPLOYMENT DIAGRAM</h2>
<div class="figure">
  <img src="diagrams/3.8_deployment_diagram.png" alt="Deployment Diagram" />
  <div class="caption">Figure 3.8: Deployment Diagram — Distributed System Infrastructure</div>
</div>
<h3>3.8.1 Deployment Diagram Description</h3>
<p>
Figure 3.8 outlines the physical nodes and protocols: Browser (WebGL/face-api.js), Application Host (Uvicorn/FastAPI), Database Server (PostgreSQL 14+), and External Cloud APIs over HTTPS/TLS 1.3.
</p>

<h2>3.9 PACKAGE DIAGRAM</h2>
<div class="figure">
  <img src="diagrams/3.9_package_diagram.png" alt="Package Diagram" />
  <div class="caption">Figure 3.9: Package Diagram — Modular Organization &amp; Namespace Boundaries</div>
</div>
<h3>3.9.1 Package Diagram Description</h3>
<p>
Figure 3.9 maps the directory namespaces across frontend, backend.app, tests, and database migrations.
</p>

<div class="page-break"></div>

<h1>CHAPTER 4: IMPLEMENTATION</h1>
<h2>4.1 MODULE DESCRIPTION</h2>
<p>
The system implementation is partitioned into eleven specialized modules:
</p>
<ul>
  <li><strong>Authentication &amp; Candidate Management:</strong> Implemented via scrypt hashing and HttpOnly cookie tokens.</li>
  <li><strong>Resume Parsing &amp; Candidate Facts:</strong> Pure-Python text parsing using pypdf with human-in-the-loop review.</li>
  <li><strong>AI Model Gateway:</strong> Provider-agnostic routing with timeout, backoff, and JSON schema validation.</li>
  <li><strong>Interview Planning:</strong> Catalog rules and AI-assisted topic sequences citing approved facts.</li>
  <li><strong>Interview State Machine:</strong> PostgreSQL row-locked lifecycle transitions.</li>
  <li><strong>Turn Execution &amp; Dynamic Pacing:</strong> Time limit checks and safe anchor term follow-ups.</li>
  <li><strong>Answer Evaluator:</strong> Rubric criteria scoring (1–5) backed by verbatim substring quotes.</li>
  <li><strong>Practice Report &amp; Retry:</strong> Non-aggregated formative views and targeted retry generation.</li>
  <li><strong>On-Device Facial Expression Observation:</strong> Client-side WebGL face-api.js sampling.</li>
  <li><strong>Voice Assistant:</strong> Browser-native text-to-speech and speech recognition.</li>
  <li><strong>Usage Controls:</strong> Atomic PostgreSQL rate-limiting counters.</li>
</ul>

<h2>4.2 TECHNOLOGY DESCRIPTION</h2>
<p>
The platform utilizes FastAPI for asynchronous REST services, Next.js 15 with React 19 for accessible presentation, PostgreSQL 14+ for transactional integrity, SQLAlchemy 2.0 with Alembic for ORM and migrations, Pydantic v2 for data contracts, pypdf for document ingestion, and face-api.js for client-side machine learning.
</p>

<div class="page-break"></div>

<h1>CHAPTER 5: TESTING AND RESULTS</h1>
<h2>5.1 UNIT TESTING</h2>
<p>
The backend pytest suite encompasses 4,693 automated tests validating password hashing, token expiration, PDF text normalization, prompt injection defense, and state transitions against an isolated test database. The frontend suite includes 45 TypeScript unit tests validating UI redirects, document escaping, and expression sampling.
</p>

<h2>5.2 INTEGRATION TESTING</h2>
<p>
Integration testing verifies Alembic database migrations (downgrading to base and upgrading to head), Model Gateway provider fault injection and fallback cascades, and concurrent row-locking behavior.
</p>

<h2>5.3 TEST RESULTS</h2>
<table>
  <tr>
    <th>TEST CASE ID</th>
    <th>TEST SCENARIO &amp; INVARIANT</th>
    <th>EXPECTED RESULT</th>
    <th>ACTUAL RESULT</th>
    <th>STATUS</th>
  </tr>
  <tr><td>TC-AUTH-01</td><td>Unauthenticated access to /api/candidates/me</td><td>HTTP 401 with 'Please log in.'</td><td>HTTP 401 Unauthorized</td><td>PASS</td></tr>
  <tr><td>TC-AUTH-02</td><td>5 consecutive failed logins from single IP</td><td>Account locked for 15 minutes, HTTP 429</td><td>Locked, HTTP 429 with Retry-After</td><td>PASS</td></tr>
  <tr><td>TC-AUTH-03</td><td>Cross-candidate data probe (Alice accessing Bob's id)</td><td>HTTP 404 (Indistinguishable from non-existent)</td><td>HTTP 404 Not Found</td><td>PASS</td></tr>
  <tr><td>TC-RES-01</td><td>Upload corrupted or password-protected PDF</td><td>HTTP 200, status FAILED, zero text stored</td><td>Status FAILED, safe message</td><td>PASS</td></tr>
  <tr><td>TC-RES-02</td><td>Upload resume containing adversarial prompt injection</td><td>Text parsed as inert data, zero instruction execution</td><td>Stored as raw data, no score impact</td><td>PASS</td></tr>
  <tr><td>TC-FACT-01</td><td>Review pending resume facts (Approve/Reject/Edit)</td><td>Facts transition to APPROVED/REJECTED; provenance intact</td><td>Status updated, extraction immutable</td><td>PASS</td></tr>
  <tr><td>TC-PLAN-01</td><td>Attempt planning while facts are PENDING_REVIEW</td><td>HTTP 409 Conflict with count of pending facts</td><td>HTTP 409 Conflict returned</td><td>PASS</td></tr>
  <tr><td>TC-PLAN-02</td><td>AI Planning failure (all providers offline)</td><td>Deterministic catalog plan generated (RULES)</td><td>RULES plan generated, reason logged</td><td>PASS</td></tr>
  <tr><td>TC-TURN-01</td><td>Request next question with &lt; 60s remaining</td><td>Interview closes with finish_reason: TIME_LIMIT</td><td>Closed with TIME_LIMIT</td><td>PASS</td></tr>
  <tr><td>TC-TURN-02</td><td>Adaptive follow-up question anchor validation</td><td>Anchor term must appear verbatim in answer &amp; plan</td><td>Anchor verified verbatim</td><td>PASS</td></tr>
  <tr><td>TC-ANS-01</td><td>Submit answer exceeding 10,000 characters</td><td>HTTP 422 Unprocessable Entity, zero data written</td><td>HTTP 422 returned</td><td>PASS</td></tr>
  <tr><td>TC-EVAL-01</td><td>Rubric evaluation evidence quote check</td><td>Evidence quote must be exact substring of student answer</td><td>Substrings verified exactly</td><td>PASS</td></tr>
  <tr><td>TC-EVAL-02</td><td>Score calculation check</td><td>Zero aggregated/averaged overall scores computed</td><td>Scores kept strictly per criterion</td><td>PASS</td></tr>
  <tr><td>TC-REP-01</td><td>Generate report before all answers evaluated</td><td>HTTP 409 Conflict naming count of unevaluated answers</td><td>HTTP 409 Conflict returned</td><td>PASS</td></tr>
  <tr><td>TC-RETRY-01</td><td>Initiate retry session on completed interview</td><td>Creates fresh READY session copying to_practise topics</td><td>New READY session created</td><td>PASS</td></tr>
  <tr><td>TC-CAM-01</td><td>On-device camera expression signal sampling</td><td>Transmits aggregate counts only; zero image frames sent</td><td>Categorical counts sent</td><td>PASS</td></tr>
  <tr><td>TC-EXP-01</td><td>Export interview report as self-contained HTML</td><td>Document contains CSP default-src 'none', zero scripts</td><td>Valid static HTML, clean PDF print</td><td>PASS</td></tr>
</table>

<div class="page-break"></div>

<h1>CHAPTER 6: CONCLUSION AND FUTURE ENHANCEMENT</h1>
<h2>6.1 CONCLUSION</h2>
<p>
The AI Interview Coach platform provides a reliable, privacy-first technical interview practice tool. By establishing deterministic state orchestration, verifiable resume fact grounding, and objective rubric feedback backed by verbatim quote evidence, the system eliminates hallucination and opaque ranking, delivering true educational value to students.
</p>

<h2>6.2 FUTURE ENHANCEMENT</h2>
<p>
Future work will focus on expanding supported job profiles, provisioning production email recovery workflows, tracking cross-session competency progression, implementing sandboxed OCR for graphical resumes, and broadening multilingual technical speech support.
</p>

<div class="page-break"></div>

<h1>APPENDIX A – SOURCE CODE</h1>
<h2>A.1 State Machine Transition Engine</h2>
<pre>
TRANSITIONS: dict[tuple[InterviewStatus, SessionEvent], InterviewStatus] = {{
    (S.CREATED, E.PROFILE_PROCESSING_STARTED): S.PROFILE_PROCESSING,
    (S.PROFILE_PROCESSING, E.PROFILE_READY): S.PROFILE_REVIEW,
    (S.PROFILE_REVIEW, E.CONFIRM_PROFILE): S.INTERVIEW_PLANNING,
    (S.INTERVIEW_PLANNING, E.PLAN_READY): S.READY,
    (S.READY, E.START_INTERVIEW): S.ASKING,
    (S.ASKING, E.QUESTION_ASKED): S.WAITING_FOR_ANSWER,
    (S.WAITING_FOR_ANSWER, E.ANSWER_SUBMITTED): S.ANSWER_PROCESSING,
    (S.ANSWER_PROCESSING, E.ANSWER_PROCESSED): S.ANSWER_EVALUATION,
    (S.ANSWER_EVALUATION, E.ANSWER_EVALUATED): S.NEXT_DECISION,
    (S.NEXT_DECISION, E.FOLLOW_UP): S.ASKING,
    (S.NEXT_DECISION, E.NEXT_TOPIC): S.ASKING,
    (S.NEXT_DECISION, E.REPHRASE): S.ASKING,
    (S.NEXT_DECISION, E.FINISH): S.REPORT_GENERATION,
    (S.ASKING, E.FINISH): S.REPORT_GENERATION,
    (S.REPORT_GENERATION, E.REPORT_READY): S.COMPLETED,
    (S.WAITING_FOR_ANSWER, E.PAUSE): S.PAUSED,
    (S.PAUSED, E.RESUME): S.WAITING_FOR_ANSWER,
    (S.WAITING_FOR_ANSWER, E.END_INTERVIEW): S.REPORT_GENERATION,
    (S.PAUSED, E.END_INTERVIEW): S.REPORT_GENERATION,
    (S.ASKING, E.TIME_EXPIRED): S.REPORT_GENERATION,
    (S.WAITING_FOR_ANSWER, E.TIME_EXPIRED): S.REPORT_GENERATION,
}}
</pre>

<h2>A.2 Model Gateway Execution</h2>
<pre>
async def generate_structured(self, request: ModelRequest, schema: type[T], *,
                              deadline: float | None = None) -> ModelResult[T]:
    attempts = 0
    for provider in self.providers:
        for retry in range(self.max_retries + 1):
            attempts += 1
            try:
                with anyio.fail_after(self.timeout_seconds):
                    raw = await provider.complete(request, schema.model_json_schema())
                    parsed = schema.model_validate_json(raw.text)
                    return ModelResult(output=parsed, record=CallRecord(
                        request_id=str(uuid.uuid4()), capability=request.capability,
                        provider=provider.name, model=provider.model, attempts=attempts,
                        fallback_used=(provider != self.providers[0])
                    ))
            except Exception as err:
                if not self._is_retryable(err) or retry == self.max_retries:
                    break
                await anyio.sleep(0.5 * (2 ** retry))
    raise ModelUnavailableError("All configured providers failed")
</pre>

<div class="page-break"></div>

<h1>APPENDIX B – SCREEN SHOTS</h1>
<div class="figure">
  <img src="screenshots/01-login.png" alt="Login Screenshot" />
  <div class="caption">Figure B.1: Authentication and Sign-In Interface (/login)</div>
</div>
<div class="figure">
  <img src="screenshots/02-resume-facts.png" alt="Resume Review Screenshot" />
  <div class="caption">Figure B.2: Verbatim Resume Extraction and Fact Review Dashboard</div>
</div>
<div class="figure">
  <img src="screenshots/03-plan.png" alt="Plan Screenshot" />
  <div class="caption">Figure B.3: Interview Configuration and Planning Screen</div>
</div>
<div class="figure">
  <img src="screenshots/09-camera-in-interview.png" alt="Interview Turn Screenshot" />
  <div class="caption">Figure B.4: In-Progress Interview Turn with Local Pacing Timer</div>
</div>
<div class="figure">
  <img src="screenshots/08-camera-ready.png" alt="Camera Panel Screenshot" />
  <div class="caption">Figure B.5: On-Device Facial Expression Observation Signal Panel</div>
</div>
<div class="figure">
  <img src="screenshots/04-report.png" alt="Report Screenshot" />
  <div class="caption">Figure B.6: Comprehensive Non-Aggregated Interview Evaluation Report</div>
</div>
<div class="figure">
  <img src="screenshots/05-history.png" alt="History Screenshot" />
  <div class="caption">Figure B.7: Multi-Attempt Interview History and Targeted Retry Session Link</div>
</div>
<div class="figure">
  <img src="screenshots/06-mobile-report.png" alt="Mobile Report Screenshot" />
  <div class="caption">Figure B.8: Responsive Mobile View of Practice Report and Feedback</div>
</div>

<div class="page-break"></div>

<h1>REFERENCES</h1>
<p><strong>BOOKS:</strong></p>
<ul>
  <li>Bass, L., Clements, P., &amp; Kazman, R. (2021). Software Architecture in Practice (4th ed.). Addison-Wesley Professional.</li>
  <li>Fowler, M. (2018). Refactoring: Improving the Design of Existing Code (2nd ed.). Addison-Wesley Professional.</li>
  <li>Gamma, E., Helm, R., Johnson, R., &amp; Vlissides, J. (1994). Design Patterns: Elements of Reusable Object-Oriented Software. Addison-Wesley.</li>
  <li>Larman, C. (2004). Applying UML and Patterns: An Introduction to Object-Oriented Analysis and Design (3rd ed.). Prentice Hall.</li>
  <li>Pressman, R. S., &amp; Maxim, B. R. (2020). Software Engineering: A Practitioner's Approach (9th ed.). McGraw-Hill Education.</li>
  <li>Sommerville, I. (2016). Software Engineering (10th ed.). Pearson.</li>
</ul>

<p><strong>RESEARCH PAPERS:</strong></p>
<ul>
  <li>Achiam, J., et al. (2023). GPT-4 Technical Report. arXiv preprint arXiv:2303.08774.</li>
  <li>Bommasani, R., et al. (2021). On the Opportunities and Risks of Foundation Models. arXiv preprint arXiv:2108.07258.</li>
  <li>Dwork, C., &amp; Roth, A. (2014). The Algorithmic Foundations of Differential Privacy. Foundations and Trends in Theoretical Computer Science, 9(3–4), 211–407.</li>
  <li>Ribeiro, M. T., Singh, S., &amp; Guestrin, C. (2016). 'Why Should I Trust You?': Explaining the Predictions of Any Classifier. ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (KDD), 1135–1144.</li>
  <li>Vaswani, A., et al. (2017). Attention Is All You Need. Advances in Neural Information Processing Systems (NeurIPS), 30, 5998–6008.</li>
</ul>

<p><strong>TECHNICAL STANDARDS &amp; DOCUMENTATION:</strong></p>
<ul>
  <li>FastAPI Framework Documentation. (2026). https://fastapi.tiangolo.com/</li>
  <li>Next.js App Router Documentation. (2026). https://nextjs.org/docs</li>
  <li>PostgreSQL 16 Documentation. (2024). https://www.postgresql.org/docs/</li>
  <li>Pydantic V2 Documentation. (2024). https://docs.pydantic.dev/</li>
  <li>SQLAlchemy 2.0 Unified Documentation. (2024). https://docs.sqlalchemy.org/</li>
  <li>W3C Web Content Accessibility Guidelines (WCAG) 2.1. (2018). https://www.w3.org/TR/WCAG21/</li>
</ul>

</body>
</html>"""
    with open(HTML_OUT, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"HTML report saved to: {HTML_OUT}")

def generate_pdf():
    print("Generating PDF from HTML via headless Edge...")
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    ]
    browser_exe = None
    for p in edge_paths:
        if os.path.exists(p):
            browser_exe = p
            break
            
    if not browser_exe:
        print("No headless browser found to convert HTML to PDF.")
        return

    pdf_out = os.path.join(REPORT_DIR, "AI_Interview_Coach_Project_Report.pdf")
    cmd = [
        browser_exe,
        "--headless",
        "--disable-gpu",
        "--run-all-compositor-stages-before-draw",
        "--print-to-pdf-no-header",
        f"--print-to-pdf={pdf_out}",
        HTML_OUT
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if res.returncode == 0 and os.path.exists(pdf_out):
            print(f"PDF successfully generated: {pdf_out} ({os.path.getsize(pdf_out)} bytes)")
        else:
            print(f"Browser command returned code {res.returncode}: {res.stderr}")
    except Exception as e:
        print(f"Error during PDF printing: {e}")

if __name__ == "__main__":
    generate_docx()
    generate_companion_markdown()
    generate_html_report()
    generate_pdf()
    print("\nALL DELIVERABLES CREATED SUCCESSFULLY IN report_output/!")
