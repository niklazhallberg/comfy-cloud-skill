# Perplexity research — 2026-05-21

Source: Perplexity AI deep-dive in response to research brief about the Comfy Cloud MCP proxy. Captured as the user shared it; unedited.

---

Ja — du kan bygga en ganska kraftfull MCP-proxy mot Comfy Cloud, men den bör utgå från att Comfy Cloud är en API-kompatibel men inte fullständigt likvärdig version av self-hosted ComfyUI: den exponerar ett officiellt Cloud-API för körning av workflows, filuppladdning, köstatus, outputhämtning, WebSocket-progress och node-introspection, samtidigt som API:t uttryckligen är experimentellt och vissa kompatibilitetsfält ignoreras i molnversionen.

Det viktigaste designbeslutet för din proxy är därför att behandla Comfy Cloud som ett jobb- och artefakt-API med dynamisk schemaintrospection, snarare än som "full remote ComfyUI access" med fri filsystems- och nodmiljökontroll.

## 1. API-ytan

Comfy Clouds officiella bas-URL är `https://cloud.comfy.org`, och all dokumenterad HTTP-auth sker via `X-API-Key`; de officiella Cloud-sidorna beskriver inte session cookies som primär auth-modell för API-anrop.

Comfy Org beskriver Cloud-API:t som kompatibelt med lokal ComfyUI, men markerar samtidigt API:t som experimental och säger uttryckligen att vissa kompatibilitetsendpoints kan ha annan semantik eller ignorera vissa fält.

### Dokumenterade endpoints

| Endpoint | Metod | Syfte | Requestform | Svar/form |
|---|---|---|---|---|
| `/api/user` | GET | Hämta användarinformation, används i auth-exempel. | X-API-Key header. | JSON med user-info; exakt schema ej utskrivet på översiktssidan. |
| `/api/object_info` | GET | Hämta alla tillgängliga node-definitioner. | Endast auth-header. | JSON map: node-namn → schema med input m.m. |
| `/api/upload/image` | POST | Ladda upp inputfiler. | multipart/form-data med image, type, ev. overwrite. | JSON med name och subfolder. |
| `/api/upload/mask` | POST | Ladda upp mask kopplad till originalbild. | Multipart med image, type, subfolder, original_ref. | JSON med uppladdad maskreferens. |
| `/api/prompt` | POST | Skicka workflow för exekvering. | JSON med minst `{ "prompt": <api-format-workflow> }`, ev. extra_data. | JSON med `prompt_id`, och ev. error. |
| `/api/job/{prompt_id}/status` | GET | Hämta status för ett jobb. | Auth-header + path-param. | JSON som `{ "status": "pending\|in_progress\|completed\|failed\|cancelled" }`. |
| `/api/jobs/{prompt_id}` | GET | Hämta jobbdetaljer inkl. outputs. | Auth-header + path-param. | JSON med bl.a. outputs; exakt schema visas indirekt i exempel. |
| `/api/view` | GET | Hämta outputfil via redirect till signerad URL. | Query: filename, subfolder, type; auth-header. | 302 redirect till temporär signerad URL. |
| `/api/queue` | GET | Hämta köstatus. | Auth-header. | JSON med queue_running och queue_pending. |
| `/api/queue` | POST | Avbryt jobb genom delete-lista. | JSON som `{ "delete": ["PROMPT_ID"] }`. | JSON/OK, exakt schema ej visat. |
| `/api/interrupt` | POST | Avbryt aktuell exekvering. | Auth-header. | Dokumenterad som kontroll-endpoint; exakt svarsschema framgår inte i hämtad text. |
| `/ws?clientId=...&token=...` | WebSocket | Realtidsstatus, progress, outputs och preview-bilder. | Query-parametrar clientId och token=<api_key>. | JSON textframes och binära preview-frames. |

### WebSocket-händelser

