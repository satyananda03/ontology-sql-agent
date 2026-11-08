<!--
SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES.
All rights reserved.
SPDX-License-Identifier: Apache-2.0
-->

# Third-Party Notices

Auto-Ontology — Copyright (c) 2024-2026, NVIDIA CORPORATION & AFFILIATES.

This product includes the third-party open-source software listed below.
The complete text of each license referenced here is reproduced in the
`licenses/` folder of the corresponding upstream project, or is available
at the URL provided. Inclusion of an OSS component on this list does not
imply that the component is statically or dynamically linked into every
build artifact — see `pyproject.toml` and the
`Dockerfile` for actual dependency graphs.

---

## Backend (Python — `pyproject.toml`)

| Component | Version | License | Project URL |
| --- | --- | --- | --- |
| Alembic | >=1.19.1 | MIT | https://github.com/sqlalchemy/alembic |
| apache-ossie-nvidia-auto-ontology | git (`converters/nvidia`) | Apache-2.0 | https://github.com/apache/ossie |
| FastAPI | >=0.141.1 | MIT | https://github.com/fastapi/fastapi |
| HTTPX | >=0.28.1 | BSD-3-Clause | https://github.com/encode/httpx |
| hvac | >=2.4.0 | Apache-2.0 | https://github.com/hvac/hvac |
| langchain-core | >=1.6.1 | MIT | https://github.com/langchain-ai/langchain |
| langchain-nvidia-ai-endpoints | >=1.4.3 | MIT | https://github.com/langchain-ai/langchain-nvidia |
| langchain-openai | >=1.3.0,<1.3.5 | MIT | https://github.com/langchain-ai/langchain |
| langchain-postgres | >=0.0.17 | MIT | https://github.com/langchain-ai/langchain-postgres |
| LangGraph | >=1.2.11 | MIT | https://github.com/langchain-ai/langgraph |
| NumPy | >=2.5.2 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | https://github.com/numpy/numpy |
| openai | ==2.44.0 | Apache-2.0 | https://github.com/openai/openai-python |
| pandas | >=2.3.3,<3 | BSD-3-Clause | https://github.com/pandas-dev/pandas |
| psycopg (`psycopg[binary]`) | >=3.3.4 | LGPL-3.0-only — see note below | https://github.com/psycopg/psycopg |
| psycopg-pool | >=3.3.1 | LGPL-3.0-only | https://github.com/psycopg/psycopg |
| Pydantic | >=2.13.5 | MIT | https://github.com/pydantic/pydantic |
| python-dotenv | >=1.2.3 | BSD-3-Clause | https://github.com/theskumar/python-dotenv |
| python-multipart | >=0.0.32 | Apache-2.0 | https://github.com/Kludex/python-multipart |
| PyYAML | >=6.0.3 | MIT | https://github.com/yaml/pyyaml |
| Requests | >=2.34.2 | Apache-2.0 | https://github.com/psf/requests |
| SQLAlchemy | >=2.0.52 | MIT | https://github.com/sqlalchemy/sqlalchemy |
| SQLGlot | >=30.17.0 | MIT | https://github.com/tobymao/sqlglot |
| tqdm | >=4.70.0 | MPL-2.0 AND MIT | https://github.com/tqdm/tqdm |
| Uvicorn (`uvicorn[standard]`) | >=0.52.4 | BSD-3-Clause | https://github.com/Kludex/uvicorn |

The `binary` extra installs the `psycopg-binary` wheel, which bundles
prebuilt native libraries rather than linking the system ones. Those carry
their own licenses and are redistributed inside any image built from this
repo: libpq (PostgreSQL License), OpenSSL 3 (Apache-2.0), MIT Kerberos
(MIT-style), and OpenLDAP (OpenLDAP Public License). Building against a
system libpq instead — `psycopg[c]` or plain `psycopg` — avoids bundling
them.

The `pyarrow` extra of `databricks-sql-connector` installs Apache Arrow's
`pyarrow` (Apache-2.0), whose wheel bundles the Arrow C++ libraries and
their own notices.

`mysql-connector-python` is licensed under GPL-2.0 with Oracle's Universal
FOSS Exception, which lets it be combined with software under OSI-approved
licenses such as Apache-2.0. It is used unmodified.

`kumo-relational-client[relational]` resolves to NVIDIA wheels vendored under
`vendor/wheels/`: `kumo-relational-client` 1.0.0, `kumo-connectors` 1.0.0 and
`kumo-relational-engine` 1.0.0, all Apache-2.0. `kumo-relational-engine`
bundles Mermaid (MIT); its license text ships in the wheel as
`kumo_relational_engine/rfm/assets/MERMAID_LICENSE`.

### Backend development dependencies (not redistributed)

| Component | Version | License | Project URL |
| --- | --- | --- | --- |
| HTTPX | >=0.28.1 | BSD-3-Clause | https://github.com/encode/httpx |
| pytest | >=9.1.1 | MIT | https://github.com/pytest-dev/pytest |
| Ruff | >=0.16.5 | MIT | https://github.com/astral-sh/ruff |

### Sample databases (test fixtures, not redistributed in any build artifact)

Vendored under `dev_tools/fixtures/sql/` and used only to seed local development and
test databases. See `dev_tools/fixtures/sql/README.md` for provenance and for the
modifications made to Pagila.

| Component | Version | License | Project URL |
| --- | --- | --- | --- |
| Pagila | pagila-v3.1.0 (trimmed; see `dev_tools/fixtures/sql/README.md`) | MIT | https://github.com/devrimgunduz/pagila |

Pagila is Copyright (c) Devrim Gündüz, distributed under the MIT licence; the
full licence text accompanies the upstream project at the URL above.

## Review UI (npm — `ui/package.json`)

Runtime dependencies bundled into the UI build. Build-only tools (Vite,
TypeScript, openapi-typescript) are not shipped and are not listed.

| Component | Version | License | Project URL |
| --- | --- | --- | --- |
| React | 18.3.1 | MIT | https://github.com/facebook/react |
| React DOM | 18.3.1 | MIT | https://github.com/facebook/react |
| React Router DOM | 6.28.0 | MIT | https://github.com/remix-run/react-router |

---

## License texts

- **Apache License 2.0** — see [`LICENSE`](./LICENSE) in this repository, or
  https://www.apache.org/licenses/LICENSE-2.0.
- **MIT License** — https://opensource.org/license/mit/
- **BSD 2-Clause "Simplified" License** — https://opensource.org/license/bsd-2-clause/
- **BSD 3-Clause "New" or "Revised" License** — https://opensource.org/license/bsd-3-clause/
- **GNU Lesser General Public License v3.0 only (LGPL-3.0-only)** —
  https://www.gnu.org/licenses/lgpl-3.0.html
- **GNU General Public License v2.0 (GPL-2.0)** —
  https://www.gnu.org/licenses/old-licenses/gpl-2.0.html
- **PostgreSQL License** — https://opensource.org/license/postgresql/
- **OpenLDAP Public License** — https://www.openldap.org/software/release/license.html

The Apache 2.0 license under which Auto-Ontology is distributed is fully compatible
with each of the licenses listed above when those components are used as
unmodified upstream dependencies. If you redistribute any modified copy of
a third-party component, you must preserve and follow the terms of that
component's original license in addition to the terms of `LICENSE`.

---

## Updating this file

The tables above list the **direct** dependencies declared in
`pyproject.toml` and `ui/package.json`, not the full transitive
closure. When adding, removing, or upgrading a direct dependency, update
the corresponding row in the same change. For the resolved closure and its
pinned versions, see `uv.lock` and `ui/package-lock.json`.
