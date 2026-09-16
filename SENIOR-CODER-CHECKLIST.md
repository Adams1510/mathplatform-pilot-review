# Senior-coder review checklist

This proposed checklist is a technical review aid. It is not independently QA-approved and does not replace security, accessibility, content, privacy, operational, or student-pilot authorization.

## Correctness

- [ ] Run migrations and exercise the home, topic, health, readiness, and synthetic-state routes.
- [ ] Confirm unavailable activity links do not render education content or collect answers.
- [ ] Trace synthetic session creation, expiry, purge, save, replay, revision conflict, and lock behaviour.
- [ ] Review transaction boundaries and identify SQLite-versus-PostgreSQL behaviour that needs later proof.
- [ ] Confirm database failures do not disclose implementation details through readiness responses.

## Security boundaries

- [ ] Review settings defaults, `DEBUG`, host handling, secret handling, CSRF, session cookies, and middleware headers.
- [ ] Confirm no route, import, manifest, test, or static asset references a private Q02 object or locator.
- [ ] Check that synthetic routes are controlled by settings and production settings disable technical fixtures.
- [ ] Review direct-route behaviour, error handling, cache policy, and data written to logs or SQLite.
- [ ] Identify missing deployment, authentication, authorization, rate-limit, dependency-review, secret-management, and database-hardening work.

## Maintainability

- [ ] Review settings separation and package-only review profile.
- [ ] Assess model constraints, migration quality, service boundaries, naming, errors, and test coverage.
- [ ] Check whether synthetic-only assumptions are mechanically enforced enough for later engineering work.
- [ ] Identify dead code, duplicated conditions, weak extension points, and documentation drift.

## Accessibility implementation

- [ ] Inspect semantic structure, landmarks, skip link, native controls, labels, focus order, error/status announcements, visible focus, responsive layout, forced-colours rules, and reduced-motion handling.
- [ ] Exercise keyboard-only interaction at 200% zoom and narrow viewport.
- [ ] Review the browser-test setup and flag untested assistive-technology combinations.
- [ ] Record observed implementation issues without treating this review as independent accessible-output verification.

## Pilot blockers

- [ ] Identify any defect that could expose private/controlled material, collect participant data, or let synthetic state be misrepresented as learner data.
- [ ] Identify missing content ownership, independent QA, accessible-audio evidence, privacy/records decisions, reviewer operations, recovery evidence, deployment, and student-safety controls.
- [ ] Mark whether each finding blocks a student pilot using the findings template.
