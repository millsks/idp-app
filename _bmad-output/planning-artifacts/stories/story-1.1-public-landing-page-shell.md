# Story 1.1: Public Landing Page Shell

Status: ready-for-dev

## Story

As a public visitor,
I want to see a clear, well-designed landing page that explains what idp-app is and what it offers,
so that I can understand the value proposition and decide whether to sign up.

## Acceptance Criteria

1. The landing page is accessible at `/` without any authentication requirement.
2. The page displays a headline and supporting copy describing the portal's purpose.
3. The page displays visual cards for each planned capability pillar: Skills & Prompts Library, Software Marketplace, Developer Utilities, Application Accelerators, Vulnerability Library.
4. Pillar cards for features not live in MVP1 are visually marked as "Coming Soon".
5. A prominent "Sign In" call-to-action button is present and links to `/login`.
6. A link to the project's GitHub repository is present (open-source disclosure).
7. Unauthenticated users are NOT prompted to log in or shown an auth modal unprompted.
8. When the user is already authenticated, the "Sign In" CTA is replaced with navigation to the library or profile.
9. The page passes WCAG 2.1 AA contrast requirements.
10. All interactive elements are keyboard-navigable.
11. The page renders correctly in the latest two versions of Chrome, Firefox, Safari, and Edge.

## Tasks / Subtasks

- [ ] Update `frontend/src/pages/HomePage.tsx` with new landing page content (AC: 1, 2, 3, 4)
  - [ ] Replace placeholder content with headline, sub-headline, and capability pillar cards
  - [ ] Implement "Coming Soon" badge/overlay for non-MVP1 pillars (Marketplace, Utilities, Accelerators, Vulnerability Library)
  - [ ] Mark "Skills & Prompts Library" pillar card as active/live
- [ ] Add Sign In CTA and GitHub repo link (AC: 5, 6)
  - [ ] CTA button links to `/login`
  - [ ] GitHub link opens `https://github.com/millsks/idp-app` in a new tab
- [ ] Implement auth-conditional CTA rendering (AC: 8)
  - [ ] When `isAuthenticated` from `useAuth()` is true, replace Sign In CTA with library/profile navigation
- [ ] Accessibility audit (AC: 9, 10)
  - [ ] Verify AA contrast ratios for all text/background combinations using MUI theme colours
  - [ ] Test full keyboard navigation flow (Tab order, focus rings visible)
- [ ] Update `frontend/src/App.tsx` to ensure `/` route renders `HomePage` (verify existing — no auth guard on this route)
- [ ] Write/update `frontend/src/App.test.tsx` or co-located test for HomePage render

## Dev Notes

- `HomePage.tsx` already exists as a placeholder — modify in place, do NOT create a new file.
- Use MUI v6 `Grid`, `Card`, `CardContent`, `Typography`, `Button`, `Chip` components. Extend theme in `src/theme/index.ts` only if new tokens are needed.
- The `useAuth()` hook does not exist yet (it is created in Epic 2 Story 2.3). For this story, read `isAuthenticated` directly from a temporary context stub OR conditionally render based on whether `AuthContext` is available. **Do not block this story on Epic 2 delivery** — the conditional CTA can be wired up as a follow-on task in Story 2.3 if AuthContext is not yet available.
- The public preview strip (FR-1.6) is a separate story (Story 1.2) and must NOT be implemented here.
- No backend changes required for this story.

### Project Structure Notes

- Modify: `frontend/src/pages/HomePage.tsx`
- Verify: `frontend/src/App.tsx` — ensure `/` route is public (no `<ProtectedRoute>` wrapper)
- Modify if needed: `frontend/src/theme/index.ts` — add any new palette tokens
- Add test: `frontend/src/pages/HomePage.test.tsx`

### References

- PRD FR-1.1 – FR-1.5 [Source: _bmad-output/planning-artifacts/prds/prd-idp-app-2026-05-24/prd.md#Feature-1]
- PRD NFR-4.3.1, NFR-4.3.2 [Source: _bmad-output/planning-artifacts/prds/prd-idp-app-2026-05-24/prd.md#43-accessibility]
- Architecture Section 4: Project Structure [Source: _bmad-output/planning-artifacts/architecture.md#4-project-structure]
- Copilot Instructions — Frontend Conventions [Source: .github/copilot-instructions.md]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
