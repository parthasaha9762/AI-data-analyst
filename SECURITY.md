# Security, Data Privacy & Secret Protection Policy

## 🔒 Executive Summary
**AI Data Analyst** is built with a **Privacy-Focused, In-Memory Execution Architecture**. Raw uploaded files are processed in memory and are not persisted by the application. Data samples sent for LLM grounding are masked to reduce sensitive-data exposure, while private API keys and credentials are guarded via multi-source resolution and version-control exclusion rules.

---

## 🏛️ Privacy & Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 APPLICATION RUNTIME IN-MEMORY RAM           │
│                                                             │
│  [ Uploaded CSVs ] ──► [ In-Memory SQLite (:memory:) ]      │
│                                │                            │
│                 ┌──────────────┴──────────────┐             │
│                 ▼                             ▼             │
│       [ SQL Sandboxing Guard ]       [ Auto PII Redactor ]  │
│                 │                             │             │
│                 ▼                             ▼             │
│       [ Read-Only Execution ]        [ Masked Sample Rows ] │
│                                                             │
│  [ API Key Resolver ] ──► [.env / Streamlit Secrets]        │
└─────────────────┬─────────────────────────────┬─────────────┘
                  │                             │
                  ▼                             ▼
       [ 100% Local Results ]         [ Metadata Only ]
       [ Local Plotly Studio ]                  │
       [ Local PPTX Export   ]                  ▼
                                     ┌─────────────────────────┐
                                     │  GOOGLE GEMINI / VERTEX │
                                     │  (NL-to-SQL Inference)  │
                                     └─────────────────────────┘
```

---

## 🛡️ Core Security Safeguards

### 1. In-Memory Ephemeral Storage
- Raw uploaded files are processed in memory and are not persisted by the application.
- All uploaded datasets are stored **strictly in RAM (`:memory:`)** using SQLite.
- Datasets are **never written to disk**, temp files, or persistent databases.
- When the session ends or datasets are cleared, active memory is purged via Python `gc.collect()`.

### 2. Automated PII Detection & Sensitive Data Masking
- The application automatically scans column names and sample values for PII patterns (Emails, Phone Numbers, Social Security Numbers, Credit Cards, Secrets/API Keys, Compensation).
- Any sample rows sent as grounding context to the LLM are **automatically masked and redacted** (e.g., `a***@domain.com`, `***-***-1234`, `[REDACTED_SECRET]`).
- Full mathematical aggregations (e.g., `SUM`, `AVG`, `COUNT`) are computed locally in SQLite.

### 3. Read-Only SQL Sandboxing
- All generated SQL queries pass through an automated **Query Sandbox Validator**.
- Only read-only `SELECT`, `WITH ... SELECT` (CTEs), and `EXPLAIN` queries can be executed.
- Destructive and modifying commands (`DROP`, `DELETE`, `INSERT`, `UPDATE`, `ALTER`, `ATTACH`, `PRAGMA`, `TRUNCATE`, `EXEC`) are blocked before execution.

### 4. API Key Protection & Secret Isolation
- **Multi-Source Resolution**: API keys are retrieved from Streamlit Secrets (`st.secrets`), environment files (`.env` via `python-dotenv`), or system environment variables.
- **No Hardcoded Credentials**: No private tokens or secret keys are hardcoded into codebase source files.
- **Version Control Exclusions**: Strict `.gitignore` rules prevent `.env`, `.streamlit/secrets.toml`, database files (`*.db`), and uploaded datasets from being committed.
- **Template Safety**: Only sanitized template files (`.env.example`, `.streamlit/secrets.toml.example`) are checked into Git.

### 5. Telemetry-Free Deployment
- Streamlit external telemetry and usage tracking are disabled (`gatherUsageStats = false`).
- Cross-Site Request Forgery (`XSRF`) protection and CORS restrictions are enforced in `.streamlit/config.toml`.

---

## 🏢 Compliance & Deployment Modes

| Deployment Mode | LLM Provider | Data Handling & Privacy |
| :--- | :--- | :--- |
| **Standard Cloud / Live Demo** | Google Gemini API | Schema metadata transmitted; raw dataset stays in memory in RAM. Masked sample rows for grounding. |
| **Enterprise Cloud** | Google Cloud Vertex AI | SOC-2, ISO 27001, HIPAA compliant backend options. |
| **Air-Gapped / On-Prem** | Local Ollama / vLLM (Llama 3, DeepSeek) | 100% of data, metadata, and LLM inferences remain inside the internal network. |

---

## 🐛 Vulnerability Reporting
If you discover a security vulnerability within this project, please open a private security advisory or contact the maintainers.
