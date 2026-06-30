# Timeline Guide

## What
Chronological event stream from extracted records.

## Events
- doctor visit / date mentions
- lab tests
- medication started/stopped/mentioned
- diagnosis mentions
- procedures/imaging (when detected)

## How
- Parse event anchors during entity extraction
- Persist normalized events in `timeline_events`
- Query with document/date/type filters

## Design Decision
Timeline stored as first-class table, not generated ad-hoc per request.

## Best Practices
- Keep original source span/page in metadata.
- Sort by date with stable tie-breakers.
- Surface unknown-date events explicitly.
