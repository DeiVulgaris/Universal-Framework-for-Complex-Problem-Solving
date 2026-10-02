# Invariant Replay Frontier Bridge v1

## Purpose

This bridge consumes the impact-localized frontier produced by Semantic Core
Stage 61 and reopens the corresponding UFCPS UQL question at the identified
reasoning step.

It does not replace the full reasoning history.

## Canonical path

information result
  -> classification
  -> invariant-rooted replay
  -> impact localization
  -> localized frontier
  -> UQL frontier update
  -> Task Discovery / next operation

## Update semantics

The adapter:

- preserves the root invariant identifier;
- records the replay trace;
- sets the current procedural unit to the affected step;
- preserves the existing unresolved difference unless a validated replacement
  is explicitly supplied;
- records downstream steps as requiring replay;
- appends an audit event.

It does not:

- delete historical events;
- mark a contradiction as proof that the invariant is false;
- assign an agent;
- claim a task;
- terminate the question.

## Explicit impact

The preferred input contains an explicit affected-step identifier produced by
semantic validation.

A missing or unknown anchor is rejected upstream by the Semantic Core
localizer.

The full localized frontier remains available as metadata so that downstream
processes can resume from the anchor without losing the root-to-anchor prefix.

## Status

v1 — experimental integration layer.