Cloud-dokumentationen listar följande JSON-meddelandetyper: `status`, `notification`, `execution_start`, `executing`, `progress`, `progress_state`, `executed`, `execution_cached`, `execution_success`, `execution_error`, och `execution_interrupted`.

För preview/render-streaming skickas också binära frames av typerna PREVIEW_IMAGE = 1, TEXT = 3, och PREVIEW_IMAGE_WITH_METADATA = 4, med specificerade big-endian frameformat.

### Auth, limits, storleksgränser

Officiellt auth-mönster för Cloud API är API-nyckel i `X-API-Key` för HTTP och `token=<api_key>` för WebSocket.

Dokumentationen anger concurrency-gränser på 3 parallella jobb för Creator och 5 för Pro, samt att jobb över gränsen köas automatiskt; pris-sidan anger också max runtime per workflow på 30 minuter för Standard/Creator och 1 timme för Pro, men den officiella Cloud API-översikten säger samtidigt att API-åtkomst kräver Creator eller Pro, så Standard-tidstaket är bara indirekt relevant för UI-läget och inte för API-berättigande.

Jag hittar däremot inga officiellt publicerade rate limits per minut/sekund eller explicita filstorleksgränser i de hämtade officiella sidorna, så din rapport bör markera dessa som "inte dokumenterade".

### Skillnader mot self-hosted

Cloud-sidorna säger att vissa kompatibilitetsendpoints finns kvar men kan ha annan semantik, och ger ett konkret exempel: `subfolder` accepteras för kompatibilitet på mask-upload men ignoreras i cloud storage eftersom lagringen är platt och content-addressed.

Det innebär att du inte bör anta self-hosted-beteenden som lokal katalogstruktur, fri filsystemsaccess eller diskbaserad subfolder-routing i proxyn.

I det officiella material jag hämtade finns ingen dokumentation som säger att Comfy Cloud låter användare installera custom nodes, ladda extensions eller hantera modellfiler via samma öppna filsystemsmekanismer som i self-hosted ComfyUI; frånvaro av sådan dokumentation, plus Clouds content-addressed storage och API-key-gated SaaS-arkitektur, talar för att din proxy bör behandla dessa som låsta eller minst icke-garanterade funktioner tills Comfy Org dokumenterar dem.

### O-dokumenterade men "stabila" endpoints

I de officiella Cloud-källorna jag kunde verifiera finns `/api/object_info`, men jag ser ingen officiell Cloud-dokumentation för per-node-variant som `/object_info/<NodeName>` eller interna modellfolder-listningar.

Du bör därför flagga sådant som community-observerat och inte göra det till kontrakterad del av din MCP-proxy utan feature flag eller capability probing.

## 2. Workflow-expressivitet

Det kanoniska formatet som Cloud accepterar på `/api/prompt` är ComfyUI:s **API format**: ett JSON-objekt där node-ID:n är nycklar och varje värde innehåller `class_type`, `inputs` och relaterad node-data; Cloud-dokumentationen säger uttryckligen att detta är formatet från frontendens "Save (API Format)".

Det innebär att din proxy bör standardisera på API-format internt och se canvas-workflow-JSON som ett redigerings-/authoringformat som måste konverteras innan submission.

### API-format vs canvas-workflow

Officiella Cloud-sidor beskriver API-formatet, men inte någon fullständig canvas-schema-konverteringstabell.

Det säkra mönstret är därför: bygg eller importera workflows i frontend/ComfyUI, exportera med "Save (API Format)", och låt din proxy mutera just inputs-värden programmässigt innan POST `/api/prompt`.

Comfy Org:s egna exempel för parameterisering gör exakt detta genom att skriva om `workflow[nodeId].inputs[inputName]`.

### Vilka pipelineklasser kan du bygga?

Officiell Cloud-dokumentation lovar inte en fast lista över installerade pipelines, men den exponerar `/api/object_info` just för att klienten ska upptäcka vilka nodes som faktiskt finns tillgängliga i molnmiljön.

