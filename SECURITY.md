# Enterprise Security & Data Privacy Policy

## 🔒 Executive Summary
**AI Data Analyst** is built with a **Zero Data Retention / Local Execution First** architecture. The application is engineered to allow organizations to analyze proprietary and confidential datasets (e.g., CSV, tabular records) without exposing raw corporate records to public LLM datasets or persistent cloud storage.

---

## 🏛️ Privacy & Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│             CUSTOMER ENVIRONMENT / LOCAL RAM                │
│                                                             │
│  [ Uploaded CSVs ] ──► [ In-Memory SQLite (:memory:) ]      │
│                                │                            │
│                 ┌──────────────┴──────────────┐             │
│                 ▼                             ▼             │
│       [ SQL Sandboxing Guard ]       [ Auto PII Redactor ]  │
│                 │                             │             │
│                 ▼                             ▼             │
│       [ Read-Only Execution ]        [ Masked Sample Rows ] │
└─────────────────┬─────────────────────────────┬─────────────┘
                  │                             │
                  ▼                             ▼
       [ 100% Local Results ]         [ Metadata Only ]
       [ Local Plotly Studio ]                  │
       [ Local PPTX Export   ]                  ▼
                                     ┌─────────────────────────┐
                                     │  GOOGLE GEMINI / VERTEX │
                                     │  (Zero-Shot SQL Gen)    │
                                     └─────────────────────────┘
```

---

## 🛡️ Core Security Safeguards

### 1. In-Memory Ephemeral Storage
- All uploaded datasets are stored **strictly in RAM (`:memory:`)** using SQLite.
- Datasets are **never written to disk**, temp files, or persistent databases.
- When the session ends or datasets are cleared, active memory is purged via Python `gc.collect()`.

### 2. Automated PII Detection & Sensitive Data Masking
- The application automatically scans column names and sample values for PII patterns (Emails, Phone Numbers, Social Security Numbers, Credit Cards, Secrets/API Keys, Compensation).
- Any sample rows sent as grounding context to the LLM are **automatically masked and redacted** (e.g., `a***@domain.com`, `***-***-1234`, `[REDACTED_SECRET]`).
- Full mathematical aggregations (e.g., `SUM`, `AVG`, `COUNT`) are computed locally.

### 3. Read-Only SQL Sandboxing
- All generated SQL queries pass through an automated **Query Sandbox Validator**.
- Only read-only `SELECT`, `WITH ... SELECT` (CTEs), and `EXPLAIN` queries can be executed.
- Destructive and modifying commands (`DROP`, `DELETE`, `INSERT`, `UPDATE`, `ALTER`, `ATTACH`, `PRAGMA`, `TRUNCATE`, `EXEC`) are blocked before execution.

### 4. Telemetry-Free Deployment
- Streamlit external telemetry and usage tracking are disabled by default (`gatherUsageStats = false`).
- Cross-Site Request Forgery (`XSRF`) protection and CORS restrictions are enforced in `.streamlit/config.toml`.

---

## 🏢 Enterprise Compliance & Deployment Options

| Deployment Mode | LLM Provider | Data Residency & Privacy |
| :--- | :--- | :--- |
| **Standard Cloud** | Google Gemini API | Schema metadata transmitted; raw dataset stays local in RAM. |
| **Enterprise Cloud** | Google Cloud Vertex AI | SOC-2, ISO 27001, HIPAA compliant. Google does not log or train on customer prompts. |
| **Air-Gapped / On-Prem** | Local Ollama / vLLM (Llama 3, DeepSeek) | 100% of data, metadata, and LLM inferences remain inside the internal corporate network. |

---

## 🐛 Vulnerability Reporting
If you discover a security vulnerability within this project, please open a private security advisory or contact the maintainers. We are committed to resolving critical security issues promptly.
