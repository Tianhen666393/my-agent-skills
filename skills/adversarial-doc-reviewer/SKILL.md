---
name: adversarial-doc-reviewer
description: Conduct adversarial red-team reviews and dense, detail-preserving rewriting for academic papers, theses, proposals, defense materials, or sensitive reports. Use when the user uploads or shares an article, thesis, or report and asks to find loopholes, critique from an opposing or harsh perspective (such as a strict reviewer, thesis committee, or adversarial recipient), stress-test arguments, or defensively rewrite text while strictly preserving all facts, parameters, and evidence.
---

# Adversarial Doc Reviewer

## Summary
A two-round adversarial review and defense-refinement workflow. Simulates harsh reviewers or opposing parties to find logical loopholes and defensive vulnerabilities in uploaded drafts or reports, then tightly refines the text without deleting critical evidence or parameters.

## When to Use

- User uploads or attaches a thesis, academic paper, proof document, or complaint/proposal.
- User wants an adversarial critique (e.g., harsh blind reviewer, defensive supervisor, resistant management).
- User wants to find blind spots, logical vulnerabilities, and potential rebuttals before submission.
- User asks to tighten or condense text without losing facts, numbers, or logical links.

## Core Rules

1. Absolute Fact Preservation: Never drop data, parameters, experimental conditions, or logical milestones during revision.
2. Direct Critique: In round one, omit compliments and generic praise. Focus exclusively on critical attack points.
3. Citation Requirement: In critique mode, explicitly cite chapter names, section titles, or exact source quotes from the uploaded document to prevent hallucination.

## Workflow

### Round 1: Red-Team Critique (The Attack)
When user triggers review mode on a document, adopt the designated adversarial role:

- For academic papers/theses: Act as an uncompromising, strict blind reviewer (Reviewer 2). Target experimental rigor, methodology gaps, data over-interpretation, and vague terminology.
- For pressure/grievance/reporting materials: Act as the defensive opposing party or administrative lead. Target factual loopholes, potential counter-accusations, procedural excuses, and emotional or loose phrasing.

Output structure:

1. Fatal Flaws: Direct rejection or liability risks
2. Logical and Evidence Loopholes: Unclosed chains, missing controls
3. Precision and Phrasing Issues: Emotional words, filler, ambiguities

### Round 2: Blue-Team Hardening (The Defense)
When user requests defense or revision based on round 1 findings:

1. Close all identified attack angles by inserting defensive qualifications, references, or tighter bounds.
2. Eliminate subjective emotion and administrative fluff. Maintain a cold, rigorous, objective tone.
3. Keep word count around 85% to 95% of original length. Prohibit broad summarization. For long documents, refine section by section.

## Gotchas

- Do not compress long text into high-level bullet summaries unless explicitly requested.
- Always check that quotes match the user's attachment before raising objections.
