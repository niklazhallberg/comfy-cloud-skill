# Forskningsrapport om MCP-proxy för Comfy Cloud

## Comfy Clouds API-yta

Comfy Cloud har nu en officiell, maskinläsbar Cloud API-yta med bas-URL `https://cloud.comfy.org`, och Comfy beskriver den uttryckligen som **experimentell** och **i huvudsak kompatibel med lokal ComfyUI:s API**. Den dokumenterade autentiseringsmodellen för HTTP är `X-API-Key`, och körning via API kräver enligt den officiella översikten en **Creator- eller Pro-prenumeration**. För realtidsuppdateringar används WebSocket på `wss://cloud.comfy.org/ws?clientId={uuid}&token={api_key}`. Comfy dokumenterar också att `clientId` för närvarande ignoreras i Cloud och att alla anslutningar för en användare får samma meddelanden, vilket är viktigt om din proxy ska multiplexa flera agent-sessioner mot ett och samma konto. citeturn5view0turn1search4turn1search0

Det viktigaste praktiska resultatet för en MCP-proxy är att Cloud-API:t i dag inte bara är “submit and poll”, utan ett bredare lager för körning, modell-/nodintrospektion, historik, queue-hantering, filvisning, upload, asset management, user-data och system/user-info. Samtidigt hittade jag **inga publikt dokumenterade numeriska request-per-second eller request-per-minute-gränser** i de officiella Cloud-dokumenten; det som är tydligt dokumenterat är i stället samtidighetsgränser på abonnemangsnivå samt att vissa endpoints kan svara med `429`. citeturn5view0turn1search5turn1search4

### Dokumenterade HTTP-endpoints på Comfy Cloud

Följande är de **dokumenterade** Cloud-endpoints som den officiella OpenAPI-specifikationen exponerar i dagsläget. Jag grupperar dem funktionsmässigt för att hålla kartan läsbar; varje path/method nedan kommer från den officiella Cloud OpenAPI-specen och/eller Cloud API Reference. citeturn1search4turn6search3turn35search13

**Körning och schemaintrospektion**

`POST /api/prompt` skickar ett workflow för exekvering.  
`GET /api/prompt` hämtar information om aktuell prompt-/queue-status.  
`GET /api/object_info` returnerar alla noddefinitioner.  
`GET /api/features` returnerar feature flags som bland annat `supports_preview_metadata` och `max_upload_size`.  
`GET /api/workflow_templates` listar workflow templates.  
`GET /api/global_subgraphs` listar globala subgraph-blueprints.  
`GET /api/global_subgraphs/{id}` hämtar ett specifikt subgraph blueprint.  
`GET /api/experiment/models` listar modellmappar.  
`GET /api/experiment/models/{folder}` listar modeller i en viss mapp.  
`GET /api/experiment/models/preview/{folder}/{path_index}/{filename}` hämtar preview-bild för modell. citeturn1search4turn6search3turn8search12

**Historik, jobb och kö**

`POST /api/history` hanterar historikoperationer, till exempel clear eller delete.  
`GET /api/history_v2` hämtar historik i v2-format.  
`GET /api/history_v2/{prompt_id}` hämtar historik för ett specifikt prompt-id.  
`GET /api/jobs` listar jobb med filtrering och paginering.  
`GET /api/jobs/{job_id}` hämtar fullständiga jobbdetaljer.  
`GET /api/job/{job_id}/status` hämtar endast status för ett jobb.  
`GET /api/queue` hämtar queue-information.  
`POST /api/queue` hanterar queue-operationer, till exempel att avbryta väntande jobb.  
`POST /api/interrupt` avbryter körande jobb. citeturn1search4turn6search3turn6search7

**Filer, outputs och upload**

`GET /api/view` visar eller laddar ned en fil via redirect till signerad URL.  
`GET /api/files/mask-layers` hämtar relaterade masklagerfiler.  
`POST /api/upload/image` laddar upp en bildfil.  
`POST /api/upload/mask` laddar upp en mask kopplad till en originalbild.  
`GET /api/userdata` listar användardatafiler.  
`GET /api/userdata/{file}` hämtar en användardatafil.  
`POST /api/userdata/{file}` skapar eller uppdaterar en användardatafil.  
`DELETE /api/userdata/{file}` raderar en användardatafil. citeturn1search4turn6search3turn35search13

**Assets och taggar**

`GET /api/assets` listar användarassets.  
`POST /api/assets` laddar upp nytt asset, antingen multipart-fil eller URL-baserat JSON-anrop.  
`POST /api/assets/from-hash` skapar en assetreferens från befintlig hash.  
`GET /api/assets/remote-metadata` hämtar metadata för extern URL.  
`POST /api/assets/download` startar bakgrundsnedladdning av större filer.  
`GET /api/assets/{id}` hämtar detaljer för ett asset.  
`PUT /api/assets/{id}` uppdaterar metadata för ett asset.  
`DELETE /api/assets/{id}` raderar ett asset.  
`POST /api/assets/{id}/tags` lägger till taggar.  
`DELETE /api/assets/{id}/tags` tar bort taggar.  
`GET /api/tags` listar taggar.  
`GET /api/assets/tags/refine` returnerar tagghistogram för filtrerade assets.  
`HEAD /api/assets/hash/{hash}` kontrollerar om asset finns via hash. citeturn1search4turn6search3

