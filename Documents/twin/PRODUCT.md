# Product

## Register

product

## Users

Bachelor thesis committee and academic examiners at Universiteti Polis. Primary context: seated in a formal defense room, evaluating the candidate's understanding of the ME-DT framework. Secondary audience: supervisors and faculty reviewers previewing the deck beforehand. They are technically literate (computer science / engineering faculty) but not necessarily specialists in digital twin systems or LLM-based threat detection. They need to follow the argument without getting lost in implementation detail.

## Product Purpose

A self-navigating slide presentation that demonstrates the ME-DT (Mythos-Enhanced Digital Twin) framework to a thesis committee. Success means the examiners leave the room understanding: (1) why existing detectors fail against low-and-slow cross-domain attacks, (2) how the five-layer architecture addresses that gap, and (3) that the empirical results validate the thesis claim. The presentation is the interface through which a technical argument is made and examined.

## Brand Personality

Measured authority. Precise, rigorous, unhurried. The voice of a researcher who has done the work and does not need to oversell it. Three words: credible, clear, composed.

## Anti-references

- Generic PowerPoint or Google Slides defaults: bullet-point grids, clip-art icons, uniform slide templates with no typographic hierarchy.
- Anything that looks like a marketing pitch deck or startup fundraise — urgency clichés, metric callout boxes, confetti animations.
- Heavy dark-mode hacker aesthetic: Matrix-green-on-black, neon glows, excessive terminal chrome used decoratively rather than to clarify content.

## Design Principles

1. **The argument is the interface.** Every layout decision should make the logical structure of the thesis more legible, not decorate around it. If a visual element does not advance comprehension, remove it.
2. **Rigor reads.** Dense technical content is not a problem to be hidden — it is the signal of real work. Design should surface complexity with clarity, not flatten it into slogans.
3. **Restraint over spectacle.** Transitions, animations, and SVG diagrams earn their place only when they explain something static text cannot. Motion that exists purely to impress the room is a distraction.
4. **Every slide has one job.** A single primary claim per slide. Supporting material is subordinate. If the slide's headline can be removed without changing what the viewer learns, the headline is wrong.
5. **Academic confidence, not corporate polish.** The audience trusts evidence and precision more than brand flair. Aim for the credibility of a well-typeset IEEE paper, not the glossiness of a product launch.

## Accessibility & Inclusion

WCAG AA minimum. The defense room may project onto a screen at varying distances — contrast ratios and text sizes must hold at a distance. Reduced-motion support already present in the codebase; maintain it. Language is Albanian (sq); ensure all labels, ARIA attributes, and any added copy stay in Albanian.
