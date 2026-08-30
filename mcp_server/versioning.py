"""Schema-versioning convention for MCP tool/resource contracts.

Nothing in M1 or M2 needs this yet — every M1 tool contract stays exactly as
it was, and M2 only adds new tools/resources/prompts, it doesn't change
existing ones. This file exists so the convention gets decided deliberately,
before M3 starts hardening (and likely reshaping) the existing tool
contracts, instead of improvised under pressure once something's already
broken for a caller.

DECIDED: identity-level versioning.

A breaking change to a tool or resource contract gets a new name/URI rather
than changing the existing one in place — e.g. `get_title_details_v2`,
`tmdb://v2/title/{id}` — and the old one keeps running, deprecated, until
callers migrate off it and it's removed.

Why, over the field-level alternative (a `schema_version: int` field bumped
in place on the same tool):

The deciding question is not "internal vs. third-party," it's *who controls
the upgrade timing* — equivalently, how many independently-deployed things
read this contract. Field-level only works cleanly when you control every
caller and can redeploy them in lockstep with the server (bump the field,
update the one reader, ship both together — nobody's left behind because
there's no independent party to leave behind). The moment a caller is
deployed independently — a third-party integrator, or even an internal team
on its own release cadence — you lose the ability to force their upgrade
timing, and a field-level bump just breaks them silently on your schedule,
not theirs. Identity-level trades code duplication (old and new versions
both sitting in the codebase for a while) for letting every caller, internal
or external, upgrade at its own pace instead of yours. Given this project's
roadmap adds real external callers in M6 (multi-tenant "MCP as a product"),
that flexibility is worth having from the first breaking change rather than
retrofitted under pressure later.

How to apply it, starting with M3's first breaking change:

1. Add the new tool/resource under a versioned name (`_v2` suffix for tools,
   a `/v2/` URI segment for resources) rather than editing the existing one.
2. Keep the old one running unchanged — same behavior, same contract — and
   mark it deprecated in its docstring/description (state what replaced it).
3. Log what changed and why in this file, in a running list below, so the
   history of breaking changes stays in one place instead of scattered
   across commit messages.
4. Remove the deprecated version only once nothing calls it anymore
   (checked via the M8 infra/observability tracing, once that exists — until
   then, a manual check of what the M5 agent / M6 tenants actually call).

Version history (append here as breaking changes happen — empty for now):
"""