**System och användare**

`GET /api/system_stats` returnerar systemstatistik inklusive version- och device-info.  
`GET /api/user` returnerar info om aktuell användare. citeturn1search4turn6search3turn6search7

### Request shape, response shape, auth och gränser

Den viktigaste endpointen är `POST /api/prompt`. Request-bodyn är ett objekt med minst `prompt`, samt valfritt `number`, `front`, `extra_data` och `partial_execution_targets`. I Cloud är `number` och `front` dokumenterat accepterade **endast för API-kompatibilitet** och **ignoreras** i praktiken; Cloud använder egen köordning och fair scheduling. Svaret innehåller typiskt `prompt_id`, `number` och `node_errors`. Dokumenterade felkoder inkluderar `400`, `402`, `429`, `500` och `503`. Det här är en viktig skillnad mot självhostad ComfyUI: kompatibilitetsfälten finns kvar, men deras kösemantik är inte kontraktsmässigt giltig i Cloud. citeturn1search5turn5view0

`GET /api/object_info` returnerar en nodkatalog där varje noddefinition innehåller sådant som namn, kategori, input-specifikationer, input-ordning, outputs, outputnamn, om noden är experimental/deprecated/api-node samt vilket Python-modulnamn som implementerar noden. Det är exakt den här endpointen du bör använda för att bygga ett typat schema-lager i proxyn, inte hårdkodade nodmallar. citeturn29view0turn1search4

`GET /api/features` returnerar åtminstone `supports_preview_metadata` och `max_upload_size` i bytes. För `POST /api/upload/image` finns dessutom en separat, mer konkret bildgräns: officiellt **50 MB**, max **16384 px per sida** och max **64 megapixlar**; större bilder ska avvisas med `400`. Det gör att din proxy bör validera både bytes och pixeldimensioner client-side innan den skickar upp filer. citeturn6search0turn6search4

`GET /api/view` används för outputs och returnerar inte i första hand filinnehållet direkt, utan en **302-redirect** till en temporär signerad URL. Den accepterar query-parametrar som `filename`, `subfolder`, `type`, `fullpath`, `format`, `frame_rate`, `workflow`, `timestamp` och `channel`. Följaktligen måste en agent- eller proxyklient kunna följa redirects, och bör behandla signerade URL:er som kortlivade hämtlänkar snarare än permanenta asset-identifierare. citeturn5view0turn1search4

`POST /api/upload/image` och `POST /api/upload/mask` är explicita Cloud-kompatibilitetslager för inputfiler. Den officiella Cloud API Reference säger att `subfolder` accepteras för kompatibilitet, men **ignoreras** i Cloud-lagringen; Cloud använder i stället ett platt, content-addressed namespace. Det betyder att om du porterar workflow-logik från självhostad ComfyUI som förlitar sig på mappstruktur, bör proxyn abstrahera bort detta och arbeta med server-returnerade filreferenser i stället. citeturn35search13turn6search2

Historiklagret är i rörelse. Den officiella dokumentationen markerar `GET /api/history_v2` som **deprecated** till förmån för `GET /api/jobs`, och `GET /api/history_v2/{prompt_id}` som **deprecated** till förmån för `GET /api/jobs/{job_id}`. Samma officiella docs säger uttryckligen att `prompt_id` från `POST /api/prompt` är samma värde som `job_id`. För ny proxykod bör du därför modellera `prompt_id == job_id` och föredra `/api/jobs`-familjen, medan `/api/history_v2` hålls som bakåtkompatibilitetslager. citeturn6search7

Queue-semantiken är också uppdelad: `POST /api/queue` påverkar väntande jobb, medan `POST /api/interrupt` avbryter körande jobb. Om du bygger agentåtgärder som “cancel current” eller “clear backlog” bör de därför mappas till olika verktyg i din MCP-proxy i stället för ett enda generiskt “cancel”. citeturn6search7

### WebSocket-event och progress-signaler

Clouds officiella docs pekar ut WebSocketen som standardvägen för realtidsprogress. I Cloud-översikten visas ett exempel där du filtrerar på `prompt_id` och hanterar minst `executing`, `progress`, `executed` och `execution_success`. Självhostade server-dokumentationen beskriver samma meddelandefamilj mer explicit: `status`, `execution_start`, `execution_error`, `execution_interrupted`, `execution_cached`, `execution_success`, `executing`, `executed` och `progress`. Cloud API Reference beskriver dessutom råa binära preview-frames, där åtminstone typerna `PREVIEW_IMAGE`, `TEXT` och `PREVIEW_IMAGE_WITH_METADATA` förekommer. Praktiskt betyder det att din proxy bör ha **två** WS-stigar i implementationen: en JSON-meddelandehanterare för livscykelhändelser och en binär frame-hanterare för previews/progress-text. citeturn5view0turn1search7turn8search7

### Skillnader mot självhostad ComfyUI

