This file is a merged representation of a subset of the codebase, containing specifically included files and files not matching ignore patterns, combined into a single document by Repomix.
The content has been processed where content has been compressed (code blocks are separated by ⋮---- delimiter).

# File Summary

## Purpose
This file contains a packed representation of a subset of the repository's contents that is considered the most important context.
It is designed to be easily consumable by AI systems for analysis, code review,
or other automated processes.

## File Format
The content is organized as follows:
1. This summary section
2. Repository information
3. Directory structure
4. Repository files (if enabled)
5. Multiple file entries, each consisting of:
  a. A header with the file path (## File: path/to/file)
  b. The full contents of the file in a code block

## Usage Guidelines
- This file should be treated as read-only. Any changes should be made to the
  original repository files, not this packed version.
- When processing this file, use the file path to distinguish
  between different files in the repository.
- Be aware that this file may contain sensitive information. Handle it with
  the same level of security as you would the original repository.

## Notes
- Some files may have been excluded based on .gitignore rules and Repomix's configuration
- Binary files are not included in this packed representation. Please refer to the Repository Structure section for a complete list of file paths, including binary files
- Only files matching these patterns are included: **/*.{py,js,mjs,cjs,ts,tsx,jsx,java,kt,kts,gd,groovy,gradle,toml,json,yaml,yml,sql,sh}
- Files matching these patterns are excluded: .ai/**, **/node_modules/**, **/.gradle/**, **/build/**, **/dist/**, **/.venv/**, **/__pycache__/**, **/.pytest_cache/**, **/.git/**, **/coverage/**, **/*.lock, **/*.min.js, **/*.map, assets/**, art/**, art_sources/**, marketing/**, colab/**, kaggle/**, discovery-cache.json, health-snapshot.json, history.json
- Files matching patterns in .gitignore are excluded
- Files matching default ignore patterns are excluded
- Content has been compressed - code blocks are separated by ⋮---- delimiter
- Files are sorted by Git change count (files with more changes are at the bottom)

# Directory Structure
```
cloudflare-paper-scheduler/
  src/
    index.js
  test/
    index.test.js
  package.json
  wrangler.toml
```

# Files

## File: cloudflare-paper-scheduler/src/index.js
```javascript
export async function invokePaperCycle(env, fetchImpl = fetch)
⋮----
// Reject legacy HTTP 200 responses that still report partial failures.
⋮----
scheduled(_event, env, ctx)
```

## File: cloudflare-paper-scheduler/test/index.test.js
```javascript
return
⋮----
text: async ()
⋮----
json: async () => (
⋮----
json: async () =>
⋮----
globalThis.fetch = async (url, options) =>
⋮----
waitUntil(promise)
```

## File: cloudflare-paper-scheduler/package.json
```json
{
  "name": "ai-trading-paper-scheduler",
  "private": true,
  "type": "module",
  "scripts": {
    "test": "node --test test/index.test.js"
  }
}
```

## File: cloudflare-paper-scheduler/wrangler.toml
```toml
name = "ai-trading-paper-scheduler"
main = "src/index.js"
compatibility_date = "2026-09-16"

[triggers]
crons = ["*/15 * * * *"]

[vars]
TARGET_URL = "https://ai-trading-dashboard-qyr2.onrender.com/internal/paper-cycle"
```
