// Pure profile-fact rules, shared by the resume review and manual entry, and run by `node --test`.
// They mirror the backend's FactText rule; the server validates again and has the last word.
import type { FactCategory } from "./api";

export const FACT_MAX_LENGTH = 200;

/** The backend's fact categories, in display order, with their headings. */
export const FACT_CATEGORIES: [FactCategory, string][] = [
  ["SKILL", "Skills"],
  ["PROJECT", "Projects"],
  ["EXPERIENCE", "Experience"],
  ["EDUCATION", "Education"],
  ["CERTIFICATION", "Certifications"],
];

export const MANUAL_LABEL = "Added by you";

/** Trims and collapses whitespace runs, exactly as the server stores a fact. */
export function normalizeFact(text: string): string {
  return text.split(/\s+/).filter(Boolean).join(" ");
}

/** null when the server would accept it; otherwise what to tell the candidate. */
export function factTextError(text: string): string | null {
  const fact = normalizeFact(text);
  if (!fact) return "Enter some text.";
  if (fact.length > FACT_MAX_LENGTH) return `Use at most ${FACT_MAX_LENGTH} characters.`;
  return null;
}

export function categoryError(category: string): string | null {
  return FACT_CATEGORIES.some(([value]) => value === category) ? null : "Choose a category.";
}