Det betyder att din proxy tekniskt kan stödja allt som kan uttryckas i API-format och vars noder finns i Cloudens object_info, inklusive klassiska ComfyUI-grafer som txt2img, img2img, inpainting, multi-pass-kedjor, batchvarianter och outputnoder för bild/video/audio, men du bör presentera dessa som capability-by-introspection, inte som statiskt garanterade features.

Cloud-dokumentationen nämner också partner nodes för externa tjänster som Flux Pro och Ideogram, vilket visar att pipelineytan kan sträcka sig utanför rena lokala diffusion-noder när `extra_data.api_key_comfy_org` skickas med.

### Modeller, checkpoints, VAEs, LoRAs

I de officiella Cloud-sidorna jag hämtade finns ingen verifierad lista över förinstallerade checkpoints, VAEs, upscalers eller LoRAs.

Det officiella sättet att avgöra den tekniska ytan är därför inte en modellkatalogsida utan node-introspection plus de workflows du faktiskt kan köra på Cloud-kontot.

Jag hittar heller ingen officiell Cloud-dokumentation i de hämtade källorna för användaruppladdning av egna modellvikter, S3-import, Civitai-integration eller generell model registry access, så detta bör flaggas som ej officiellt dokumenterat.

### Custom nodes och Manager

Det finns ingen officiell text i de hämtade Cloud-källorna som säger att användare kan installera custom node-paket eller använda ComfyUI Manager i Comfy Cloud.

För en MCP-proxy är därför den robusta workaroundsstrategin: bygg bara mot officiellt exponerade nodes via `/api/object_info`, och om du behöver speciallogik, kapsla den i proxy-lagret genom workflow-templates, parametermappar och validering snarare än att förutsätta server-side custom nodes.

## 3. Orkestreringsmönster

Det officiella jobbflödet är tydligt: POST `/api/prompt` ger ett `prompt_id`, sedan kan du antingen polla status eller lyssna på WebSocket tills `execution_success` eller `execution_error`, och därefter hämta outputs via jobbdatan eller `/api/view`.

För en MCP-proxy bör `prompt_id` vara primär korrelationsnyckel genom hela livscykeln, eftersom även WebSocket-strömmen måste filtreras klient-side på just `prompt_id`.

### Chained workflows

För kedjning är standardmönstret att vänta tills första körningen är `completed` eller tills WebSocket har skickat `executed`/`execution_success`, extrahera outputreferenserna från nodresultaten och därefter mata dessa vidare i nästa workflowsubmission.

Eftersom `/api/view` returnerar 302 till signerad URL är det klokt att skilja på "metadata pipeline" och "blob download pipeline": agenten behöver oftast bara filreferenser tills den faktiskt måste ladda ner binärdata.

### Dynamisk schema-introspection

`/api/object_info` är den officiella introspektionsytan för tillgängliga noder och deras input/output-specifikationer.

Det gör den till rätt källa för automatisk tool-generering i en MCP-proxy: du kan bygga en registry-cache per konto/version, generera typed parameter-schema för LLM-tools och validera workflowmutationer mot node-definitionerna innan submission.

### Sweeps, seeds, determinism, caching

Comfy Orgs officiella exempel för parallell exekvering visar seed-variation genom att duplicera samma basworkflow och bara ändra seed, vilket i praktiken är det rätta mönstret för parameter sweeps och A/B-varianter.

För deterministisk regeneration bör proxyn därför spara minst: API-format-workflow, alla explicita inputvärden, seed, modellval och Comfy Cloud-miljöns capability snapshot från object_info; utan dessa är reproducerbarhet skör även om prompt_id sparas.

Cloud WebSocket definierar också `execution_cached`, vilket betyder att du kan exponera cache-awareness till agentlagret, men dokumentationen beskriver inte någon officiell "identical prompt dedupe" kontraktsnivå på `/api/prompt`, så sådan cache ska behandlas som körningsobservation snarare än garanti.

