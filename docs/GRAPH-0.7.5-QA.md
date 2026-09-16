# Graph 0.7.5 verification

- 72 Node tests and official Obsidian SDK typecheck passed. New tests cover bilingual matches, generic-word exclusions, direct links, isolated papers, deterministic layout, and 44px target spacing at 230/300/650px.
- Real Windows Vault: 15 papers, 19 discovery relations. Node click opens the matching report in the right pane and retains one dashboard. Narrow dashboard header stays 240px; compact graph body does not overflow.
- Local classification reads only titles, concept names and tags; no model request or upload. Explicit links and inferred topic relationships are distinguished. Missing metadata falls back to title/tags; originals are not rewritten.
- FULL visual review: typography, surfaces, icons, focus, restrained transitions and layout reviewed in native Windows Obsidian. Existing CSS and font settings retained. Right-panel resize and compact card clipping were corrected. Extra animation and another graph library were rejected as unnecessary.
- Real Android/macOS interaction and 10%-speed transition playback are UNVERIFIED. Responsive geometry was tested; this is not a real-device claim. Analyzer scientific contents were not revalidated or changed.

- Added card alignment fix: one shared desktop row grid replaces independent column fractions. Native heights 800/1000/1250px each measured 0px project/minutes top and bottom difference, and graph/papers start difference.
