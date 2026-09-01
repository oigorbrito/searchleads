# PROJECT_CHARTER

Status: CANONICAL
Authority: highest project-level narrative for SearchLeads until superseded by a newer canonical charter.

## Problem

SearchLeads needs a repeatable system for discovering, normalizing, validating, and qualifying B2B leads from evidence-backed sources without turning every session into a rediscovery exercise.

## Purpose

Provide a governed engineering baseline for the product, so requirements, architecture, implementation, tests, evidence, and release gates remain traceable and stable.

## Audience

- engineers
- reviewers
- maintainers
- operators
- future automation agents

## Value Proposition

- deterministic lead discovery and qualification
- explicit evidence retention and replay
- conservative entity resolution and review routing
- measurable quality and operational gates
- documentation that governs work instead of trailing it

## Scope

- company and person discovery
- contact discovery and validation
- evidence and provenance handling
- persistence and replay
- qualification and lead wrapping
- controlled acquisition/runtime integration
- documented architecture and verification gates

## Non-Scope

- generic web crawling at arbitrary scale
- uncontrolled fuzzy merges
- silent truth discovery from incomplete evidence
- campaign execution authorization
- legal certification
- external compliance claims without evidence

## Current Stage

STAGE 1 - ENGINEERING BASELINE is not yet fully established.

The repository has substantial implementation and experimental evidence, but canonical documentation, ER decisions, and traceability are still being consolidated.

## Technical Objectives

- stabilize canonical domain and data models
- close Company ER and Person ER with evidence-backed decisions
- preserve raw evidence and deterministic replay
- keep runtime, application chassis, and persistence boundaries explicit
- align implementation, tests, and docs under stable IDs

## Commercial Objectives

- support qualified lead generation for approved ICPs
- keep qualification separate from send readiness
- preserve compliance boundaries for contacts and campaigns
- make operational readiness measurable

## Constraints

- avoid inventing benchmark winners before benchmark execution
- preserve historical experimental docs
- do not claim ISO conformance without formal assessment
- keep secrets out of documentation
- do not mutate `main`

## Success Definition

SearchLeads is successful when a reader can answer from the repository alone:

- what the system does
- what it does not do
- which architecture is current
- which requirements are active
- which decisions are closed
- which capability is next
- which blocker is technical, operational, or external