### Guardrails i proxy-lagret

Comfy Clouds officiella docs fokuserar på auth, jobs och execution, inte på agent-säkerhetspolicys, så guardrails behöver läggas i din proxy.

Praktiska kontrollpunkter är: kostbudget före submission, samtidighetsbudget mot Creator/Pro-gränserna, filtyp- och storleksregler för upload, prompt-/negativprompt-filter mot policybrott samt allowlists över godkända workflowtemplates och nodeklasser som agenten får använda.

Eftersom partner nodes kan debitera via samma Comfy-konto och kräver `extra_data.api_key_comfy_org`, bör just dessa noder markeras som högrisk i proxyn och kräva explicit tillåtelse eller separat policy.

## 4. Anpassning bortom standard

Den officiella dokumentationen ger inte färdiga "best practice"-grafer för varje avancerad multimodellkedja, men eftersom `/api/prompt` accepterar godtyckliga API-format-grafer och outputs kan vara bilder, video eller audio, finns det tekniskt stöd för multi-stage pipelines så länge nödvändiga nodes finns i object_info.

I praktiken betyder det att du kan modellera kedjor som generation → refinement → upscale → restoration som separata noder i samma graf eller som flera jobb, men din proxy bör först validera att respektive loader-, sampler-, conditioning- och save-noder faktiskt finns i molninstansen.

### LoRA, embeddings, conditioning

De officiella Cloud-källorna jag hämtade specificerar inte särskilda LoRA- eller embedding-endpoints; sådan styrning sker därför, när stödd, via vanliga workflownodes och deras inputs.

Det innebär att multi-LoRA-stackning, styrkekontroll och dynamiskt val ur registry i proxy-lagret bäst implementeras som template-parametrisering över kända loader/apply-noder som upptäckts via object_info, inte som fristående API-koncept.

Samma sak gäller prompt weighting, conditioning combine/average/concat, area conditioning och ControlNet-stacking: proxyn bör uttrycka dem som nodegrafmönster, inte som högre API-primitiver, om du vill hålla dig kompatibel med både Cloud och self-hosted.

### Animation och video

Cloud-dokumentationen säger uttryckligen att outputs kan vara images, video eller audio, vilket visar att videoarbetsflöden är en förstaklassig outputtyp i API:t.

Däremot listar de hämtade officiella sidorna inte specifikt AnimateDiff, SVD, Mochi, Hunyuan eller LTX som garanterat installerade i Comfy Cloud, så här måste du vara strikt: dokumentera dem endast som möjliga om motsvarande nodes/modeller finns i object_info eller i officiella Cloud-workflows, inte som alltid tillgängliga.

## 5. Claude Code-skill

Anthropic beskriver skills som kataloger med en obligatorisk SKILL.md, där YAML frontmatter styr när Claude ska använda skillen och markdownkroppen innehåller instruktionerna; supporting files kan läggas bredvid för referensmaterial, exempel eller scripts.

För ditt användningsfall bör du alltså inte lägga hela Comfy Cloud-kartan i en monolitisk fil, utan göra en tunn SKILL.md som beskriver syftet och länkar vidare till chunkade referenssidor.

### Rekommenderad skill-struktur

Anthropic rekommenderar att SKILL.md hålls fokuserad och att stora referensdokument flyttas till separata filer; de ger också en uttrycklig tumregel att hålla SKILL.md under 500 rader.

En bra repo-layout för din publika skill är därför ungefär:

- `.claude/skills/comfy-cloud-mcp/SKILL.md` — kort triggertext, guardrails, navigation.
- `reference/api-surface.md` — endpoints, auth, WebSocket, limits.
- `reference/workflow-format.md` — API-format, mutation patterns, prompt_id-lifecycle.
- `reference/pipeline-patterns.md` — txt2img/img2img/inpaint/video som capability templates.
- `reference/safety-and-cost.md` — proxy guardrails, quotas, moderation.
- `examples/*.md` — korta, konkreta workflow- och tool-exempel.
- `scripts/validate-workflow.*` — optional validator/generator som Claude kan köra.

