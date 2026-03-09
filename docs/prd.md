# Insurance Co-Pilot PRD (Prototype Scope)

## Vision
Insurance Co-Pilot helps roadside assistance teams resolve claims faster and more consistently by combining AI-supported intake, policy checks, and dispatch recommendations in one guided workflow. The first release augments human agents with transparent recommendations rather than replacing them.

## Goals and Business Impact
- Reduce average handling time for roadside calls by automating data capture and first-pass decisions.
- Improve decision consistency by applying explicit policy rules in a repeatable way.
- Increase customer confidence through immediate, clear status updates.
- Provide an observer console so supervisors can audit AI decisions and intervene quickly.

## Key Features
1. Voice-first claim intake with browser microphone and text fallback.
2. Rule-based extraction of structured claim details from transcript text.
3. Automated policy coverage validation against synthetic policy fixtures.
4. Next-best-action recommendation: tow truck vs repair van, with nearest provider selection.
5. Fake SMS-style customer updates for demo purposes.
6. Observer console showing transcript, extracted entities, coverage rationale, and dispatch output.

## Prioritization Rationale
Prioritized features are those required to demonstrate the end-to-end value chain in the case study within a strict 5-6 hour build window. UI polish, external integrations, and advanced ML features are intentionally deferred in favor of functional completeness and clear decision logic.

## Milestones for a Real Build
1. **MVP (4-6 weeks)**: transcript ingestion, policy matching, decision explainability, manual handoff.
2. **Integration phase (6-10 weeks)**: connect insurer policy systems, dispatch systems, and CRM.
3. **Scale and quality phase (8-12 weeks)**: model quality monitoring, reliability hardening, A/B rollout.
4. **Advanced AI phase**: multimodal damage assessment and real-time call coaching.

## Technical Risks
- Speech recognition quality depends on browser/environment quality.
- Policy interpretation becomes complex when using unstructured legal documents.
- Incorrect automated decisions can create operational and regulatory risk.
- Provider ETA and availability become unreliable without live dispatch integrations.

## AI Integration for Damage Assessment (Future)
Production damage assessment should combine:
- image and video inputs from customers,
- incident text context from transcripts,
- policy constraints and repair history.

Recommended approach:
- multimodal model for visual damage classification,
- confidence thresholds and human-review routing,
- continuous evaluation against labeled outcomes.

This is intentionally out of current prototype scope.

## Deferred Features
- telephony integration and call recordings,
- real SMS and dispatch APIs,
- authentication and role-based access,
- full policy document retrieval + semantic search,
- production monitoring and compliance tooling.
