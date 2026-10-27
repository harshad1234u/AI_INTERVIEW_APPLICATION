"""Generate all 9 UML diagrams for the AI Interview Coach Project Report.
Uses matplotlib to produce high-resolution, aesthetically styled UML diagrams.
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, ArrowStyle

OUT_DIR = r"D:\code_placed\ai_interview_coach\report_output\diagrams"
os.makedirs(OUT_DIR, exist_ok=True)

# Common styling constants
FONT_NAME = "sans-serif"
BG_COLOR = "#FFFFFF"
TEXT_COLOR = "#1F2937"
PRIMARY_COLOR = "#2563EB"
BORDER_COLOR = "#374151"
BOX_BG = "#F8FAFC"
HEADER_BG = "#E2E8F0"
ACTOR_COLOR = "#1E293B"

def save_fig(fig, filename):
    filepath = os.path.join(OUT_DIR, filename)
    fig.savefig(filepath, dpi=300, bbox_inches="tight", facecolor=BG_COLOR)
    plt.close(fig)
    print(f"Saved: {filepath}")

# ==========================================
# 1. USE CASE DIAGRAM (Figure 3.1)
# ==========================================
def generate_use_case():
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis("off")

    # Title
    ax.text(7, 9.7, "Figure 3.1: Use Case Diagram — AI Interview Coach Platform", 
            ha="center", va="center", fontsize=14, fontweight="bold", color=TEXT_COLOR)

    # System boundary box
    sys_box = FancyBboxPatch((3.2, 0.4), 7.6, 9.0, boxstyle="round,pad=0.2",
                             ec="#475569", fc="#F8FAFC", lw=2, linestyle="--")
    ax.add_patch(sys_box)
    ax.text(7, 9.15, "AI Interview Coach System Boundary", ha="center", va="center",
            fontsize=12, fontweight="bold", color="#1E3A8A")

    # Helper: draw stick figure actor
    def draw_actor(x, y, label):
        # Head
        circle = plt.Circle((x, y + 0.35), 0.15, ec=ACTOR_COLOR, fc="#E2E8F0", lw=2)
        ax.add_patch(circle)
        # Body
        ax.plot([x, x], [y + 0.2, y - 0.15], color=ACTOR_COLOR, lw=2)
        # Arms
        ax.plot([x - 0.2, x + 0.2], [y + 0.05, y + 0.05], color=ACTOR_COLOR, lw=2)
        # Legs
        ax.plot([x, x - 0.15], [y - 0.15, y - 0.45], color=ACTOR_COLOR, lw=2)
        ax.plot([x, x + 0.15], [y - 0.15, y - 0.45], color=ACTOR_COLOR, lw=2)
        # Label
        ax.text(x, y - 0.65, label, ha="center", va="top", fontsize=10, fontweight="bold", color=TEXT_COLOR)

    # Primary Actor: Candidate
    draw_actor(1.5, 5.0, "Candidate\n(Student / Job Seeker)")

    # Secondary Actor: AI Provider
    draw_actor(12.5, 7.0, "External AI Providers\n(Gemini / Groq / NVIDIA)")

    # System Actor: Orchestrator
    draw_actor(12.5, 3.0, "Deterministic Orchestrator\n(FSM & Limits Engine)")

    # Use cases list: (text, y_pos, has_extend_or_include, target_idx, rel_label)
    use_cases = [
        ("Register & Authenticate (HttpOnly Cookie)", 8.5),
        ("Manage Profile & Manual Candidate Facts", 7.7),
        ("Upload PDF Resume & Parse Verbatim Facts", 6.9),
        ("Review Extracted Facts (Approve/Reject/Edit)", 6.1),
        ("Request AI Fact Extraction (Grounding Gated)", 5.3),
        ("Configure Plan & Toggle AI Consent", 4.5),
        ("Execute Interview Turn (Timer & Q&A)", 3.7),
        ("Submit Answer (Text / Voice Review)", 2.9),
        ("Evaluate Answer Against Rubric (Verbatim Quotes)", 2.1),
        ("Generate Practice Report & Actionable Feedback", 1.3),
        ("Initiate Targeted Retry Session", 0.6),
    ]

    uc_centers = []
    for i, (text, y) in enumerate(use_cases):
        x = 7.0
        # Draw ellipse
        ellipse = patches.Ellipse((x, y), 5.2, 0.55, ec="#2563EB", fc="#EFF6FF", lw=1.5)
        ax.add_patch(ellipse)
        ax.text(x, y, text, ha="center", va="center", fontsize=8.5, fontweight="medium", color="#1E293B")
        uc_centers.append((x, y))

        # Actor line from Candidate
        ax.plot([1.7, 4.4], [5.0, y], color="#94A3B8", lw=1.2, linestyle="-")

    # Connect to External AI Providers
    for idx in [4, 5, 8]: # AI Fact Extraction, Plan, Evaluate
        ax.plot([9.6, 12.3], [use_cases[idx][1], 7.0], color="#9333EA", lw=1.2, linestyle="--")

    # Connect to Orchestrator
    for idx in [2, 5, 6, 8, 9, 10]:
        ax.plot([9.6, 12.3], [use_cases[idx][1], 3.0], color="#059669", lw=1.2, linestyle="--")

    # Include / Extend Annotations
    ax.annotate("<<extend>>", xy=(7.0, 5.58), xytext=(7.0, 5.82),
                arrowprops=dict(arrowstyle="->", color="#DC2626", lw=1, linestyle=":"),
                ha="center", fontsize=7.5, color="#DC2626", fontweight="bold")
    ax.annotate("<<include>>", xy=(7.0, 2.38), xytext=(7.0, 2.62),
                arrowprops=dict(arrowstyle="->", color="#0284C7", lw=1, linestyle=":"),
                ha="center", fontsize=7.5, color="#0284C7", fontweight="bold")

    save_fig(fig, "3.1_use_case_diagram.png")

# ==========================================
# 2. CLASS DIAGRAM (Figure 3.2)
# ==========================================
def generate_class_diagram():
    fig, ax = plt.subplots(figsize=(16, 12))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 12)
    ax.axis("off")

    ax.text(8, 11.7, "Figure 3.2: Domain & System Class Diagram — Object Model", 
            ha="center", va="center", fontsize=14, fontweight="bold", color=TEXT_COLOR)

    def draw_class(x, y, w, h, title, attributes, methods=None):
        # Header box
        header_h = 0.5
        body_h = h - header_h
        hdr = FancyBboxPatch((x, y + body_h), w, header_h, boxstyle="round,pad=0.0",
                             ec=BORDER_COLOR, fc=HEADER_BG, lw=1.5)
        ax.add_patch(hdr)
        ax.text(x + w / 2, y + body_h + 0.25, title, ha="center", va="center",
                fontsize=9.5, fontweight="bold", color="#1E3A8A")

        # Body box
        body = FancyBboxPatch((x, y), w, body_h, boxstyle="round,pad=0.0",
                              ec=BORDER_COLOR, fc=BOX_BG, lw=1.5)
        ax.add_patch(body)

        # Content text
        curr_y = y + body_h - 0.25
        for attr in attributes:
            ax.text(x + 0.15, curr_y, attr, ha="left", va="center", fontsize=7.5, fontfamily="monospace", color="#334155")
            curr_y -= 0.22

        if methods:
            ax.plot([x, x + w], [curr_y - 0.05, curr_y - 0.05], color="#CBD5E1", lw=1)
            curr_y -= 0.25
            for m in methods:
                ax.text(x + 0.15, curr_y, m, ha="left", va="center", fontsize=7.5, fontfamily="monospace", color="#0F766E")
                curr_y -= 0.22

    # Classes placement
    # 1. Candidate
    draw_class(0.5, 7.8, 4.2, 3.4, "Candidate (Model)", [
        "- id: UUID (PK)",
        "- email: String (Unique, Lower)",
        "- name: String",
        "- password_hash: String",
        "- failed_logins: Integer",
        "- locked_until: DateTime",
        "- created_at: DateTime"
    ], [
        "+ verify_password(pw): bool",
        "+ lock_account(mins): void",
        "+ reset_failed_logins(): void"
    ])

    # 2. AuthSession
    draw_class(0.5, 4.5, 4.2, 2.6, "AuthSession (Model)", [
        "- token_hash: String(64) (PK)",
        "- candidate_id: UUID (FK)",
        "- created_at: DateTime",
        "- expires_at: DateTime"
    ], [
        "+ is_expired(): bool",
        "+ revoke(): void"
    ])

    # 3. Resume
    draw_class(5.5, 7.8, 4.6, 3.4, "Resume (Model)", [
        "- id: UUID (PK)",
        "- candidate_id: UUID (FK)",
        "- status: ResumeStatus",
        "- page_count: Integer",
        "- parsed_json: JSONB",
        "- raw_text: Text",
        "- created_at: DateTime"
    ], [
        "+ parse_sections(): dict",
        "+ is_readable(): bool"
    ])

    # 4. CandidateFact
    draw_class(5.5, 4.2, 4.6, 3.2, "CandidateFact (Model)", [
        "- id: UUID (PK)",
        "- candidate_id: UUID (FK)",
        "- resume_id: UUID (FK, Nullable)",
        "- category: FactCategory",
        "- fact: String(200)",
        "- extracted_fact: String(200)",
        "- source: FactSource (RESUME|MANUAL)",
        "- status: FactStatus (PENDING|APP|REJ)",
        "- extracted_by: ExtractionType"
    ], [
        "+ approve(): void",
        "+ reject(): void",
        "+ edit(new_text): void"
    ])

    # 5. InterviewSession
    draw_class(10.8, 7.2, 4.8, 4.0, "InterviewSession (Model)", [
        "- id: UUID (PK)",
        "- candidate_id: UUID (FK)",
        "- status: InterviewStatus",
        "- plan: JSONB",
        "- ai_consent: Boolean",
        "- active_seconds: Float",
        "- finish_reason: FinishReason",
        "- retry_of_id: UUID (FK, Nullable)",
        "- created_at: DateTime",
        "- updated_at: DateTime"
    ], [
        "+ is_active(): bool",
        "+ time_remaining(): float",
        "+ apply_transition(event): void"
    ])

    # 6. InterviewQuestion
    draw_class(10.8, 3.2, 4.8, 3.6, "InterviewQuestion (Model)", [
        "- id: UUID (PK)",
        "- session_id: UUID (FK)",
        "- seq: Integer",
        "- question_kind: QuestionKind",
        "- text: String(640)",
        "- source: QuestionSource (AI|RULES)",
        "- answer_kind: AnswerKind",
        "- answer_text: String(10000)",
        "- evaluation_status: EvalStatus",
        "- asked_at: DateTime"
    ], [
        "+ submit_answer(kind, text): void",
        "+ mark_evaluated(status): void"
    ])

    # 7. AnswerEvaluation
    draw_class(10.8, 0.2, 4.8, 2.7, "AnswerEvaluation (Model)", [
        "- id: UUID (PK)",
        "- question_id: UUID (FK, Unique)",
        "- rubric: String",
        "- source: EvalSource (AI|RULES)",
        "- missing_concepts: JSONB",
        "- claims_to_verify: JSONB",
        "- feedback: String(600)"
    ])

    # 8. ModelGateway (Service)
    draw_class(0.5, 0.4, 4.2, 3.5, "ModelGateway (Service)", [
        "- providers: list[ModelProvider]",
        "- timeout_seconds: float",
        "- max_retries: int",
        "- daily_budget_limit: int"
    ], [
        "+ generate_structured(req, Schema)",
        "+ route_capability(cap): Provider",
        "+ validate_output(raw_json, Schema)",
        "+ execute_with_fallback(req)"
    ])

    # 9. InterviewStateMachine (Service)
    draw_class(5.5, 0.4, 4.6, 3.4, "InterviewStateMachine", [
        "- transitions: dict[tuple, Status]",
        "- finish_reasons: dict"
    ], [
        "+ create_session(db, candidate_id)",
        "+ apply_event(db, session_id, event)",
        "+ next_status(status, event)",
        "+ check_fact_invariants(db, sid)"
    ])

    # Draw Relationship Lines
    # Candidate -> AuthSession (1 to many)
    ax.annotate("", xy=(2.6, 7.1), xytext=(2.6, 7.8),
                arrowprops=dict(arrowstyle="-|>", color="#1E293B", lw=1.5))
    ax.text(2.8, 7.4, "1..* owns", fontsize=8, color="#475569")

    # Candidate -> Resume (1 to many)
    ax.annotate("", xy=(5.5, 9.5), xytext=(4.7, 9.5),
                arrowprops=dict(arrowstyle="-|>", color="#1E293B", lw=1.5))
    ax.text(4.8, 9.65, "1..* uploads", fontsize=8, color="#475569")

    # Candidate -> CandidateFact (1 to many)
    ax.annotate("", xy=(5.5, 6.0), xytext=(4.7, 8.5),
                arrowprops=dict(arrowstyle="-|>", color="#1E293B", lw=1.5))
    ax.text(4.8, 6.9, "1..* profile", fontsize=8, color="#475569")

    # Candidate -> InterviewSession (1 to many)
    ax.annotate("", xy=(10.8, 9.5), xytext=(10.1, 9.5),
                arrowprops=dict(arrowstyle="-|>", color="#1E293B", lw=1.5))
    ax.text(10.2, 9.65, "1..* practices", fontsize=8, color="#475569")

    # Resume -> CandidateFact (1 to many)
    ax.annotate("", xy=(7.8, 7.4), xytext=(7.8, 7.8),
                arrowprops=dict(arrowstyle="-|>", color="#1E293B", lw=1.5))
    ax.text(8.0, 7.55, "1..* contains", fontsize=8, color="#475569")

    # InterviewSession -> InterviewQuestion (1 to many)
    ax.annotate("", xy=(13.2, 6.8), xytext=(13.2, 7.2),
                arrowprops=dict(arrowstyle="-|>", color="#1E293B", lw=1.5))
    ax.text(13.4, 6.95, "1..* questions", fontsize=8, color="#475569")

    # InterviewQuestion -> AnswerEvaluation (1 to 1)
    ax.annotate("", xy=(13.2, 2.9), xytext=(13.2, 3.2),
                arrowprops=dict(arrowstyle="-|>", color="#1E293B", lw=1.5))
    ax.text(13.4, 3.0, "1..1 evaluated", fontsize=8, color="#475569")

    save_fig(fig, "3.2_class_diagram.png")

# ==========================================
# 3. ACTIVITY DIAGRAM (Figure 3.3)
# ==========================================
def generate_activity_diagram():
    fig, ax = plt.subplots(figsize=(10, 13))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 13)
    ax.axis("off")

    ax.text(5, 12.6, "Figure 3.3: Activity Diagram — End-to-End Operational Lifecycle", 
            ha="center", va="center", fontsize=13, fontweight="bold", color=TEXT_COLOR)

    # Helper: draw action state
    def draw_action(x, y, text, w=4.4, h=0.55):
        rect = FancyBboxPatch((x - w/2, y - h/2), w, h, boxstyle="round,pad=0.15",
                              ec="#2563EB", fc="#EFF6FF", lw=1.5)
        ax.add_patch(rect)
        ax.text(x, y, text, ha="center", va="center", fontsize=8.2, fontweight="medium", color="#1E293B")

    # Helper: draw decision diamond
    def draw_decision(x, y, text, size=0.45):
        diamond = patches.RegularPolygon((x, y), 4, radius=size, orientation=0,
                                         ec="#D97706", fc="#FEF3C7", lw=1.5)
        ax.add_patch(diamond)
        ax.text(x, y, text, ha="center", va="center", fontsize=7.5, fontweight="bold", color="#92400E")

    # Start Node
    start = plt.Circle((5, 12.1), 0.18, color="#1E293B")
    ax.add_patch(start)

    actions = [
        ("Candidate Sign In & Authenticate", 11.4),
        ("Upload PDF Resume or Enter Manual Profile Facts", 10.6),
        ("Extract Verbatim Resume Sections & Facts", 9.8),
    ]

    for text, y in actions:
        draw_action(5, y, text)

    # Decision: Profile review complete?
    draw_decision(5, 8.9, "Pending\nFacts?")

    # Branch: Review facts
    draw_action(1.8, 8.9, "Candidate Reviews Facts\n(Approve / Reject / Edit)", w=2.8, h=0.6)

    # Plan creation
    draw_action(5, 7.9, "Configure Interview & Manage AI Consent")
    draw_action(5, 7.1, "Generate & Validate Interview Plan (AI/RULES)")

    # Start turn loop
    draw_action(5, 6.2, "Fetch Next Turn: Orchestrator Selects Question")

    # Decision: Deadline passed?
    draw_decision(5, 5.3, "Time\nRemaining\n< 60s?")

    # Interview Question Action
    draw_action(5, 4.3, "Candidate Answers (Text / Speech Review)")

    # Decision: More questions or time left?
    draw_decision(5, 3.4, "Plan Done\nor Candidate\nEnded?")

    # Evaluation
    draw_action(5, 2.4, "Post-Interview Rubric Evaluation (AI/RULES)")
    draw_action(5, 1.6, "Build Deterministic Non-Aggregated Report")

    # Decision: Retry?
    draw_decision(5, 0.9, "Retry\nTopics?")

    # End Node
    end_outer = plt.Circle((5, 0.2), 0.20, ec="#1E293B", fc="none", lw=1.5)
    end_inner = plt.Circle((5, 0.2), 0.13, color="#1E293B")
    ax.add_patch(end_outer)
    ax.add_patch(end_inner)

    # Connecting arrows
    arrow_args = dict(arrowstyle="->", color="#334155", lw=1.3)
    ax.annotate("", xy=(5, 11.7), xytext=(5, 11.92), arrowprops=arrow_args)
    ax.annotate("", xy=(5, 10.9), xytext=(5, 11.1), arrowprops=arrow_args)
    ax.annotate("", xy=(5, 10.1), xytext=(5, 10.3), arrowprops=arrow_args)
    ax.annotate("", xy=(5, 9.25), xytext=(5, 9.5), arrowprops=arrow_args)

    # Pending facts branch
    ax.annotate("Yes", xy=(3.2, 8.9), xytext=(4.55, 8.9), arrowprops=arrow_args, fontsize=8)
    ax.annotate("", xy=(5, 9.6), xytext=(1.8, 9.2), arrowprops=arrow_args) # loops back
    ax.annotate("No [Approved]", xy=(5, 8.2), xytext=(5, 8.55), arrowprops=arrow_args, fontsize=8, ha="left")

    ax.annotate("", xy=(5, 7.4), xytext=(5, 7.6), arrowprops=arrow_args)
    ax.annotate("", xy=(5, 6.5), xytext=(5, 6.8), arrowprops=arrow_args)
    ax.annotate("", xy=(5, 5.65), xytext=(5, 5.9), arrowprops=arrow_args)

    # Time check branch
    ax.annotate("No [Active]", xy=(5, 4.6), xytext=(5, 4.95), arrowprops=arrow_args, fontsize=8, ha="left")
    ax.annotate("Yes [Expired]", xy=(7.4, 2.4), xytext=(5.4, 5.3), arrowprops=arrow_args, fontsize=8)

    ax.annotate("", xy=(5, 3.75), xytext=(5, 4.0), arrowprops=arrow_args)

    # Decision loop
    ax.annotate("No", xy=(8.2, 6.2), xytext=(5.45, 3.4), arrowprops=arrow_args, fontsize=8)
    ax.annotate("", xy=(7.2, 6.2), xytext=(8.2, 6.2), arrowprops=arrow_args)

    ax.annotate("Yes", xy=(5, 2.7), xytext=(5, 3.05), arrowprops=arrow_args, fontsize=8, ha="left")
    ax.annotate("", xy=(5, 1.9), xytext=(5, 2.1), arrowprops=arrow_args)
    ax.annotate("", xy=(5, 1.25), xytext=(5, 1.3), arrowprops=arrow_args)

    ax.annotate("Yes [New Session]", xy=(1.5, 7.1), xytext=(4.6, 0.9), arrowprops=arrow_args, fontsize=8)
    ax.annotate("No [Done]", xy=(5, 0.4), xytext=(5, 0.55), arrowprops=arrow_args, fontsize=8, ha="left")

    save_fig(fig, "3.3_activity_diagram.png")

# ==========================================
# 4. SEQUENCE DIAGRAM (Figure 3.4)
# ==========================================
def generate_sequence_diagram():
    fig, ax = plt.subplots(figsize=(15, 11))
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 11)
    ax.axis("off")

    ax.text(7.5, 10.6, "Figure 3.4: Sequence Diagram — Interactive Turn Orchestration & Verification", 
            ha="center", va="center", fontsize=13, fontweight="bold", color=TEXT_COLOR)

    lifelines = [
        ("Candidate\n(Browser)", 1.2),
        ("Next.js UI\n(App Router)", 3.4),
        ("FastAPI API\n(/questions/next)", 5.8),
        ("State Machine\n(Row Lock)", 8.2),
        ("Interviewer\n(Service)", 10.4),
        ("ModelGateway\n(Validation)", 12.6),
        ("PostgreSQL\n(DB Session)", 14.4),
    ]

    for name, x in lifelines:
        box = FancyBboxPatch((x - 0.9, 9.7), 1.8, 0.7, boxstyle="round,pad=0.1",
                             ec="#1E293B", fc="#E2E8F0", lw=1.2)
        ax.add_patch(box)
        ax.text(x, 10.05, name, ha="center", va="center", fontsize=8, fontweight="bold", color="#0F172A")
        # Lifeline dash
        ax.plot([x, x], [0.8, 9.7], color="#94A3B8", lw=1, linestyle="--")

    # Sequence calls
    messages = [
        (1.2, 3.4, 9.2, "1: Click 'Start Interview'", False),
        (3.4, 5.8, 8.8, "2: POST /api/interview-sessions/{id}/questions/next", False),
        (5.8, 8.2, 8.4, "3: lock_session_row() [SELECT FOR UPDATE]", False),
        (8.2, 14.4, 8.0, "4: Execute query & verify candidate ownership", False),
        (5.8, 10.4, 7.5, "5: decide_next(plan, clock, history, facts)", False),
        (10.4, 5.8, 7.1, "6: Action = FOLLOW_UP (Term: 'trade-offs')", True),
        (5.8, 8.2, 6.7, "7: commit() [Release lock before model call]", False),
        (5.8, 12.6, 6.2, "8: generate_structured(QUESTION_GENERATION, Schema)", False),
        (12.6, 12.6, 5.7, "9: Provider routing & schema validation check", False), # self call
        (12.6, 5.8, 5.2, "10: Return validated ModelResult[QuestionWording]", True),
        (5.8, 8.2, 4.7, "11: re_lock_session() & re-verify AI consent", False),
        (8.2, 14.4, 4.2, "12: apply_event(QUESTION_ASKED) & persist question", False),
        (5.8, 3.4, 3.7, "13: HTTP 200 OK (question, timer, progress)", True),
        (3.4, 1.2, 3.3, "14: Render question turn & start client countdown", True),
        (1.2, 3.4, 2.7, "15: Submit answer text ('I chose SQLite because...')", False),
        (3.4, 5.8, 2.3, "16: POST /api/interview-sessions/{id}/answers", False),
        (5.8, 14.4, 1.8, "17: Store answer (evaluation_status = NOT_EVALUATED)", False),
        (5.8, 3.4, 1.3, "18: HTTP 200 OK (status: ANSWER_PROCESSING)", True),
    ]

    for x1, x2, y, msg, is_return in messages:
        if x1 == x2: # self call
            ax.plot([x1, x1 + 0.5, x1 + 0.5, x1], [y + 0.15, y + 0.15, y - 0.15, y - 0.15],
                    color="#4F46E5", lw=1.2)
            ax.text(x1 + 0.6, y, msg, ha="left", va="center", fontsize=7.2, color="#4F46E5", fontweight="bold")
        else:
            style = "-->" if is_return else "->"
            line_style = ":" if is_return else "-"
            ax.annotate("", xy=(x2, y), xytext=(x1, y),
                        arrowprops=dict(arrowstyle="->", color="#1E3A8A" if not is_return else "#047857",
                                        lw=1.2, linestyle=line_style))
            mid_x = (x1 + x2) / 2
            ax.text(mid_x, y + 0.14, msg, ha="center", va="bottom", fontsize=7.2,
                    fontweight="medium", color="#1E293B")

    save_fig(fig, "3.4_sequence_diagram.png")

# ==========================================
# 5. STATE MACHINE DIAGRAM (Figure 3.5)
# ==========================================
def generate_state_machine():
    fig, ax = plt.subplots(figsize=(15, 11))
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 11)
    ax.axis("off")

    ax.text(7.5, 10.6, "Figure 3.5: State Machine Diagram — Interview Session Lifecycle", 
            ha="center", va="center", fontsize=13, fontweight="bold", color=TEXT_COLOR)

    def draw_state(x, y, name, w=2.4, h=0.7):
        box = FancyBboxPatch((x - w/2, y - h/2), w, h, boxstyle="round,pad=0.15",
                             ec="#1E40AF", fc="#DBEAFE", lw=1.5)
        ax.add_patch(box)
        ax.text(x, y, name, ha="center", va="center", fontsize=8.2, fontweight="bold", color="#1E3A8A")

    # States
    draw_state(1.8, 9.6, "CREATED")
    draw_state(5.0, 9.6, "PROFILE_PROCESSING")
    draw_state(8.5, 9.6, "PROFILE_REVIEW")
    draw_state(12.5, 9.6, "INTERVIEW_PLANNING")
    draw_state(12.5, 7.8, "READY")
    draw_state(8.5, 7.8, "ASKING")
    draw_state(4.5, 7.8, "WAITING_FOR_ANSWER")
    draw_state(1.5, 7.8, "PAUSED")
    draw_state(4.5, 5.6, "ANSWER_PROCESSING")
    draw_state(8.5, 5.6, "ANSWER_EVALUATION")
    draw_state(12.5, 5.6, "NEXT_DECISION")
    draw_state(8.5, 3.4, "REPORT_GENERATION")
    draw_state(8.5, 1.6, "COMPLETED\n(Terminal)")

    arrow_args = dict(arrowstyle="->", color="#334155", lw=1.3)

    # Initial transition
    start = plt.Circle((0.5, 9.6), 0.15, color="#1E293B")
    ax.add_patch(start)
    ax.annotate("", xy=(0.6, 9.6), xytext=(0.4, 9.6), arrowprops=arrow_args)

    # CREATED -> PROFILE_PROCESSING -> PROFILE_REVIEW -> INTERVIEW_PLANNING
    ax.annotate("PROFILE_PROCESSING_STARTED", xy=(3.8, 9.6), xytext=(3.0, 9.6), arrowprops=arrow_args, fontsize=6.5, ha="center", va="bottom")
    ax.annotate("PROFILE_READY", xy=(7.3, 9.6), xytext=(6.2, 9.6), arrowprops=arrow_args, fontsize=6.5, ha="center", va="bottom")
    ax.annotate("CONFIRM_PROFILE [facts reviewed]", xy=(11.3, 9.6), xytext=(9.7, 9.6), arrowprops=arrow_args, fontsize=6.5, ha="center", va="bottom")

    # INTERVIEW_PLANNING -> READY -> ASKING -> WAITING_FOR_ANSWER
    ax.annotate("PLAN_READY [plan valid]", xy=(12.5, 8.2), xytext=(12.5, 9.25), arrowprops=arrow_args, fontsize=6.5, ha="center", va="center")
    ax.annotate("START_INTERVIEW", xy=(9.7, 7.8), xytext=(11.3, 7.8), arrowprops=arrow_args, fontsize=6.5, ha="center", va="bottom")
    ax.annotate("QUESTION_ASKED", xy=(5.7, 7.8), xytext=(7.3, 7.8), arrowprops=arrow_args, fontsize=6.5, ha="center", va="bottom")

    # Pause / Resume
    ax.annotate("PAUSE", xy=(2.7, 7.95), xytext=(3.3, 7.95), arrowprops=arrow_args, fontsize=6.5, ha="center", va="bottom")
    ax.annotate("RESUME", xy=(3.3, 7.65), xytext=(2.7, 7.65), arrowprops=arrow_args, fontsize=6.5, ha="center", va="top")

    # WAITING_FOR_ANSWER -> ANSWER_PROCESSING -> ANSWER_EVALUATION -> NEXT_DECISION
    ax.annotate("ANSWER_SUBMITTED", xy=(4.5, 6.0), xytext=(4.5, 7.4), arrowprops=arrow_args, fontsize=6.5, ha="center", va="center")
    ax.annotate("ANSWER_PROCESSED", xy=(7.3, 5.6), xytext=(5.7, 5.6), arrowprops=arrow_args, fontsize=6.5, ha="center", va="bottom")
    ax.annotate("ANSWER_EVALUATED", xy=(11.3, 5.6), xytext=(9.7, 5.6), arrowprops=arrow_args, fontsize=6.5, ha="center", va="bottom")

    # Decisions back to ASKING or FINISH
    ax.annotate("FOLLOW_UP / NEXT_TOPIC / REPHRASE", xy=(9.7, 7.6), xytext=(12.5, 6.0),
                arrowprops=dict(arrowstyle="->", color="#2563EB", lw=1.2, connectionstyle="arc3,rad=-0.2"),
                fontsize=7, color="#2563EB", fontweight="bold")
    ax.annotate("FINISH [PLAN_COMPLETED / TIME_LIMIT]", xy=(9.7, 3.7), xytext=(12.5, 5.2),
                arrowprops=dict(arrowstyle="->", color="#059669", lw=1.2, connectionstyle="arc3,rad=0.2"),
                fontsize=7, color="#059669", fontweight="bold")

    # Early End & Time Expired edges
    ax.annotate("END_INTERVIEW / TIME_EXPIRED", xy=(7.3, 3.4), xytext=(4.5, 7.4),
                arrowprops=dict(arrowstyle="->", color="#DC2626", lw=1.2, connectionstyle="arc3,rad=0.3"),
                fontsize=7, color="#DC2626", fontweight="bold")

    # REPORT_GENERATION -> COMPLETED
    ax.annotate("REPORT_READY [POST /report]", xy=(8.5, 2.0), xytext=(8.5, 3.0),
                arrowprops=arrow_args, fontsize=7.5, ha="center", va="center")

    save_fig(fig, "3.5_state_machine_diagram.png")

# ==========================================
# 6. COMMUNICATION DIAGRAM (Figure 3.6)
# ==========================================
def generate_communication_diagram():
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis("off")

    ax.text(7, 9.6, "Figure 3.6: Communication Diagram — Turn Processing & Evaluation Collaboration", 
            ha="center", va="center", fontsize=13, fontweight="bold", color=TEXT_COLOR)

    def draw_node(x, y, label, w=3.0, h=0.9):
        box = FancyBboxPatch((x - w/2, y - h/2), w, h, boxstyle="round,pad=0.1",
                             ec="#1E293B", fc="#F1F5F9", lw=1.5)
        ax.add_patch(box)
        ax.text(x, y, label, ha="center", va="center", fontsize=8.5, fontweight="bold", color="#1E3A8A")

    nodes = {
        "UI": (2.0, 7.5, ":CandidateClientUI"),
        "Router": (7.0, 7.5, ":InterviewRouter"),
        "FSM": (12.0, 7.5, ":StateMachine"),
        "Interviewer": (7.0, 4.5, ":InterviewerService"),
        "Gateway": (2.0, 4.5, ":ModelGateway"),
        "Evaluator": (12.0, 4.5, ":EvaluatorService"),
        "DB": (7.0, 1.5, ":DatabaseSession"),
    }

    for k, (x, y, lbl) in nodes.items():
        draw_node(x, y, lbl)

    # Helper: draw numbered communication arrow between nodes
    def draw_comm_link(n1, n2, messages):
        x1, y1, _ = nodes[n1]
        x2, y2, _ = nodes[n2]
        ax.plot([x1, x2], [y1, y2], color="#94A3B8", lw=1.5)
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        # Text offset
        offset_y = 0.25 * (len(messages) / 2)
        for i, (num, text, direction) in enumerate(messages):
            arrow = "→" if direction == "fwd" else "←"
            ax.text(mid_x, mid_y + offset_y - i * 0.28, f"{num} {arrow} {text}",
                    ha="center", va="center", fontsize=7.5, fontweight="medium",
                    bbox=dict(boxstyle="round,pad=0.1", fc="#FFFFFF", ec="#CBD5E1", lw=0.8))

    draw_comm_link("UI", "Router", [
        ("1.0", "submit_turn_action()", "fwd"),
        ("1.8", "return_turn_response()", "rev")
    ])

    draw_comm_link("Router", "FSM", [
        ("1.1", "apply_event(CONFIRM_PROFILE)", "fwd"),
        ("1.6", "apply_event(QUESTION_ASKED)", "fwd")
    ])

    draw_comm_link("Router", "Interviewer", [
        ("1.2", "decide_next(session)", "fwd"),
        ("1.5", "format_question()", "rev")
    ])

    draw_comm_link("Interviewer", "Gateway", [
        ("1.3", "generate_structured(Q_GEN)", "fwd"),
        ("1.4", "return_validated_wording()", "rev")
    ])

    draw_comm_link("Router", "Evaluator", [
        ("2.1", "evaluate_answer(rubric)", "fwd"),
        ("2.4", "return_scores_and_quotes()", "rev")
    ])

    draw_comm_link("Router", "DB", [
        ("1.7", "commit_transaction()", "fwd")
    ])

    draw_comm_link("Evaluator", "DB", [
        ("2.2", "store_evaluation_row()", "fwd")
    ])

    save_fig(fig, "3.6_communication_diagram.png")

# ==========================================
# 7. COMPONENT DIAGRAM (Figure 3.7)
# ==========================================
def generate_component_diagram():
    fig, ax = plt.subplots(figsize=(15, 11))
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 11)
    ax.axis("off")

    ax.text(7.5, 10.6, "Figure 3.7: Component Diagram — Architectural Subsystems & Interfaces", 
            ha="center", va="center", fontsize=13, fontweight="bold", color=TEXT_COLOR)

    def draw_component(x, y, w, h, name, sub_items):
        box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.15",
                             ec="#1E40AF", fc="#F8FAFC", lw=1.5)
        ax.add_patch(box)
        # Tab
        tab = FancyBboxPatch((x + 0.2, y + h - 0.45), w - 0.4, 0.45, boxstyle="round,pad=0.05",
                             ec="#1E40AF", fc="#DBEAFE", lw=1)
        ax.add_patch(tab)
        ax.text(x + w/2, y + h - 0.22, f"«component» {name}", ha="center", va="center",
                fontsize=8.5, fontweight="bold", color="#1E3A8A")

        curr_y = y + h - 0.7
        for item in sub_items:
            ax.text(x + 0.3, curr_y, f"• {item}", ha="left", va="center", fontsize=7.5, color="#334155")
            curr_y -= 0.3

    # Layer 1: Frontend Client Components
    draw_component(0.5, 6.0, 4.2, 4.0, "Frontend Presentation Subsystem", [
        "Next.js App Router (app/)",
        "Interview Flow (InterviewFlow.tsx)",
        "Expression Camera (useExpressionCamera.ts)",
        "Voice Assistant (useVoice.ts / VoicePanel)",
        "Document Export Engine (exportDoc.ts)",
        "API Gateway Client (lib/api.ts)"
    ])

    # Layer 2: Backend API & Core
    draw_component(5.3, 6.0, 4.4, 4.0, "FastAPI Service Application", [
        "App Factory & CORS Config (app/main.py)",
        "Session Auth Guard (api/deps.py)",
        "Candidate & Resume Routers",
        "Interview Sessions Router",
        "Deterministic State Machine",
        "Rate & Abuse Limiter (limits.py)"
    ])

    # Layer 3: AI Model Subsystem
    draw_component(10.3, 6.0, 4.2, 4.0, "AI Model Gateway Subsystem", [
        "ModelGateway (app/ai/gateway.py)",
        "Provider Adapters (Gemini, Groq, NVIDIA)",
        "ProfileAgent (Resume Grounding)",
        "PlannerAgent (Plan Schema Boundary)",
        "InterviewerAgent (Follow-up Wording)",
        "EvaluatorAgent (Rubric Scoring)"
    ])

    # Layer 4: Storage & Persistence
    draw_component(2.5, 0.8, 5.0, 4.0, "Data Persistence Layer", [
        "SQLAlchemy 2.0 Declarative Engine",
        "Candidate & Resume Models",
        "Interview Sessions & Questions",
        "Answer Evaluations & Criteria",
        "Expression Observations & Usage Counters",
        "Alembic Database Migration Pipeline"
    ])

    # Layer 5: External Services & On-Device ML
    draw_component(8.2, 0.8, 4.5, 4.0, "External & Client Execution Runtimes", [
        "On-Device face-api.js (TensorFlow.js)",
        "Google Generative AI (Gemini 2.5 Flash)",
        "Groq Cloud Inference (Llama 3.3)",
        "NVIDIA NIM Hosted Services",
        "PostgreSQL 14+ Relational Engine"
    ])

    # Connecting dependency arrows
    arrow_args = dict(arrowstyle="-|>", color="#2563EB", lw=1.5)
    ax.annotate("HTTP / REST (JSON)", xy=(5.3, 8.0), xytext=(4.7, 8.0), arrowprops=arrow_args, fontsize=7.5, ha="center", va="bottom")
    ax.annotate("Internal Service Calls", xy=(10.3, 8.0), xytext=(9.7, 8.0), arrowprops=arrow_args, fontsize=7.5, ha="center", va="bottom")
    ax.annotate("ORM Relational Mappings", xy=(5.0, 4.8), xytext=(6.5, 6.0), arrowprops=arrow_args, fontsize=7.5, ha="center")
    ax.annotate("HTTPS / TLS 1.3", xy=(10.5, 4.8), xytext=(12.0, 6.0), arrowprops=arrow_args, fontsize=7.5, ha="center")

    save_fig(fig, "3.7_component_diagram.png")

# ==========================================
# 8. DEPLOYMENT DIAGRAM (Figure 3.8)
# ==========================================
def generate_deployment_diagram():
    fig, ax = plt.subplots(figsize=(15, 11))
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 11)
    ax.axis("off")

    ax.text(7.5, 10.6, "Figure 3.8: Deployment Diagram — Distributed System Infrastructure", 
            ha="center", va="center", fontsize=13, fontweight="bold", color=TEXT_COLOR)

    def draw_node(x, y, w, h, name, sub_text):
        # 3D Node box effect
        d = 0.25
        # Front face
        rect = patches.Rectangle((x, y), w, h, ec="#1E293B", fc="#F8FAFC", lw=1.5)
        ax.add_patch(rect)
        # Top face
        top = patches.Polygon([[x, y + h], [x + d, y + h + d], [x + w + d, y + h + d], [x + w, y + h]],
                              ec="#1E293B", fc="#CBD5E1", lw=1.2)
        ax.add_patch(top)
        # Side face
        side = patches.Polygon([[x + w, y], [x + w + d, y + d], [x + w + d, y + h + d], [x + w, y + h]],
                               ec="#1E293B", fc="#94A3B8", lw=1.2)
        ax.add_patch(side)

        ax.text(x + w/2, y + h - 0.35, f"«device / execution node»\n{name}", ha="center", va="center",
                fontsize=8.5, fontweight="bold", color="#1E3A8A")

        curr_y = y + h - 0.8
        for t in sub_text:
            ax.text(x + 0.25, curr_y, t, ha="left", va="center", fontsize=7.5, color="#334155")
            curr_y -= 0.28

    # Node 1: Candidate Client Device
    draw_node(0.5, 4.5, 4.2, 5.0, "Candidate Client Machine\n(Browser Runtime)", [
        "• Modern Browser (Edge / Chrome / Firefox)",
        "• Next.js SPA Web Client",
        "• On-Device face-api.js (WebGL/WASM)",
        "• Web Speech API (Synthesis/Recognition)",
        "• LocalStorage (Theme & Audio Settings)",
        "• Client-Side HTML/PDF Export Engine",
        "• Privacy: Zero Raw Video Transmission"
    ])

    # Node 2: Web / API Application Server
    draw_node(5.5, 4.5, 4.2, 5.0, "Backend Application Server\n(Linux / Windows Container)", [
        "• Python 3.11+ ASGI Execution Environment",
        "• Uvicorn Production Web Server",
        "• FastAPI Application Instance",
        "• Pure Python pypdf 6.x Extractor",
        "• Deterministic Orchestrator & State Machine",
        "• Model Gateway & Capability Router",
        "• Pydantic v2 Schema Validation Engine"
    ])

    # Node 3: Database Server Node
    draw_node(10.5, 4.5, 4.0, 5.0, "Database Server Node\n(Enterprise Storage Engine)", [
        "• PostgreSQL 14+ Relational Engine",
        "• Database: ai_interview_coach",
        "• Schema: Tables, Indexes, Constraints",
        "• Isolation: Explicit Row-Level Locks",
        "• Alembic Versioned Migrations",
        "• SSL/TLS Encrypted Connection Pool",
        "• Cascade Deletions & Partial Indexes"
    ])

    # Node 4: Cloud AI Services Node
    draw_node(5.5, 0.4, 4.2, 3.2, "External AI Provider Cloud\n(Stateless API Endpoints)", [
        "• Google Gemini 2.5 Flash API",
        "• Groq Cloud (Llama 3.3 / GPT-OSS)",
        "• NVIDIA NIM Hosted Models",
        "• OpenAI-Compatible JSON Schema Mode"
    ])

    # Communication Links
    ax.annotate("HTTP / HTTPS (Port 3000 / 8000)\nSame-Site HttpOnly Cookie", xy=(5.5, 7.0), xytext=(4.7, 7.0),
                arrowprops=dict(arrowstyle="<|-|>", color="#2563EB", lw=1.5),
                fontsize=7.5, ha="center", va="bottom")

    ax.annotate("PostgreSQL Wire Protocol\npsycopg 3 (Port 5432)", xy=(10.5, 7.0), xytext=(9.7, 7.0),
                arrowprops=dict(arrowstyle="<|-|>", color="#059669", lw=1.5),
                fontsize=7.5, ha="center", va="bottom")

    ax.annotate("HTTPS / TLS 1.3 (Port 443)\nBearer API Keys (SecretStr)", xy=(7.6, 3.7), xytext=(7.6, 4.5),
                arrowprops=dict(arrowstyle="<|-|>", color="#9333EA", lw=1.5),
                fontsize=7.5, ha="center", va="center")

    save_fig(fig, "3.8_deployment_diagram.png")

# ==========================================
# 9. PACKAGE DIAGRAM (Figure 3.9)
# ==========================================
def generate_package_diagram():
    fig, ax = plt.subplots(figsize=(15, 11))
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 11)
    ax.axis("off")

    ax.text(7.5, 10.6, "Figure 3.9: Package Diagram — Modular Organization & Namespace Boundaries", 
            ha="center", va="center", fontsize=13, fontweight="bold", color=TEXT_COLOR)

    def draw_package(x, y, w, h, name, sub_packages):
        # Package tab
        tab_w = min(1.8, w * 0.4)
        tab_h = 0.35
        tab = patches.Rectangle((x, y + h), tab_w, tab_h, ec="#334155", fc="#CBD5E1", lw=1.2)
        ax.add_patch(tab)
        ax.text(x + tab_w/2, y + h + tab_h/2, name.split(".")[0], ha="center", va="center",
                fontsize=7.5, fontweight="bold", color="#1E293B")

        # Package body
        body = patches.Rectangle((x, y), w, h, ec="#334155", fc="#F8FAFC", lw=1.2)
        ax.add_patch(body)
        ax.text(x + w/2, y + h - 0.25, name, ha="center", va="center",
                fontsize=8.5, fontweight="bold", color="#1E3A8A")

        curr_y = y + h - 0.6
        for sp in sub_packages:
            sp_box = FancyBboxPatch((x + 0.2, curr_y - 0.35), w - 0.4, 0.4, boxstyle="round,pad=0.05",
                                    ec="#94A3B8", fc="#FFFFFF", lw=1)
            ax.add_patch(sp_box)
            ax.text(x + w/2, curr_y - 0.15, sp, ha="center", va="center", fontsize=7.2, color="#334155")
            curr_y -= 0.48

    # Frontend Packages
    draw_package(0.5, 5.2, 4.2, 4.8, "frontend", [
        "app (Next.js pages & layout)",
        "components (UI widgets & forms)",
        "components.interview (flow, turns)",
        "lib.api (fetch wrapper)",
        "lib.interview & auth (state logic)",
        "lib.expressions & voice (signals)",
        "lib.exportDoc (self-contained HTML)"
    ])

    # Backend App Packages
    draw_package(5.4, 5.2, 4.4, 4.8, "backend.app", [
        "app.api (deps & routes)",
        "app.core (config & scrypt security)",
        "app.db (declarative Base & session)",
        "app.models (SQLAlchemy entities)",
        "app.schemas (Pydantic API models)",
        "app.services (FSM, limits, planner)",
        "app.ai (gateway & provider adapters)"
    ])

    # Quality Assurance / Test Packages
    draw_package(10.4, 5.2, 4.2, 4.8, "tests & verification", [
        "tests.unit (pytest 4693 tests)",
        "tests.fakes (scripted AI providers)",
        "tests.test_state_machine (FSM tests)",
        "tests.test_limits & auth (lockout)",
        "e2e.journey.mjs (37 browser checks)",
        "frontend.lib.*.test.ts (45 node tests)",
        "e2e.live_smoke.py (real API checks)"
    ])

    # Alembic Migrations
    draw_package(5.4, 1.0, 4.4, 3.4, "backend.alembic", [
        "alembic.versions (13 revisions)",
        "alembic.env (metadata & connection)",
        "constraints & naming conventions",
        "one_active_session partial index",
        "strict cascade rules on foreign keys"
    ])

    # Package Dependency Arrows
    arrow_args = dict(arrowstyle="-|>", color="#2563EB", lw=1.5, linestyle="--")
    ax.annotate("«imports / REST»", xy=(5.4, 7.6), xytext=(4.7, 7.6), arrowprops=arrow_args, fontsize=7.5, ha="center", va="bottom")
    ax.annotate("«verifies»", xy=(9.8, 7.6), xytext=(10.4, 7.6), arrowprops=arrow_args, fontsize=7.5, ha="center", va="bottom")
    ax.annotate("«migrates schema»", xy=(7.6, 4.4), xytext=(7.6, 5.2), arrowprops=arrow_args, fontsize=7.5, ha="center", va="center")

    save_fig(fig, "3.9_package_diagram.png")

if __name__ == "__main__":
    print("Generating 9 UML diagrams...")
    generate_use_case()
    generate_class_diagram()
    generate_activity_diagram()
    generate_sequence_diagram()
    generate_state_machine()
    generate_communication_diagram()
    generate_component_diagram()
    generate_deployment_diagram()
    generate_package_diagram()
    print("All 9 UML diagrams generated successfully!")
