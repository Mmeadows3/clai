## Purpose
Search the internet and local CLI documentation for third-party solutions, libraries, and design patterns that fit the provided query.

## Input
- `search_query` (string): The problem or topic to research.

## Output
A raw research response that helps decide whether to:
- use an existing internal tool,
- solve with installed CLI tools, or
- use external projects, libraries, services, or patterns.

## Instructions
Always research the provided `search_query` by using all of the following tools:
- `cli.w3m` for web discovery and reading internet sources.
- `cli.tldr` for tools by their command usage patterns and examples.
- `cli.man` for seeing if an installed tool fits the solution by searching our installed tooling documentation.

Shorthand convention:
- Treat `~w3m` as a cue to use `cli.w3m`.
- Treat `~tldr` as a cue to use `cli.tldr`.
- Treat `~man` as a cue to use `cli.man`.

During research, determine:
1. Whether an existing tool in this environment likely already fits the job.
2. Whether one or more installed CLI tools can solve the job directly.
3. Whether third-party solutions from the web are strong candidates.
4. Whether common design patterns could be employed for a clean, simple coded solution.

Return a practical, query-specific response with:
- Recommended path that best fits the query.
- Viable alternatives.
- Commands, libraries, projects, or patterns discovered.
- Key tradeoffs, assumptions, and any notable uncertainty.

Scope and depth should match what best fits the provided query.
