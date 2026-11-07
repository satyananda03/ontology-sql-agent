<!--
SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES.
All rights reserved.
SPDX-License-Identifier: Apache-2.0
-->

# Container Third-Party Notices

This file covers what the ontology-sql-agent container image adds on top of its
base image. The application's own open-source dependencies (Python packages)
are listed separately in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

The image ships these files under `/licenses/`: `LICENSE`,
`THIRD_PARTY_NOTICES.md`, this file, and `OPEN_SOURCE_NOTICE`.

## Source code

Source code for the open-source components added on top of the base image is
archived by NVIDIA at https://opensource.nvidia.com/oss/teams/nvidia, as stated
in `OPEN_SOURCE_NOTICE`. The upstream Auto-Ontology source this project derives from is at
https://github.com/NVIDIA/auto-ontology.

## Base image

The image is built on the NVIDIA-approved Ubuntu 22.04 base container
(OSRB Bug 3840915), pulled from NVIDIA's registry:

| Image | Base |
| --- | --- |
| `ontology-sql-agent` (backend, ingestion and migrations) | `nvcr.io/nvidia/base/ubuntu:jammy-20250619` |

Source code for the base container is provided by NVIDIA with that image.

## Components added on top of the base image

### `ontology-sql-agent` — `Dockerfile`

| Component | Version | License | Project URL |
| --- | --- | --- | --- |
| CPython (python-build-standalone, installed by uv) | 3.12 | PSF-2.0, plus the licenses of its bundled libraries | https://github.com/astral-sh/python-build-standalone |
| Python packages in `/opt/venv` | per `uv.lock` | see `THIRD_PARTY_NOTICES.md` (Backend) | — |
| `ca-certificates` (Ubuntu package) | jammy | MPL-2.0 (certificate data), GPL-2.0-or-later (scripts) | https://packages.ubuntu.com/jammy/ca-certificates |
| `libpq5` (Ubuntu package) | jammy | PostgreSQL License | https://www.postgresql.org |
| `tini` (Ubuntu package) | jammy | MIT | https://github.com/krallin/tini |

Build-only tools (uv, compilers, `curl`) are used in the builder stage and are
not present in the final image.

## Updating this file

Update this file whenever the Dockerfile changes its base image, its apt
packages, or the runtimes it installs. `THIRD_PARTY_NOTICES.md` tracks
dependency changes.