På självhostad ComfyUI är servern och frontendens extensionsystem avsevärt mer öppna. Den officiella server-/openapi-dokumentationen för OSS visar endpoints som bland annat `/api/object_info/{node_class}`, `/api/embeddings`, `/api/extensions`, `/api/models`, `/api/view_metadata`, `/api/settings`, `/api/users`, `/api/free` och flera bare aliases. Frontend-dokumentationen visar också att ComfyUI vid startup hämtar `/extensions` och dynamiskt laddar JavaScript från `/web/extensions/*.js` och `/custom_nodes/*/web/*.js`, medan backend skannar `/custom_nodes/` och exponerar dessa noder via `/object_info`. citeturn18view0turn18view1turn29view0

I Cloud är bilden mer kuraterad. Den officiella Cloud-sidan säger att Cloud har **pre-installed custom nodes**, stöder de mest populära custom nodes och att workflows fungerar mellan Local och Cloud, men den säger också att Local är **infinitely customizable** medan Cloud bara stödjer de extensions och modeller som Comfy valt att göra tillgängliga. Jag hittade ingen officiell dokumentation som lovar användarinstallerade custom-node packs eller ComfyUI Manager-stöd i Cloud. Den säkra tolkningen är därför att Cloud ska ses som en **managed nod-/modellkatalog**, inte som fritt root-åtkomlig ComfyUI-hosting. citeturn36view0

För de “odokumenterade men stabila” ytorna är min slutsats: på **självhostad** ComfyUI är `/api/object_info/{node_class}` och det äldre `/api/models` tydligt officiella eller åtminstone formellt publicerade i OSS-openapi; på **Cloud** bör du däremot luta dig mot det som faktiskt finns i Cloud OpenAPI, där modellupptäckt uttryckligen ligger under de **experimentella** `/api/experiment/models*`-endpoints. Jag skulle alltså inte bygga en publik agentproxy som förutsätter parameteriserad `/api/object_info/<NodeName>` på Cloud innan Comfy själva dokumenterar den där också. citeturn18view0turn1search4turn6search7

## Workflowens uttryckskraft

Den viktigaste övergripande slutsatsen är att Comfy Cloud i princip försöker ge dig **hela inferenspipelinen**, inte ett litet, prompt-fokuserat delmängds-API. Comfy marknadsför Cloud med “Every node exposed. Every setting adjustable” och beskriver den som “the full power of ComfyUI” med förinstallerade modeller och custom nodes. Den officiella FAQ:n säger också att workflows fungerar mellan Local och Cloud, med begränsningen att bara stödda custom nodes är tillgängliga i Cloud. citeturn36view0

### API-format kontra workflow-format

Det finns två viktiga JSON-format att hålla isär. Cloud-översikten säger uttryckligen att API:t accepterar workflows i **“API format”**, alltså formatet som frontendens **Save (API Format)** producerar. Frontendkoden gör detta ännu tydligare: `graphToPrompt()` returnerar både `workflow` och `output`, där `workflow` är canvas-/graph-formatet och `output` är API-formatet som skickas till backend. citeturn5view0turn27view0

I praktiken betyder det här följande. **Workflow-formatet** är ett serialiserat grafdokument för canvasen: noder, länkar, layout, `extra`, versionsinfo och andra UI-relaterade detaljer. **API-formatet** är däremot ett objekt där varje nod-id är en nyckel, och värdet innehåller `class_type`, `inputs` och `_meta.title`. Nodlänkar serialiseras som tvåelement-arrayer av formen `["origin_id", origin_slot]`. Widget-värden serialiseras direkt i `inputs`, men om widget-värdet själv är en array kapslar frontend det som `{ "__value__": [...] }` så att backend inte misstar det för en länk; kurv-widgets serialiseras i stället som `{ "__type__": "CURVE", "__value__": [...] }`. Det här är en av de viktigaste detaljerna att kopiera korrekt i en proxy som genererar prompt-JSON programmatiskt. citeturn27view0

Det omvända flödet finns också i frontend. `loadApiJson()` tar ett API-format, skapar noder från `class_type`, återansluter länkar, sätter widgetvärden och försöker till och med konvertera widgets till riktiga inputs om det behövs. `workflowService` beskriver dessutom uttryckligen tre huvudsakliga inläsningsvägar i frontend: `loadGraphData`, `loadApiJson` och `importA1111`. Det är precis den här tredelningen din dokumentation bör lära ut till agenten: **graf-format för sparade workflows och canvas**, **API-format för exekvering**, och ibland **A1111-parametertext** som fallback-importkälla. citeturn28view0turn26view0

En viktig, lätt missad detalj från frontend är att **API-prompt-serialisering** använder `widget.options.serialize`, inte `widget.serialize`. Den senare styr workflow persistence, men inte nödvändigtvis om ett värde kommer med i prompt-JSON. Om du senare bygger helperkod eller custom UI över proxyn kan den här skillnaden orsaka “det ser sparat ut i workflow, men skickas inte till körningen”-buggar. citeturn25search4turn27view0

### Vilka pipelineklasser kan du realistiskt exponera

Det som är **högst säkerställt** i den officiella dokumentationen är att Cloud stöder breda bild-, video- och 3D-scenarier, samt både öppna modeller och partner/API-modeller. Comfy nämner uttryckligen öppna modeller som **Wan 2.2, Flux, LTX och Qwen**, och partnermodeller som **Nano Banana, Seedance, Seedream, Grok, Kling och Hunyuan 3D**. Samma sida säger att community-workflows kan browsas, köras och remixas i Cloud, att custom nodes är förinstallerade, och att “nodes powering ~90% of local ComfyUI workflows are now in the cloud”. På en hög nivå innebär det att en agentproxy absolut kan sikta på verktyg för text-to-image, image editing, text-to-video, image-to-video, 3D och sammansatta multimodala pipelines. citeturn36view0

