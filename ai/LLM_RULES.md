# LLM Rules

- Minden állításhoz jelöld meg: **defined** / **draft** / **concept**
- Ha a státuszt nem tudod fájl-szinten alátámasztani, ne mondd ki tényként
- Aggregate-ből indulj, soha nem domain objektumból (Pod, Switch, VM)
- A kompozíció mechanizmusa git — ne javasolj YAML override rules rendszert
- Ne találj ki új fogalmat ha egy meglévő (IaC, YANG szemantika, control loop) fedi
- Kimenet YAML-ban determinisztikus: rendezett kulcsok, schema-first
- Ha egy primitive-re nem tudod megmondani a YAML, API és runtime mappinget → nem lezárt
- MCP kérdéseknél: graph-first, ne snippet-first
