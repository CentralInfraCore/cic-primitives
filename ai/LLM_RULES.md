# LLM Szabályok / LLM Rules

## Magyar

- Minden állításhoz jelöld meg: **defined** / **draft** / **concept**
- Ha a státuszt nem tudod fájl-szinten alátámasztani, ne mondd ki tényként
- Aggregate-ből indulj, soha nem domain objektumból (Pod, Switch, VM)
- A kompozíció mechanizmusa git — ne javasolj YAML override rules rendszert
- Ne találj ki új fogalmat ha egy meglévő (IaC, YANG szemantika, control loop) fedi
- Kimenet YAML-ban determinisztikus: rendezett kulcsok, schema-first
- Ha egy primitive-re nem tudod megmondani a YAML, API és runtime mappinget → nem lezárt
- MCP kérdéseknél: graph-first, ne snippet-first

---

## English

- Tag every claim as: **defined** / **draft** / **concept**
- If you cannot back up the status at the file level, do not state it as fact
- Start from the aggregate, never from a domain object (Pod, Switch, VM)
- The composition mechanism is git — do not propose a YAML override rules system
- Do not invent a new concept if an existing one (IaC, YANG semantics, control loop) covers it
- YAML output must be deterministic: ordered keys, schema-first
- If you cannot state the YAML, API, and runtime mapping for a primitive → it is not closed
- For MCP queries: graph-first, not snippet-first