Det som däremot **inte** finns som en enda offentlig, uttömmande källa är en live-matris som säger “dessa exakta installerade node packs + dessa exakta checkpoints + dessa exakta LoRAs + dessa exakta VAEs finns just nu i Cloud”. Därför skulle jag dela upp pipelineklasser i två grupper:

Det som du kan behandla som **plattformsmässigt möjligt** om noder/modeller finns i katalogen: txt2img, img2img, inpainting, batch generation, multi-pass upscaling, LoRA-laddning, refiner-steg, compositing och andra klassiska ComfyUI-grafer. Cloud ger dig hela nodgrafen, och `/api/object_info` samt `/api/experiment/models*` är den robusta runtime-källan för just din users faktiska räckvidd. citeturn36view0turn1search4turn5view0

Det som du **inte** bör hårdkoda som “garanterat finns” utan att verifiera i runtime: ControlNet-stacking, IP-Adapter, AnimateDiff, SVD, regional prompting, face restoration, Mochi/Hunyuan/LTX som specifika nodkedjor, samt custom-node-beroende specialpipelines. De kan mycket väl vara genomförbara i Cloud, men den publika dokumentationen som granskats här publicerar inte en fullständig installerad nodmatris. För de här klasserna bör proxyn först fråga `/api/object_info`, eventuellt kombinera med Cloud/MCP-discovery (`search_models`, `search_nodes`, `search_templates`) och därefter bestämma om ett verktyg ska exponeras eller döljas. citeturn4view0turn36view0turn1search4

### Modeller, checkpoints, VAEs, upscalers och LoRAs

Här finns en viktig **officiell konflikt** som du bör spegla i din skilldokumentation. Cloud-marknadssidan säger i brödtexten att du kan “Upload custom LoRAs or finetuned foundational models from CivitAI and Hugging Face.” Men FAQ-delen på samma officiella sida säger något smalare: att Creator- och Pro-användare i nuläget kan ta in **egna fine-tuned LoRAs från CivitAI**, medan **Hugging Face-import och direktfiluppladdning för större modeller** ligger på roadmap. När samma officiella källa motsäger sig själv så här, skulle jag i proxyn behandla **CivitAI LoRA-import** som den högst förtroendeingivande BYO-vägen, och behandla **Hugging Face/full checkpoint-import** som capability som måste testas live, inte antas. citeturn36view0

Det är också viktigt att skilja på **filer** och **registrerande modellinstallation**. Cloud har dokumenterade endpoints för asset-upload (`/api/assets`) och image/mask-upload (`/api/upload/image`, `/api/upload/mask`), men jag hittade ingen officiell Cloud-API-dokumentation som säger att ett generiskt asset-upload automatiskt gör en checkpoint, VAE eller upscale-model synlig under `/api/experiment/models/{folder}`. För en publik proxy bör du därför dokumentera att “asset upload” inte är samma sak som “model install”. Om du vill ha stabil modellinventering bör du läsa den från de officiella modelldiscovery-endpointsen, inte från assetlagret. citeturn1search4turn36view0

### Custom nodes och Manager-stöd

Den officiella skillnaden mellan Local och Cloud är i praktiken att Local kan skanna `/custom_nodes/`, ladda Python-moduler, exponera dem via `/object_info` och frontend-JS via `/extensions`, medan Cloud levererar en färdig, kuraterad uppsättning “most popular custom nodes”. Därför är den tekniskt säkra work-arounden inte att försöka replikera ComfyUI Manager i din proxy, utan att i stället göra två saker: först upptäcka aktuella Cloud-abilities via `/api/object_info`; sedan mappa högre nivåers agentverktyg endast till de nodkombinationer som faktiskt finns. citeturn29view0turn36view0

## Mönster för pipelineorkestrering

En robust Cloud-proxy bör modellera exekvering som en tydlig livscykel: **submit → prompt_id/job_id → monitorera → hämta outputs → eventuellt kedja vidare**. Officiellt är det här exakt så Comfy beskriver flödet: `POST /api/prompt` för submission, sedan WebSocket eller `GET /api/job/{prompt_id}/status` för progress, och därefter `GET /api/view` för outputfiler. Eftersom Comfy också dokumenterar att `prompt_id` och `job_id` är samma identifierare i de nyare job-endpointsen, kan din proxy lugnt använda ett enda internt begrepp som exempelvis `jobId`. citeturn5view0turn6search7

### Chained workflows

För kedjade workflows finns två solida mönster. Det första är **intra-job routing**, där du håller allt i en enda API-format-graf och låter noderna koppla outputs direkt till senare steg. Det andra är **inter-job chaining**, där ett steg avslutas, outputs hämtas eller återrefereras, och nästa `POST /api/prompt` byggs från det resultatet. ComfyUI MCP Server beskriver redan verktyget `use_previous_output` för att kedja workflows över körningar, vilket är en bra ledtråd för hur en agentcentrerad proxy bör abstrahera saken även om du använder rå HTTP i bakgrunden. citeturn4view0

