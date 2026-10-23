# Repository Guidelines

## Purpose

Sandboxer is a generic Docker Compose environment for local web development.

It is intended as a reusable base for developing applications locally. Production deployments use separate, project-specific containers.

Keep Sandboxer generic, small, simple, reproducible, and easy to extend.

Do not turn it into a production deployment environment.

## Priorities

Prioritize:

1. correctness
2. small and minimal images
3. simple architecture
4. maintainability
5. reproducibility
6. sensible local security
7. developer usability
8. flexibility
9. debugging convenience

Avoid unnecessary abstractions, dependencies, services, and tooling.

## Alpine-first images

Prefer official or well-maintained Alpine-based images by default.

If Alpine is unsuitable, explain why before recommending another base image.

When evaluating software, consider:

* musl vs glibc compatibility
* Alpine package availability
* precompiled binaries
* native dependencies
* GNU-specific assumptions
* Bash-specific assumptions

Prefer minimal runtime images.

Remove build-only dependencies, package caches, temporary files, compilers, headers, and other unnecessary tooling from finished images.

Use temporary build dependencies or multi-stage builds when they provide a meaningful benefit.

Do not sacrifice simplicity for trivial image-size reductions.

## Debugging

Debugging convenience is secondary to keeping the normal images small.

Do not permanently install debugging or profiling tools unless they provide recurring value.

When additional debugging software is required, explain:

* what is required
* whether it works with Alpine
* whether musl or glibc compatibility is relevant
* whether it should be temporary, optional, or permanent

Prefer temporary packages, Compose overrides, profiles, separate debug images, or alternative build targets over bloating the normal image.

Do not switch away from Alpine merely because debugging would be easier.

## Architecture

Keep the environment generic rather than tied to Laravel, Symfony, WordPress, or another framework.

Prefer straightforward Dockerfiles and Docker Compose configuration over additional infrastructure.

Avoid kitchen-sink containers.

Keep optional or project-specific functionality isolated where practical through:

* separate services
* Compose profiles
* overrides
* alternative build targets
* documented extensions

Do not introduce Kubernetes, production orchestration, or deployment infrastructure unless explicitly requested.

## Project structure

`docker-compose.yml` defines the development environment.

Root-level `*.dockerfile` files build local images.

Configuration lives primarily under `config/`.

Application code and assets live under the ignored `www/` directory.

Local database data, import/export data, and logs live under directories such as:

* `dbdata/`
* `iedata/`
* `log/`

Do not commit generated data or logs.

## Scope and context efficiency

Inspect only files relevant to the current task.

Do not perform repository-wide scans, recursive directory listings, or broad searches unless explicitly requested.

Do not inspect, search, enumerate, summarize, or modify `www/`, `dbdata/`, `iedata/`, or `log/` unless the current task explicitly requires one of those directories.

Treat these directories as out of scope by default.

Content under `www/` belongs to applications developed with Sandboxer rather than to Sandboxer itself.

The remaining excluded directories primarily contain local runtime data.

When a task requires something under one of these directories, inspect only the specific subdirectory or files necessary for that task.

Prefer targeted file reads and searches over broad repository exploration.

Do not read documentation, configuration, or source files merely to gather general context. Read them when they are relevant to the current task.

## Branch workflow

Use `develop` for future Sandboxer code changes and commits. Do not create
feature branches for routine work unless requested.

Before editing, check the current branch, working tree, and whether `develop`
contains the latest main changes. Preserve existing work when switching branches;
never discard it or force-push to resolve a mismatch.

Push Sandboxer changes only to `origin develop` unless the user explicitly
requests another target. Main is normally updated through a pull request.
Explicit permission for one main-branch commit or push is a one-time exception,
not permission to use main for later work. Commit, push, merge, and release only
when requested.

These rules apply to Sandboxer's repository. Applications under `www/` have
their own repositories and branch instructions (Profundarium uses `development`).

## Working rules

Before changing behavior, inspect only the files and configuration relevant to the change.

Depending on the task, this may include:

* Compose configuration
* Dockerfiles
* configuration files
* setup scripts
* volumes
* networking
* README

Understand existing behavior before replacing it.

Prefer incremental changes over broad rewrites.

Distinguish between:

* bugs
* security issues
* outdated dependencies
* portability problems
* Alpine compatibility problems
* unnecessary image size
* maintainability problems
* developer-experience improvements
* stylistic preferences

Do not present stylistic preferences as technical requirements.

Before substantial architectural changes, explain:

1. the problem
2. the proposed solution
3. important tradeoffs
4. Alpine compatibility
5. relevant image-size impact

Challenge assumptions when there is a concrete technical reason.

## Dependencies

Evaluate important dependencies based on:

* upstream support
* security support
* compatibility
* Alpine support
* image size
* maintenance cost

Do not upgrade something merely because a newer version exists.

Use current authoritative documentation when support status or compatibility may have changed.

## Security

Sandboxer is development-only, but avoid unnecessary risks to the host.

Pay particular attention to:

* privileged containers
* unnecessary Linux capabilities
* Docker socket access
* dangerous volume mounts
* unnecessary host port exposure
* services exposed beyond localhost without reason
* committed real secrets

Simple development credentials are acceptable when clearly development-only.

## Validation

Use appropriate validation after changes.

Common checks include:

* `docker compose config`
* `docker compose build`
* `docker compose up`
* `docker compose ps -a`
* relevant `docker compose logs` commands
* service connectivity checks
* image-size comparisons when relevant

Run only the validation relevant to the change unless broader validation is explicitly requested or technically necessary.

Avoid destructive Docker cleanup commands.

Never delete unrelated containers, images, volumes, or user data.

## Documentation

Keep `README.md` consistent with actual behavior.

Update documentation when commands, URLs, prerequisites, configuration, dependencies, or user-visible behavior change.

Document important Alpine limitations and optional debugging requirements.

Avoid unnecessary Docker tutorials.

## Guiding principle

Sandboxer is a lightweight generic workshop for building web applications.

Keep the normal environment small and simple.

Add specialized tooling only when it is actually needed.