### Frontmatter och triggerheuristik

Anthropic säger att `description` är det viktigaste fältet eftersom Claude använder det för att avgöra när skillen ska laddas, och att `when_to_use` kan komplettera med triggerfraser och exempel.

För just denna skill bör du sannolikt sätta `user-invocable: false` om den främst är bakgrundskunskap, eller låta den vara user-invocable om du också vill ha en explicit `/comfy-cloud-mcp`-entrypoint.

Om skillen innehåller scripts som ska få köras utan extra prompt kan `allowed-tools` användas, men Anthropic varnar indirekt för att sådana rättigheter bör granskas noga i repos som delas med andra.

### Kontextbudget

Anthropic förklarar att full skilltext stannar i kontexten efter invocation och att auto-compaction bara återfäster de senaste 5 000 token per skill inom en delad budget på 25 000 token.

Det betyder att din dokumentation bör vara hierarkisk: kort "router"-fil högst upp, sedan små fokuserade referensfiler som bara laddas när de behövs.

Det är exakt rätt upplägg för en Comfy Cloud skill, eftersom endpointkatalog, workflow-format, node-introspection och pipeline-recept annars snabbt blir för stora för att vara ergonomiska i Claude Code.

## 6. Källor att citera

De officiella Comfy Cloud-källor du bör prioritera är Cloud API Overview, Cloud API Reference och OpenAPI Specification på docs.comfy.org.

För Claude Code-skilldelen är Anthropics officiella "Extend Claude with skills" den centrala källan för skill-anatomi, frontmatter, supporting files, invocation control och context budget.

När communitykällor säger mer än de officiella docs gör, bör du uttryckligen markera konflikten som "community-observerat, ej officiellt verifierat", eftersom Comfy Org själva säger att Cloud-API:t är experimentellt och kan ändras utan förvarning.

## Implementation checklist

Följande är det jag skulle dokumentera i din GitHub-skillrepo från dag ett, för att göra proxyn användbar och robust.

- Dokumentera officiella endpoints: `/api/user`, `/api/object_info`, `/api/upload/image`, `/api/upload/mask`, `/api/prompt`, `/api/job/{prompt_id}/status`, `/api/jobs/{prompt_id}`, `/api/view`, `/api/queue`, `/api/interrupt`, och `wss://cloud.comfy.org/ws?...`.
- Dokumentera auth-flöden separat för HTTP och WebSocket: `X-API-Key` respektive `token` query-param.
- Dokumentera officiellt kända begränsningar: experimental API, Creator/Pro-krav, concurrency 3/5, runtime caps och att vissa kompatibilitetsfält ignoreras i cloud.
- Dokumentera att `subfolder` på cloud inte ska tolkas som verklig katalogstruktur.
- Dokumentera att intern proxyrepresentation ska vara API-format workflow JSON, inte canvas-workflow.
- Dokumentera schema-introspection via `/api/object_info` och bygg tool/capability generation ovanpå den.
- Dokumentera prompt-lifecycle: submit → prompt_id → poll/WebSocket → outputs → `/api/view`.
- Dokumentera WebSocket-händelser och hur agenten filtrerar på prompt_id.
- Dokumentera att partner nodes kräver `extra_data.api_key_comfy_org` och därför bör policygranskas.
- Dokumentera att modellistor, custom nodes, Manager-stöd, egna viktuppladdningar och vissa avancerade pipelineklasser bara ska markeras som stödda när officiell dokumentation eller object_info bekräftar dem.
- Strukturera skillen som liten SKILL.md + chunkade referensfiler + eventuella scripts, i linje med Anthropics skill-rekommendationer.