För monitorering är rekommendationen att stödja både polling och WS. Polling via `GET /api/job/{id}/status` är enklare och räcker för många verktyg. Men om du vill låta en LLM agent reagera på “node completed”, “preview updated”, “execution successful” och “execution failed” i realtid är WebSocket-spåret överlägset, särskilt eftersom Cloud-dokumentationen och OSS-meddelandedokumentationen tillsammans täcker händelser som `execution_start`, `executing`, `progress`, `executed`, `execution_success`, `execution_error` och `status`. citeturn5view0turn1search7

### Dynamisk schemaintrospektion

Standardapproachen här bör vara: hämta `/api/object_info`, bygg en typad registry över tillgängliga noder, och generera sedan workflow-JSON utifrån den. Det är också ungefär så den officiella frontendkoden är uppbyggd: canvasen serialiseras till API-format via `graphToPrompt`, och `loadApiJson` kan invertera API-format till canvasscenariot. Med andra ord är frontendkoden den mest auktoritativa referensen för hur Comfy självt betraktar den formella översättningen mellan mänskligt redigerbar graf och exekverbart prompt-JSON. citeturn27view0turn28view0

Praktiskt rekommenderar jag att proxyn cachar object-info per session eller per kombination av användare + Cloud-version, och invaliderar cache när du ser tydlig server/version-förändring i `system_stats` eller när ett anrop får node-schemafel. På så sätt kan agenten generera verktygsbeskrivningar och formulär dynamiskt utan att hårdkoda ett gammalt node universe. `GET /api/system_stats` returnerar uttryckligen versions- och deviceinformation, vilket gör det användbart som capability fingerprint. citeturn6search7turn1search4

### Sweeps, seeds, A/B, registries och cache

För parameter-sweeps är den officiella Cloud-översikten redan tydlig: API-användare kan skicka flera `POST /api/prompt` parallellt upp till abonnemangets samtidighetsgräns. Comfy visar själv ett exempel där samma workflow klonas och bara seed ändras mellan körningarna. Det här är den renaste modellen för A/B-varianter också: håll ett normaliserat bas-workflow och generera minimala deltan för seed, prompt, LoRA-styrka eller modellalias. citeturn5view0

För deterministisk regenerering bör du lagra åtminstone följande i din proxy: det exakta API-format-JSON:t som skickades, seedar, uppladdade assetreferenser eller hashar, modellreferenser, och gärna en snapshot av relevanta noddefinitioner eller åtminstone en versionsstämpel. Lokalt sparar ComfyUI normalt workflow-JSON i bildmetadata så att en genererad bild kan dras tillbaka in i canvasen, men MCP-servern dokumenterar uttryckligen att **MCP-genererade assets saknar workflow metadata**. Därför bör din proxy aldrig förlita sig på att outputfiler i sig är tillräckligt självbärande som reproducerbarhetskälla. citeturn8search6turn8search16turn4view0

För asset-registry är det rimligt att använda `/api/assets`, taggar och `user_metadata` som ditt officiella lager, snarare än att försöka tolka filnamn från `/api/view`. `HEAD /api/assets/hash/{hash}` och `POST /api/assets/from-hash` gör dessutom content-addressed dedupe möjlig i designen. Däremot hittade jag ingen officiell dokumentation som lovar cross-job prompt-cache i Cloud, även om Comfy generellt dokumenterar att nodexecution kan använda cache lokalt. Därför bör **identical prompt caching** i en agentproxy implementeras som ett eget proxy-lager, inte antas från Cloud-plattformen. citeturn1search4turn6search3turn6search6

### Guardrails i proxy-lagret

Här finns flera guardrails som är tekniskt motiverade av de officiella dokumenten. Kostnad: API och UI delar samma kreditpool, och samtidigheten är abonnemangsberoende. Din proxy bör därför ha per-användare-kvoter, max batch count, max samtidiga jobb och gärna uppskattad kreditexponering innan submission. Filguardrails: validera `max_upload_size`, bildstorlek, pixeldimensioner och MIME-typer före upload. Queueguardrails: skilj mellan cancel pending och interrupt running. Capabilityguardrails: exponera inte verktyg vars noder inte finns i `/api/object_info`, eller vars modellfamiljer inte syns i modelldiscovery eller mallkatalogen. citeturn5view0turn6search0turn6search4turn6search7

För NSFW/content policy hittade jag **ingen tydligt publicerad, produktnära policytext i den dokumentation som granskades här**. Därför bör du lägga dina faktiska innehållsregler i proxyn, inte hoppas att Cloud fungerar som enda policygrind. Det gäller särskilt om en LLM-agent får fria händer att välja modeller, ladda referensbilder och kedja flera steg. Den säkra designen är att proxyn gör preflight-klassificering, modell-/nodallowlist och storleks-/kostnadskontroll **innan** `POST /api/prompt`. citeturn5view0turn36view0

## Anpassning bortom standard

Det centrala här är att ComfyUI redan är byggt som en modulär graf för modellkedjor, och Cloud försöker bevara den egenskapen. Därför är den rätta abstraktionen för din proxy inte “en modell = ett verktyg”, utan “en validerad nodgraf = ett verktyg eller ett verktygsanrop”. Comfy säger själv att Cloud ger tillgång till hela inferenspipelinen och att du kan välja sampler, scheduler och model chain, vilket är precis det som gör multi-model-pipelines rimliga att exponera för en agent. citeturn36view0

