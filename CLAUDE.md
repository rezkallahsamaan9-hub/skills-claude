# AgentOS — Projektkontext

## Projekte

### KlickWert — B2B AI Automation Agency
Voice Agents, Chatbots, Workflow Automation für Business-Kunden.
Stack: n8n, GitHub, Supabase (geplant), Vercel.
Regel: Client-Arbeit = Produktionsqualität. Immer testen vor Aktivierung. n8n bevorzugen.

### ErfolgsCode — YouTube Automation
Automatisierter YouTube-Kanal (Buchzusammenfassungen, Educational Content).
Pipeline: Topic → Script → TTS → Visuals → Upload → SEO.
Regel: Volumen + Konsistenz. Alles automatisieren. Human Review nur vor Publish.

## Infrastruktur

### Aktive MCP Server
- **n8n** — Workflows bauen/managen/triggern
- **GitHub** — Repos, Issues, PRs via wrapper script
- **Context7** — Live Library-Docs im Kontext (npx, kein Key nötig)
- **Tavily** — AI-optimierte Websuche: search, extract, crawl, map (Key in Keychain)

### Geplante MCP Server
Supabase, Vercel, Google (YouTube/Sheets/Calendar), Playwright

### Task-Routing

| Task | Tool | Fallback |
|------|------|----------|
| Workflow | n8n MCP | Code wenn n8n nicht reicht |
| Code/Repo | GitHub/gh CLI | — |
| Lookup | Direkter Tool-Call | Haiku Agent |
| Content | Direkt antworten | Sonnet für Langform |
| Multi-Step | Plan → parallel Sonnet | Sequential wenn abhängig |
| Research | Parallel + WebSearch | Single wenn eng |
| Design | frontend-design Skill | Sonnet Agent |
| Docs | pdf/pptx/docx Skills | Write |
| Debug | Read → Edit | Sonnet wenn komplex |

### n8n vs Code
Wiederholbar? → n8n. Nativ möglich? → n8n pur. Sonst → n8n + Code Node. Immer noch nicht? → Custom Code + n8n Webhook.

## Skills (./skills/)

| Kategorie | Skills |
|-----------|--------|
| Dev | claude-api, mcp-builder, skill-creator, webapp-testing |
| Docs | pdf, pptx, docx, xlsx, doc-coauthoring |
| Design | frontend-design, algorithmic-art, canvas-design, theme-factory, web-artifacts-builder |
| SEO | seo, seo-audit, seo-content, seo-technical, seo-local, seo-page, seo-schema |
| Marketing | copywriting, email-sequence, cold-email, lead-magnets, page-cro, content-strategy, pricing-strategy, sales-enablement, marketing-seo-audit |
| Context | context-optimization, context-compression, multi-agent-patterns |
| Comms | brand-guidelines, internal-comms, slack-gif-creator |
| OS | dispatch |

## Environment
macOS Darwin 24.5.0 / zsh / Python 3.12 / n8n Cloud / GitHub CLI
