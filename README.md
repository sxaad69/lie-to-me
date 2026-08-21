# LIE TO ME — greybox feeler

Testimony-deduction interrogation prototype. One seeded case, three suspects,
nine claims, four evidence records. Stamp every claim TRUE/FALSE/UNPROVEN
against the records, then lock your accusation — a correct lock prints the full
contradiction chain; a wrong one names the innocent you convicted.

The generator is a prover: every seed ships with machine-checked proofs of
unique-culprit and no-innocent-convicts (printed to the browser console).
A case without proofs does not ship.

**Status:** M1 feeler (throwaway greybox, pinned-rule-12 gate artifact — never
promoted). Playable: https://sxaad69.github.io/lie-to-me/

## Verify locally

```
node harness.js   # 2000-seed proof stress test + chain integrity
python3 -m http.server 8741  # then open http://localhost:8741
```

Known limitations: single case shape, no art/audio/tutorial by design.
Full-build spec (Godot 4.5, 4-5d) fires only after a human pulse KEEP verdict.