### Multi-model-pipelines

Exempel som “SD1.5 generation → SDXL refiner → 4x ESRGAN upscale → face restoration” är i ComfyUI-termer inte magi utan bara sekventiell nodkoppling över latens- och bilddomäner. Det officiellt säkra sättet att beskriva dem i din dokumentation är därför som **mönster**, inte som garantier om exakta installerade nodnamn i Cloud: ett basgenereringssteg, ett refinementssteg, ett upscale-steg och eventuellt ett restorationssteg. Om alla fyra behövliga noder/modeller finns i `object_info` och modelldiscovery kan proxyn generera eller acceptera den kedjan som ett API-format-workflow. Om någon del saknas, bör verktyget inte exponeras. citeturn36view0turn1search4

Det finns också ett bra skäl att skilja mellan **single-job composition** och **multi-job composition**. Single-job är bäst för rena nodkedjor där outputs går direkt vidare. Multi-job är bättre när du vill materialisera mellanresultat som beständiga inputs, återanvända ett tidigare output i flera grenar, eller låta agenten inspektera ett mellanresultat innan nästa steg. ComfyUI MCP Server pekar här direkt på ett bra verktygsmönster med `use_previous_output`, `get_output` och `upload_file`. citeturn4view0

### LoRA- och embeddinghantering

LoRAs passar väl för ett agentdrivet registry-tänk. Eftersom Cloud-dokumentationen är motsägelsefull kring exakt hur långt BYO-modeller har kommit, bör du behandla LoRA-val som en registryfunktion i proxyn: ett vänligt namn, en dokumenterad källa/importstatus, en styrkeprofil och ett känt Cloud-referensobjekt eller modellalias. Själva körningen är sedan bara workflow-graf med en eller flera loader/apply-noder, men proxyn bör äga policyn: max antal LoRAs, tillåtna styrkor, kompatibla basmodeller och vilken källa som är officiellt stödd på kontot. citeturn36view0

### Conditioning, prompt weighting och regional styrning

Här måste man skilja mellan HTTP-ytan och nodytan. Cloud-API:t bryr sig i grunden inte om prompt weighting, BREAK-syntax, conditioning concat/average/combine, area conditioning eller ControlNet-stacking som begrepp; API:t tar bara emot nodgrafen. Om en installerad nod i `object_info` accepterar en viss conditioningstruktur, kan proxyn skicka den. Därför bör dokumentationen för agenten inte hårdkoda textsyntaktiska påståenden som “BREAK fungerar alltid”, utan i stället beskriva dessa som **nodberoende tekniker** som ska valideras mot just den nodfamilj som finns tillgänglig. Det är mer tekniskt korrekt och mindre skört över tid. citeturn1search4turn27view0

### Animation och video på Cloud

På video-/animationssidan är den publika signalen stark på modellnivå men svagare på uttömmande nodnivå. Officiella Cloud-sidan nämner bland annat **Wan 2.2**, **LTX**, **Seedance**, **Grok Video**, **Kling** och **Hunyuan 3D**. MCP-servern visar dessutom att du kan söka templates, modeller och noder, vilket är ett tydligt tecken på att Comfy ser video-/3D-upptäckt som ett centralt agentscenario. Men jag hittade inte en enda offentlig sida som säger “AnimateDiff finns installerat i Cloud”, “SVD finns installerat i Cloud” eller “Mochi/Hunyuan/LTX finns som dessa exakta noder”. Slutsatsen blir: text-to-video, image-to-video och partner-node-video är högst plausibla och delvis officiellt demonstrerade via modellkatalogen; custom-node-specifika videokedjor måste capability-checkas i runtime. citeturn36view0turn4view0turn3search5

## Som Claude Code-skill

Anthropics nuvarande officiella modell är tydlig: en skill är ett `SKILL.md`-dokument med valfri frontmatter, stöd för supporting files och möjlighet att laddas automatiskt när relevant eller invokeras direkt via `/skill-name`. Officiellt laddas skillens kropp **bara när den används**, till skillnad från `CLAUDE.md` som ligger kvar som alltid-på-kontext. Det gör skills till exakt rätt leveransformat för ett Comfy Cloud-kunskapslager som annars skulle bli för tungt att ligga permanent i kontext. citeturn32view0turn32view1

### Rekommenderad skill-anatomi

För just din use case skulle jag inte leverera **en** stor skill, utan två nära relaterade:

En **referensskill**, auto-invocable, till exempel `comfy-cloud-reference`, vars jobb är att hjälpa Claude Code att förstå endpoints, workflow-format, capability detection, säkerhetsgrindar och vanliga mönster. Den bör ha ganska kort `SKILL.md` med tydlig `description`, och peka vidare till supporting files för endpointkatalog, JSON-format, orchestrationmönster och kända konflikter i docs. Eftersom Anthropic säger att descriptions används för att avgöra när en skill ska användas och att den texten trunkeras i skill-listningen, bör de första meningarna vara mycket explicit formulerade. citeturn34view1turn34view2

