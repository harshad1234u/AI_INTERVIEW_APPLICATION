// Run with `npm test` (node --test; Node strips the TypeScript types).
import { test } from "node:test";
import assert from "node:assert/strict";
import { FACT_CATEGORIES, categoryError, factTextError, normalizeFact } from "./profile.ts";

test("whitespace is normalized like the server's FactText rule", () => {
  assert.equal(normalizeFact("  Spring   Boot \t"), "Spring Boot");
  assert.equal(normalizeFact("a\n\nb"), "a b");
  assert.equal(normalizeFact("   "), "");
});

test("fact text: empty, whitespace-only and over 200 characters are refused", () => {
  assert.equal(factTextError(""), "Enter some text.");
  assert.equal(factTextError(" \t\n "), "Enter some text.");
  assert.equal(factTextError("x".repeat(201)), "Use at most 200 characters.");
});

test("fact text: 1 and exactly 200 characters are fine, measured after trimming", () => {
  assert.equal(factTextError("x"), null);
  assert.equal(factTextError("x".repeat(200)), null);
  assert.equal(factTextError(`  ${"x".repeat(200)}  `), null);
});

test("categories are exactly the backend's, and nothing else is accepted", () => {
  assert.deepEqual(FACT_CATEGORIES.map(([value]) => value),
                   ["SKILL", "PROJECT", "EXPERIENCE", "EDUCATION", "CERTIFICATION"]);
  for (const [value] of FACT_CATEGORIES) assert.equal(categoryError(value), null);
  for (const bad of ["", "skill", "HOBBY"]) assert.equal(categoryError(bad), "Choose a category.");
});