En **exekveringsskill**, manuellt invokerad, till exempel `comfy-cloud-execute`, med `disable-model-invocation: true`. Den bör användas för side-effectful handlingar som faktiskt submitter workflows, avbryter jobb eller laddar upp filer. Officiellt är just detta ett rekommenderat användningsfall för `disable-model-invocation: true`: arbetsflöden med side effects där du inte vill att modellen själv bestämmer när de aktiveras. citeturn34view1

Om du senare vill paketera allt för återanvändning utanför en enskild repo är nästa naturliga steg en **plugin**, eftersom Anthropic beskriver plugins som paketlagret som kan bunta ihop skills, hooks, subagents och MCP-servrar. Men för ett publikt GitHub-repo som i första hand ska ge Claude Code domänkunskap är en vanlig `.claude/skills/<name>/SKILL.md`-struktur fullt tillräcklig. citeturn32view1turn33view0

### Filerna jag skulle lägga i skill-repot

Anthropic rekommenderar uttryckligen att supporting files används för att hålla `SKILL.md` fokuserad och låta Claude ladda stora referensdokument bara när de behövs. För ditt repo innebär det att huvudskillen bör vara en navigations- och policyfil, inte en monolit. En bra struktur vore:

`SKILL.md` som översikt, triggrar, säkerhetsregler och navigering.  
`endpoints-reference.md` som inventerar Cloud-endpoints och WS-event.  
`workflow-json-vs-api-format.md` som förklarar serialisering, `graphToPrompt`, `loadApiJson`, länkar och widgetvärden.  
`capability-detection.md` som beskriver hur `/api/object_info`, `/api/features` och `/api/experiment/models*` ska användas.  
`pipeline-recipes.md` för mönster som multi-stage refine, upscale, chaining, LoRA registry, deterministic replay.  
`conflicts-and-limitations.md` för dokumenterade motsägelser och öppna frågor.  
`examples/` för verkliga API-format-JSON-exempel.  
`scripts/` endast om du verkligen behöver helperkod; Anthropic säger uttryckligen att supporting scripts kan exekveras men inte behöver laddas in i kontext. citeturn34view4turn32view0

### Frontmatter och kontextbudget

Enligt Anthropic är `description` det enda fält som verkligen bör finnas i nästan alla skills, eftersom Claude använder det för att avgöra när skillen ska lastas. `allowed-tools` kan förgodkänna vissa verktyg när skillen är aktiv, men Anthropic betonar att detta också är en säkerhetsrisk i projektrepon eftersom skillen efter trust-dialogen kan ge sig själv bred access. För en publik skill som ska distribueras via GitHub bör du därför vara mycket restriktiv med `allowed-tools` och använda det främst i den manuella exekveringsskillen, inte i referensskillen. citeturn33view2turn34view1

Anthropic dokumenterar också att en invokerad skill stannar kvar i sessionen, att auto-compaction reattacher den med en budget på första 5000 tokens per skill och totalt 25000 tokens över återinfogade skills. Det här är ett starkt argument för att hålla `SKILL.md` kort och skjuta ned detaljer till separata filer. Det är också ett argument för att dela upp din Comfy Cloud-kunskap i flera domain-specific supporting docs i stället för ett enda jättedokument. citeturn33view3turn34view1

Som inspirationskälla från community-sidan – inte som norm – finns ett stort, kuraterat ekosystem kring Claude Code-skills i samlingen **awesome-claude-code**. Jag skulle dock fortfarande låta Anthropics egna docs vara den enda källan för hur skillkontraktet formellt ska se ut. citeturn31search1turn32view0

## Officiella källor att citera

Det mest användbara officiella Comfy-underlaget för din repo är följande källpaket:

**Cloud och API**
Cloud API Overview, Cloud API Reference och OpenAPI Specification. De definierar bas-URL, auth, concurrency, jobb- och outputlivscykel samt den formella endpointkartan. citeturn5view0turn35search13turn1search4

**Comfy Cloud-produkt och skillnader mot OSS**
Comfy Clouds officiella produktsida och FAQ är viktiga för Begränsningar, BYO-modeller, custom-node-stöd, GPU-typ och kommersiell modelllicens. De innehåller också två av de viktigaste officiella konflikterna som din dokumentation bör flagga. citeturn36view0

**ComfyUI kärndokumentation**
Server Overview, Messages, Routes, Workflow JSON-specifikationen och utvecklingsdokumentationen för custom nodes och subgraph blueprints. De behövs för att förklara hur frontend och server egentligen tänker om workflows, custom-node expose, WebSocket-events och grafserialisering. citeturn3search3turn1search7turn1search6turn8search0turn29view0turn8search12

**Officiell frontendkod**
ComfyUI_frontend är den mest auktoritativa referensen för `graphToPrompt`, `loadApiJson`, `app.queuePrompt`, `window.comfyAPI`-shim-lagret och hur gamla extensions fortsatt fungerar i Vite/TypeScript-världen. För API-format kontra graf-format är det här ofta viktigare än communitybloggar. citeturn27view0turn28view0turn29view0

**ComfyUI MCP Server**
Den officiella MCP-serverdokumentationen är central eftersom den redan visar hur Comfy själva översätter agentvärlden till Cloud: discovery tools, execution tools, output handling och kända begränsningar. Om ditt mål är en egen MCP-proxy är det här en referens du absolut ska citera, både för samma möjligheter och för samma begränsningar. citeturn4view0

**Claude Code**
Anthropics officiella docs för Skills, Commands, Features overview och Hooks behövs för att beskriva exakt hur din kunskap ska skeppas som en reusable skill, när en skill bör vara auto- eller manuellt invokerad, hur `allowed-tools` fungerar och varför supporting files är rätt mönster för stora referensmängder. citeturn32view0turn32view1turn32view2turn31search3

## Implementationschecklista

Det här är den praktiska checklistan jag skulle lägga in i ditt publika GitHub-repo som “definition of done” för en Comfy Cloud-skill och en MCP-proxy.

Dokumentera först **kärnendpoints**: `POST /api/prompt`, `GET /api/object_info`, `GET /api/features`, `GET /api/job/{job_id}/status`, `GET /api/jobs/{job_id}`, `GET /api/queue`, `POST /api/queue`, `POST /api/interrupt`, `GET /api/view`, `POST /api/upload/image`, `POST /api/upload/mask`, samt assets-lagret om du tänker stödja registrerade inputs och hash-dedupe. Förklara också att `/api/history_v2*` är bakåtkompatibelt men deprecated. citeturn1search4turn6search7

Dokumentera sedan **WebSocket-kontraktet**: URL-format, att `clientId` är forward-compat-only i Cloud, att filtrering måste ske på `prompt_id`, och att proxyklienten måste förstå både JSON-event och binära preview-frames. Lista åtminstone `execution_start`, `executing`, `progress`, `executed`, `execution_success`, `execution_error` och `status`. citeturn1search4turn1search7turn8search7

Lägg till en separat sida för **API-format kontra workflow-format** där du visar: nod-id-som-nycklar, `class_type`, `inputs`, `_meta.title`, länkformatet `["node_id", slot]`, och arraywrapping via `__value__`. Visa även hur `loadApiJson` fungerar åt andra hållet, så att skillen kan förklara conversion patterns för agenten. citeturn27view0turn28view0

Skapa en **capability detection playbook** som säger att proxyn alltid ska läsa `/api/object_info`, `/api/features` och `/api/experiment/models*` i stället för att anta att vissa node packs eller modeller finns. Lägg in ett tydligt avsnitt om att publik dokumentation inte ger fullständig liveinventering av Cloud. citeturn1search4turn6search0turn36view0

Lägg till en **limits and conflicts**-sida. Den ska uttryckligen nämna att officiella källor just nu är motsägelsefulla om BYO-modeller och om samtidighet kontra “one active job at a time”, så att skillen inte hallucinerar ett starkare kontrakt än Comfy själva erbjuder. citeturn36view0turn5view0

Bygg en **proxy-side normalization and hashing**-regel: normalisera API-format-JSON, inkludera seed, modell- och assetreferenser, hash det och använd det för dedupe, retry och reproducibility. Dokumentera att proxy-lagret är den säkra platsen för reproduktionsmetadata, särskilt eftersom MCP-genererade outputs saknar workflow metadata. citeturn4view0turn8search6

Skapa en **safety and guardrails**-sektion som täcker kreditbudget, samtidighetsbudget, batchgränser, filstorlek, bilddimensioner, blockering av icke-stödda nodes/modeller och content policy i proxyn. Var tydlig med att dessa regler ligger i ditt lager, inte i skilltexten ensam. citeturn5view0turn6search4

I själva `.claude/skills/`-strukturen skulle jag lägga:
`SKILL.md`, `endpoints-reference.md`, `workflow-format.md`, `orchestration.md`, `capabilities.md`, `limits-and-conflicts.md`, `examples/basic-txt2img-api.json`, `examples/chained-img2img-api.json`, `examples/asset-backed-workflow-api.json`. Anthropic rekommenderar uttryckligen denna uppdelning i stödjefiler när referensmaterialet är stort. citeturn34view4turn32view0

## Öppna frågor och begränsningar

Den största öppna frågan är att Comfy inte publicerar en enda, uttömmande livekatalog över exakt vilka node packs, checkpoints, VAEs, upscalers och LoRAs som för tillfället finns installerade i Cloud. Den officiella vägen är runtime-detektion via schema- och modelldiscovery, inte en statisk docslista. citeturn1search4turn36view0

Den näst största öppna frågan är **BYO-modeller**. Officiell marknadstext och FAQ säger inte samma sak. Därför bör din proxy i nuläget behandla CivitAI-LoRA som den säkraste officiellt stödda BYO-scenariot och allt bredare än så som “måste verifieras på det faktiska kontot”. citeturn36view0

Det finns också en **officiell samtidighetskonflikt**. Cloud FAQ säger att varje workflow kan köra upp till 60 minuter med ett aktivt jobb åt gången, medan Cloud API Overview säger att API-användare kan köra flera jobb parallellt – tre på Creator och fem på Pro – och att detta just nu gäller via API. Jag skulle implementera proxyn efter den mer specifika API-översikten men tydligt dokumentera konflikten. citeturn36view0turn5view0

Slutligen hittade jag inga publika, numeriska rate-limit-tal och ingen tydligt granskad officiell policytext för NSFW/moderation i det material som analyserades här. Om du vill exponera Comfy Cloud säkert till LLM-agenter behöver de två sakerna därför hanteras som **proxy policy**, inte som implicita plattformsgarantier. citeturn1search4turn5view0