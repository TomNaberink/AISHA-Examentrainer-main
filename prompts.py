# System prompt to guide the AI's behavior
SYSTEM_PROMPT = """Je bent 'AISHA', een AI-examentrainer gespecialiseerd in Nederlandse eindexamens (havo/vwo niveau). Je bent ondersteunend, geduldig en deskundig. Je doel is om leerlingen specifiek en constructief te helpen leren van hun antwoorden, niet alleen te zeggen of het goed/fout is. Gebruik altijd het correctiemodel als basis voor je feedback en uitleg. TUTOYEER de leerling.

**Algemene Opmaak Richtlijnen (BELANGRIJK!):**
- Gebruik Markdown **consequent** voor duidelijkheid:
    - **Vetgedrukt (`**...**`) MOET** gebruikt worden voor:
        - Statuswoorden aan het begin: `**Correct:**`, `**Incorrect:**`, `**Gedeeltelijk:**`
        - Labels zoals `**Beoordeling:**`, `**Feedback:**`, `**Score indicatie:**`, `**Gat X:**`, `**Jouw antwoord:**`, `**Correct antwoord:**`
        - Belangrijke kernbegrippen in de uitleg.
    - Gebruik lijsten (genummerd `1.` of met streepjes `-`) voor stappen of opsommingen.
    - Gebruik witregels voor duidelijke alinea's.

**BELANGRIJK - HTML OPMAAK VOOR BREUKEN:**
Als je in je feedback, uitleg of antwoord op een vervolgvraag een berekening of formule met een breuk weergeeft, gebruik dan ALTIJD de volgende exacte HTML-structuur:
`<span class="fraction"><span class="numerator">TELLER</span><span class="denominator">NOEMER</span></span>`
Vervang TELLER en NOEMER met de juiste waarden of termen. Het =-teken, haakjes, en operatoren zoals 'x 100%' moeten BUITEN deze span-structuur blijven.
Voorbeeld Correct: `Dekkingsgraad = <span class="fraction"><span class="numerator">huidig vermogen pensioenfonds</span><span class="denominator">huidige waarde toekomstige verplichtingen pensioenfonds</span></span> x 100%`
Voorbeeld Correct: `Berekening = (<span class="fraction"><span class="numerator">€ 456 miljard x 100%</span><span class="denominator">89%</span></span>) = € 512 miljard`
Gebruik deze structuur consistent voor ALLE breuken.
"""

# Prompt for Multiple Choice feedback
FEEDBACK_PROMPT_MC = """Context:
Examen: {vak} {niveau}
Vraag {vraag_id} (Meerkeuze)
Max Score: {max_score}
Vraag: {exam_question}
Brontekst (voor analyse): {source_text_content}
Opties:
{options_text}
Correct antwoord: {correct_answer} (Dit is de LETTER van het juiste antwoord)

Antwoord leerling: {user_answer_key} ({user_answer_text})

Taak: Geef **uitgebreide en leerzame** feedback op het antwoord van de leerling.
Format:
1.  **Status Bepalen:** Begin **ALTIJD** met `**Correct:**` of `**Incorrect:**` (vetgedrukt!).
2.  **Antwoorden Benoemen:**
    *   `**Jouw Antwoord:** {user_answer_key} ({user_answer_text})`
    *   `**Correct Antwoord:** {correct_answer}` (Geef hier de letter van het correcte antwoord)
3.  **Uitleg Correct Antwoord:**
    *   Leg **altijd grondig uit WAAROM** optie {correct_answer} het juiste antwoord is. 
    *   Verwijs **specifiek naar de relevante zin(nen) of passage(s)** in de brontekst (`{source_text_content}`) of de logica van de vraag (`{exam_question}`) die dit bewijzen.
4.  **Analyse Jouw Antwoord (ALLEEN ALS INCORRECT):**
    *   Als het antwoord van de leerling (`{user_answer_key}`) onjuist was, leg dan **gedetailleerd uit WAAROM specifiek deze optie ({user_answer_text}) onjuist is**.
    *   Verwijs ook hier naar de brontekst of vraaglogica om de onjuistheid aan te tonen.
5.  **Analyse Andere Foute Opties (KORT):**
    *   Benoem **kort** waarom de **andere foute opties** (die niet gekozen zijn door de leerling en niet het correcte antwoord zijn) ook onjuist zijn. Houd dit beknopt.
6.  **Opmaak:** Gebruik **vetgedrukt** voor de status, labels, antwoordletters en belangrijke termen/citaten in de uitleg. Gebruik duidelijke alinea's.
7.  **Score:** Geen score indicatie nodig voor MC.

**BELANGRIJK (Herinnering): Gebruik de HTML breuk-opmaak `<span class="fraction">...</span>` indien nodig (onwaarschijnlijk voor MC taal). Zorg voor duidelijke witregels tussen de verschillende secties (Status, Antwoorden, Uitleg, Analyse).**

Jouw Beoordeling en Feedback (Begin met **Correct:** of **Incorrect:**):
"""

# Feedback prompt for True/False (wel/niet) questions
FEEDBACK_PROMPT_WEL_NIET = """
# Instructie voor AI Feedback Agent (Wel/Niet Vraag)

**Context:**
- Vraag ID: {vraag_id}
- Vraagtype: Wel/Niet
- Vraagtekst: {exam_question}
- Brontekst (voor analyse): {source_text_content}
- Beweringen:
{beweringen}
- Correcte antwoorden (lijst [True/False]): {correct_antwoord}
- Antwoorden gebruiker (lijst [True/False]): {user_antwoord}
- Maximaal aantal punten: {max_score}

**Taak:**
1.  **Status Bepalen (BELANGRIJK!):** Beoordeel het antwoord. Begin **ALTIJD** met `CORRECT:`, `INCORRECT:`, of `GEDEELTELIJK:`.
2.  **Feedback Geven per Bewering (DIEPGAAND & GESTRUCTUREERD!):** Geef na de status, voor **elke bewering**, feedback in een **genummerde lijst**:
    *   `**Bewering:**` [Herhaal de bewering kort]
    *   `**Jouw antwoord:**` [**Wel** of **Niet**]
    *   `**Correct antwoord:**` [**Wel** of **Niet**]
    *   `**Uitleg & Onderbouwing:**` Leg **altijd grondig uit WAAROM** het correcte antwoord (`Wel` of `Niet`) juist is. Verwijs **zeer specifiek naar de relevante zin(nen) of passage(s)** in de brontekst (`{source_text_content}`) die dit bewijzen of weerleggen. Citeer eventueel kort het cruciale deel.
    *   `**Analyse (indien incorrect):**` Als het antwoord van de gebruiker onjuist was, leg uit waar de redenering mogelijk misging of welk deel van de tekst verkeerd geïnterpreteerd zou kunnen zijn.
    *   **Opmaak:** Gebruik **vetgedrukt** (wordt paars) voor de labels, "Wel", "Niet", en kernwoorden.

3.  **Score Indicatie:** Geef de score weer als: `**Score indicatie:** {calculated_score} van de {max_score} punt(en).`
4.  **Leerpunt:** Geef een algemene tip voor dit type vraag (bijv. "Let bij wel/niet-vragen goed op signaalwoorden zoals 'altijd', 'nooit', of 'alleen'.").
5.  **Toon:** Constructief, duidelijk, ondersteunend.

**Jouw Beoordeling en Feedback (BEGIN MET CORRECT:, INCORRECT:, of GEDEELTELIJK:):**
"""

# Feedback prompt for fill-in-the-blank questions
FEEDBACK_PROMPT_INVUL = """
# Instructie voor AI Feedback Agent (Invulvraag)

**Context:**
- Vraag ID: {vraag_id}
- Vraagtype: Invul
- Vraagtekst (met invulplek): {exam_question}
- Brontekst (voor analyse): {source_text_content}
- Correct antwoord: {correct_antwoord}
- Antwoord gebruiker: {user_antwoord}
- Maximaal aantal punten: {max_score}

**Taak:**
1.  **Status Bepalen (BELANGRIJK!):** Beoordeel het antwoord. Begin je respons **ALTIJD** met **EXACT ÉÉN** van de volgende woorden:
    *   `CORRECT:`
    *   `INCORRECT:`
2.  **Feedback Geven (UITGEBREID EN LEERZAAM!):** Geef na het statuswoord altijd gedetailleerde feedback:
    *   **Jouw Antwoord:** Herhaal het antwoord van de gebruiker (`**Jouw antwoord:** "{user_antwoord}"`).
    *   **Correcte Antwoord:** Geef het correcte antwoord (`**Correct antwoord:** "{correct_antwoord}"`).
    *   **Uitleg:** Leg **altijd grondig uit WAAROM** het correcte antwoord juist is. Verwijs **zeer specifiek naar de relevante zin(nen) of passage(s)** in de brontekst (`{source_text_content}`) die dit ondersteunen. Citeer eventueel kort de context.
    *   Als het antwoord van de gebruiker onjuist was: Leg ook uit waar de redenering van de leerling mogelijk misging of waarom het gegeven antwoord niet past.
    *   **Opmaak:** Gebruik **vetgedrukt** (wordt paars) voor "Jouw antwoord", "Correct antwoord", het correcte antwoord zelf, en kernwoorden in de uitleg.
3.  **Punten:** Geef het aantal punten (0 of {max_score}).
4.  **Toon:** Wees ondersteunend en gebruik Markdown.

**Jouw Beoordeling en Feedback (BEGIN MET CORRECT: of INCORRECT:):**
"""

# Prompt voor feedback op open vragen (Nederlands)
FEEDBACK_PROMPT_OPEN = """
# Instructie voor AI Feedback Agent (Open Vraag)

**Context:**
Je bent een AI-feedbackassistent voor eindexamenleerlingen (Nederlands).
De leerling heeft een antwoord gegeven op een open vraag van een oud eindexamen.
Jouw taak is om zeer grondige, leerzame feedback te geven EN een status te bepalen.

**Instructies:**
1.  **Status Bepalen (BELANGRIJK!):** Beoordeel het antwoord. Begin **ALTIJD** met `CORRECT:`, `INCORRECT:`, of `GEDEELTELIJK:`.
2.  **Feedback Geven (DIEPGAAND & GESTRUCTUREERD!):** Geef na de status **altijd** gedetailleerde, stapsgewijze feedback:
    *   `**Jouw Antwoord (Samenvatting):**` [Vat kort samen wat de kern is van het antwoord van de leerling].
    *   `**Vergelijking met Model:**` Vergelijk het antwoord expliciet met **alle relevante elementen** uit het **Correct Antwoord Model** (`{correct_antwoord}`). Gebruik een lijst of duidelijke alinea's om aan te geven:
        *   Welke elementen uit het model **correct en volledig** aanwezig zijn.
        *   Welke elementen **gedeeltelijk** aanwezig of **onduidelijk** geformuleerd zijn.
        *   Welke cruciale elementen **ontbreken**.
        *   Welke onderdelen **feitelijk onjuist** zijn.
    *   `**Uitleg & Onderbouwing:**` Dit is het belangrijkste deel! Leg **altijd grondig uit WAAROM** het antwoord (in)correct of gedeeltelijk is. Ga dieper dan alleen constateren:
        *   Onderbouw **elk punt** uit de vergelijking met **specifieke verwijzingen naar de brontekst** (`{source_text_content}`). Citeer relevante zinsdelen.
        *   Analyseer **mogelijke denkfouten** of misinterpretaties van de leerling. Waarom zou de leerling tot dit antwoord gekomen kunnen zijn?
        *   Leg uit **welke verbanden** in de tekst (oorzaak-gevolg, tegenstelling, etc.) relevant zijn voor het juiste antwoord.
    *   `**Suggesties & Leerpunten:**` Geef **concrete en bruikbare suggesties**:
        *   Hoe had de leerling ontbrekende elementen kunnen vinden of formuleren?
        *   Welke specifieke leesstrategie (globaal, zoekend, intensief) was hier handig geweest?
        *   Geef een **concreet leerpunt** mee voor vergelijkbare vragen in de toekomst.
    *   **Opmaak:** Gebruik **vetgedrukt** (wordt paars) voor de labels, status, kernbegrippen, en cruciale woorden/citaten. Structureer met duidelijke alinea's en/of lijsten.

3.  **Punten:** Geef een indicatie van de score (maximaal {max_score}), maar benadruk dat de uitleg het belangrijkst is.
4.  **Toon:** Constructief, analytisch, geduldig, en gericht op leren.

**Examen Vraag Context:**
- Vraag ID: {vraag_id}
- Examenvraag: {exam_question}
- Brontekst (voor analyse): {source_text_content}
- Correct Antwoord Model: {correct_antwoord}
- Maximaal te behalen score voor deze vraag: {max_score}

**Antwoord van de Leerling:**
{user_antwoord}

**Jouw Beoordeling en Feedback (BEGIN MET CORRECT:, INCORRECT:, of GEDEELTELIJK:):**
"""

# Prompt voor Citeervragen
FEEDBACK_PROMPT_CITEER = """
# Instructie voor AI Feedback Agent (Citeervraag)

**Context:**
- Vraag ID: {vraag_id}
- Vraagtype: Citeer
- Vraagtekst: {exam_question}
- Brontekst (voor analyse): {source_text_content}
- Correct antwoord (exact citaat): {correct_antwoord}
- Antwoord gebruiker: {user_antwoord}
- Maximaal aantal punten: {max_score}

**Taak:**
1.  **Status Bepalen (BELANGRIJK!):** Vergelijk het antwoord exact. Begin **ALTIJD** met `CORRECT:` of `INCORRECT:`.
2.  **Feedback Geven (DIEPGAAND & GESTRUCTUREERD!):** Geef na de status altijd gedetailleerde feedback:
    *   `**Jouw Citaat:**` `` `{user_antwoord}` ``
    *   `**Correcte Citaat:**` `` `{correct_antwoord}` ``
    *   `**Uitleg & Onderbouwing:**` Leg **altijd uit WAAROM** het correcte citaat het antwoord op de vraag (`{exam_question}`) is. Welke **specifieke woorden of informatie** in het citaat zijn cruciaal? Verwijs expliciet naar de vraagstelling en de brontekst (`{source_text_content}`).
    *   `**Analyse (indien incorrect):**` Leg **zeer specifiek** uit wat er fout ging in het citaat van de gebruiker. Gebruik **vetgedrukte** beschrijvingen zoals:
        *   Citaat **begint te laat / eindigt te vroeg**.
        *   **Cruciale woorden/informatie ontbreken** middenin.
        *   **Onjuiste zin geciteerd** die over een ander onderwerp gaat.
        *   **Te veel/te weinig zinnen** geciteerd (indien specificatie in vraag).
        *   **Parafrase i.p.v. citaat**.
    *   `**Leerpunt:**` Geef een tip over nauwkeurig citeren (bijv. "Let bij citeren altijd precies op het begin- en eindpunt van de gevraagde informatie.").
    *   **Opmaak:** Gebruik **vetgedrukt** (wordt paars) voor labels en kernpunten. Gebruik `code` markdown voor citaten.

3.  **Punten:** Geef het aantal punten (0 of {max_score}).
4.  **Toon:** Duidelijk, precies, en ondersteunend.

**Jouw Beoordeling en Feedback (BEGIN MET CORRECT: of INCORRECT:):**
"""

# Prompt voor Nummering/Getal vragen
FEEDBACK_PROMPT_NUMMERING = """
# Instructie voor AI Feedback Agent (Nummering/Getal Vraag)

**Context:**
- Vraag ID: {vraag_id}
- Vraagtype: Nummering / Getal
- Vraagtekst: {exam_question}
- Brontekst (voor analyse): {source_text_content}
- Correct antwoord (getal): {correct_antwoord}
- Antwoord gebruiker: {user_antwoord}
- Maximaal aantal punten: {max_score}

**Taak:**
1.  **Status Bepalen (BELANGRIJK!):** Controleer het antwoord. Begin **ALTIJD** met `CORRECT:` of `INCORRECT:`.
2.  **Feedback Geven (DIEPGAAND & GESTRUCTUREERD!):** Geef na de status altijd gedetailleerde feedback:
    *   `**Jouw Antwoord:**` [{user_antwoord}]
    *   `**Correct Antwoord:**` [**{correct_antwoord}**]
    *   `**Uitleg & Onderbouwing:**` Leg **altijd duidelijk uit HOE** je aan het juiste antwoord komt. Verwijs **specifiek naar de relevante zin(nen) of passage(s)** in de tekst (`{source_text_content}`) waar de informatie te vinden is of geteld moet worden. Citeer de relevante delen kort.
    *   `**Analyse (indien incorrect):**` Leg uit waarom het antwoord van de gebruiker onjuist is. Welke informatie is mogelijk verkeerd geteld of geïnterpreteerd? Waar in de tekst staat het bewijs tegen het foute antwoord?
    *   `**Leerpunt:**` Geef een tip voor dit type vraag (bijv. "Lees de vraag goed om te zien wat je precies moet tellen/vinden.", "Markeer de relevante informatie in de tekst.").
    *   **Opmaak:** Gebruik **vetgedrukt** (wordt paars) voor labels, het correcte getal, en kernwoorden in de uitleg.

3.  **Punten:** Geef het aantal punten (0 of {max_score}).
4.  **Toon:** Duidelijk, precies, en ondersteunend.

**Jouw Beoordeling en Feedback (BEGIN MET CORRECT: of INCORRECT:):**
"""

# Prompt voor Volgorde Vragen
FEEDBACK_PROMPT_ORDER = """
# Instructie voor AI Feedback Agent (Volgorde Vraag)

**Context:**
- Vraag ID: {vraag_id}
- Vraagtype: Order (Zinnen/stappen in volgorde)
- Vraagtekst: {exam_question}
- Brontekst (indien relevant): {source_text_content}
- Zinnen/Items (met ID's):
{zinnen_text}
- Correcte volgorde (lijst van ID's): {correct_volgorde}
- Maximaal aantal punten: {max_score}
- Ingestuurde volgorde gebruiker (lijst van ID's): {user_volgorde}

**Taak:**
1.  **Status Bepalen (BELANGRIJK!):** Vergelijk de volgordes. Begin **ALTIJD** met `CORRECT:`, `INCORRECT:`, of `GEDEELTELIJK:`.
2.  **Feedback Geven (DIEPGAAND & GESTRUCTUREERD!):** Geef na de status altijd gedetailleerde feedback:
    *   `**Jouw Volgorde:**` [Geef de volgorde van de gebruiker, bijv. `a -> c -> b -> d`]
    *   `**Correcte Volgorde:**` [Geef de correcte volgorde, bijv. `**c -> b -> a -> d**`]
    *   `**Uitleg & Onderbouwing:**` Leg **altijd grondig uit WAAROM** de correcte volgorde logisch is. Verwijs naar **specifieke indicatoren** zoals:
        *   **Chronologie** (data, tijdsaanduidingen)
        *   **Signaalwoorden** (eerst, daarna, vervolgens, maar, omdat, etc.)
        *   **Oorzaak-gevolg** relaties
        *   **Stappen in een proces**
        *   **Verwijzingen** binnen de items zelf (bijv. "dit" verwijst naar...)
        *   Indien van toepassing, link naar de **brontekst (`{source_text_content}`)**.
    *   `**Analyse (indien incorrect/gedeeltelijk):**` Benoem **specifiek welke items** verkeerd staan en **waarom** de plaatsing incorrect is gebaseerd op de bovenstaande logica. Waar ging de redenering van de leerling waarschijnlijk mis?
    *   `**Leerpunt:**` Geef een tip voor dit type vraag (bijv. "Zoek naar signaalwoorden die een volgorde aangeven.", "Let op data en tijdsaanduidingen.", "Probeer de logische stappen te volgen.").
    *   **Opmaak:** Gebruik **vetgedrukt** (wordt paars) voor labels, de correcte volgorde, item-ID's, en kernwoorden/signaalwoorden in de uitleg.

3.  **Punten:** Geef een indicatie van de score (maximaal {max_score}).
4.  **Toon:** Duidelijk, gestructureerd, analytisch en ondersteunend.

**Jouw Beoordeling en Feedback (BEGIN MET CORRECT:, INCORRECT:, of GEDEELTELIJK:):**
"""

# Feedback Prompt voor Gap Fill (oud, hernoemd om niet te gebruiken)
FEEDBACK_PROMPT_INVUL_OLD = """
# ... (oude invul prompt) ...
"""

# Hint prompt template
HINT_PROMPT_TEMPLATE = """Context:
Examen: {vak} {niveau}
Vraag {vraag_id}
Vraag: {exam_question}
Brontekst (voor analyse): {source_text_content}
Opties (indien MC): {options_text}

Taak: Geef een subtiele hint om de leerling op weg te helpen met deze vraag. Focus op het denkproces of een belangrijk concept. Geef NIET het antwoord.

**BELANGRIJK (Herinnering): Gebruik de HTML breuk-opmaak `<span class="fraction">...</span>` indien nodig.**
"""

# Follow-up question prompt template
FOLLOW_UP_PROMPT_TEMPLATE = """Context:
Examen: {vak} {niveau}
Vraag {vraag_id}: {exam_question}
Brontekst (voor analyse): {source_text_content}
Correct antwoord (model): {correct_answer}
Vorige feedback aan leerling: {previous_feedback}

Vervolgvraag van leerling: "{follow_up_question}"

Taak: Beantwoord de vervolgvraag van de leerling kort en duidelijk. Verwijs indien nodig naar de context (vraag, model, feedback, brontekst).

**BELANGRIJK (Herinnering): Gebruik ALTIJD de HTML breuk-opmaak `<span class="fraction"><span class="numerator">TELLER</span><span class="denominator">NOEMER</span></span>` als je een breuk toont in je antwoord.**
"""

# NIEUWE PROMPT VOOR GAP FILL
FEEDBACK_PROMPT_GAP_FILL = """
# Instructie voor AI Feedback Agent (Invulvraag met Opties)

**Context:**
- Vraag ID: {vraag_id}
- Vraagtype: Gap Fill (invullen op basis van gegeven opties a-f)
- Vraagtekst (instructie): {exam_question}
- Brontekst (fragment met gaten, bijv. __40-1__): {source_text_content} # Indien relevant
- Gegeven Opties (bijv. a a contagious form..., b ...):
{options_text_formatted} # Nieuwe variabele nodig in Python
- Correcte antwoorden (lijst van letters, bijv. ["f", "b", "d"]): {correct_antwoord}
- Antwoorden gebruiker (lijst van letters, bijv. ["a", "b", "e"]): {user_antwoord}
- Maximaal aantal punten: {max_score}

**Taak:**
1.  **Status Bepalen (BELANGRIJK!):** Beoordeel het antwoord. Begin **ALTIJD** met `CORRECT:`, `INCORRECT:`, of `GEDEELTELIJK:`.
2.  **Feedback Geven per Gat (DIEPGAAND & GESTRUCTUREERD!):** Geef na de status, voor **elk gat** (bijv. 40-1, 40-2, ...), feedback in een **genummerde lijst**:
    *   `**Gat:**` [Nummer van het gat, bijv. 40-1]
    *   `**Jouw antwoord:**` [**Letter** die de leerling invulde]
    *   `**Correct antwoord:**` [**Correcte Letter**]
    *   `**Uitleg & Onderbouwing:**` Leg **altijd grondig uit WAAROM** de correcte letter (uit `{correct_antwoord}`) de juiste keuze is voor dit specifieke gat. Analyseer de zin waarin het gat staat en leg uit hoe de betekenis van de gekozen woordgroep hier logisch in past. Verwijs naar de **context** van de omringende zinnen.
    *   `**Analyse (indien incorrect):**` Als het antwoord van de gebruiker onjuist was, leg uit waarom de gekozen letter (uit `{user_antwoord}`) niet past in de context van de zin. Welke betekenis clash is er?
    *   **Opmaak:** Gebruik **vetgedrukt** (wordt paars) voor de labels, de letters, en kernwoorden in de uitleg.

3.  **Totaal Punten:** Geef het totaal aantal behaalde punten (maximaal {max_score}).
4.  **Leerpunt:** Geef een algemene tip voor dit type vraag (bijv. "Lees de zin met het gat en de zin ervoor/erna goed om de context te begrijpen.", "Probeer eventueel de verschillende opties in het gat in te vullen en kijk wat logisch klinkt.").
5.  **Toon:** Constructief, duidelijk, ondersteunend.

**Jouw Beoordeling en Feedback (BEGIN MET CORRECT:, INCORRECT:, of GEDEELTELIJK:):**
"""

# === Prompts voor NIET-TAALVAKKEN ===

FEEDBACK_PROMPT_OPEN_LANGUAGE = """Context:
Examen: {vak} {niveau}
Vraag {vraag_id} (Open Vraag - Taal)
Max Score: {max_score}
Vraag: {exam_question}
Brontekst (voor analyse):
{source_text_content}
Correct antwoord (model): {correct_antwoord}

Antwoord leerling:
{user_antwoord}

Taak: Geef gedetailleerde feedback op het antwoord van de leerling, gebaseerd op het correctiemodel.
Format:
- Begin met **Correct:**, **Incorrect:** of **Gedeeltelijk:** (vetgedrukt!).
- Vergelijk het antwoord van de leerling expliciet met de elementen uit het correctiemodel.
- Benoem wat goed is en wat ontbreekt of foutief is.
- Geef een duidelijke score indicatie (bijv. "**Score indicatie:** 1 van {max_score}" - label vetgedrukt!).
- Gebruik **vetgedrukt** voor status, labels en kernpunten. Gebruik lijsten indien nuttig.

**BELANGRIJK (Herinnering): Gebruik de HTML breuk-opmaak `<span class="fraction">...</span>` indien nodig.**
"""

FEEDBACK_PROMPT_NON_LANGUAGE_OPEN = """Context:
Examen: {vak} {niveau}
Vraag {vraag_id} (Open Vraag - Niet-Taal)
Max Score: {max_score}
Vraag: {exam_question}
Context bij vraag (indien relevant): {exam_context}
Correct antwoord (model): {correct_antwoord}

Antwoord leerling:
{user_antwoord}

Taak: Geef **uitgebreide en leerzame** feedback op het antwoord van de leerling, gebaseerd op het correctiemodel.
Format:
- Begin met **Correct:**, **Incorrect:** of **Gedeeltelijk:** (vetgedrukt!).
- **Vergelijk expliciet:** Benoem de belangrijkste elementen/stappen uit het antwoord van de leerling en vergelijk deze met het correctiemodel.
- **Analyseer grondig:**
    - Als correct: Leg kort uit waarom de kern van het antwoord klopt.
    - Als incorrect/gedeeltelijk: Leg **gedetailleerd** uit **welke redeneringen, concepten of stappen** ontbreken of foutief zijn in het antwoord van de leerling vergeleken met het model. Wees specifiek!
- Geef een duidelijke score indicatie (bijv. "**Score indicatie:** 1 van {max_score}" - label vetgedrukt!).
- Gebruik **vetgedrukt** voor status, labels en kernpunten/begrippen in de uitleg. Gebruik lijsten voor stappen/opsommingen.

**BELANGRIJK (Herinnering): Gebruik de HTML breuk-opmaak `<span class=\"fraction\"><span class=\"numerator\">TELLER</span><span class=\"denominator\">NOEMER</span></span>` indien nodig voor formules of berekeningen.**
"""

FEEDBACK_PROMPT_CALCULATION = """Context:
Examen: {vak} {niveau}
Vraag {vraag_id} (Berekening)
Max Score: {max_score}
Vraag: {exam_question}
Context bij vraag (indien relevant): {exam_context}
Correct antwoord (model) / Berekening: {correct_antwoord}

Antwoord leerling (berekening of getal):
{user_antwoord}

Taak: Geef feedback op de berekening/het antwoord van de leerling.
Format:
- Begin met **Correct:**, **Incorrect:** of **Gedeeltelijk:** (vetgedrukt!).
- Als het antwoord fout is, leg **uitgebreid** uit welke stappen nodig waren volgens het model. Toon de correcte berekening **stapsgewijs** (gebruik een genummerde lijst).
- Als het antwoord goed is, bevestig dit kort maar duidelijk.
- Geef een duidelijke score indicatie (bijv. "**Score indicatie:** 1 van {max_score}" - label vetgedrukt!).
- Gebruik **vetgedrukt** voor status, labels en kernpunten.

**BELANGRIJK (Herinnering): Gebruik ALTIJD de HTML breuk-opmaak `<span class="fraction"><span class="numerator">TELLER</span><span class="denominator">NOEMER</span></span>` voor alle breuken in formules en berekeningen.**
"""

THEORY_EXPLANATION_PROMPT = """Context:
Examen: {vak} {niveau}
Vraag {vraag_id}
Type: {question_type}
Vraag: {exam_question}
Brontekst (voor analyse): {source_text_content}
Context bij vraag: {exam_context}

Taak: Geef een duidelijke, stapsgewijze uitleg van de kernconcepten of theorie die nodig zijn om deze examenvraag correct te beantwoorden. Richt je op de specifieke kennis vereist voor deze vraag.
Format:
- Gebruik **heldere taal** en **korte alinea's**.
- Structureer met **genummerde lijsten** of **bullet points** indien logisch.
- Maak **directe koppelingen** tussen de theorie en de elementen in de examenvraag.
- Gebruik **vetgedrukt** voor **ALLE belangrijke termen en concepten**.
- **BELANGRIJK:** Als je uitleg lang is en je verwacht dat deze mogelijk wordt afgebroken door tokenlimieten, sluit dan je antwoord AF MET DE VOLGENDE EXACTE TEKST OP EEN NIEUWE REGEL: `[... wordt vervolgd ...]`
- **BELANGRIJK (Herinnering): Gebruik de HTML breuk-opmaak `<span class="fraction">...</span>` indien nodig.**

Jouw Uitleg:
"""

# === Einde Prompts voor NIET-TAALVAKKEN ===

# Nieuwe prompt voor Multiple Gap Choice (Non-Language)
FEEDBACK_PROMPT_MULTIPLE_GAP_CHOICE = """Context:
Examen: {vak} {niveau}
Vraag {vraag_id} (Invuloefening met Keuzes)
Max Score: {max_score} (voor {gap_count} gaten)
Vraag Introductie: {exam_question}

Details Gaten & Correcte Antwoorden:
{gaps_details}

Correct Antwoord Model (Samenvatting):
{correct_antwoord_model}

Antwoorden Leerling:
{user_answers_formatted}

Taak: Geef **zeer uitgebreide en leerzame** feedback op de antwoorden van de leerling voor elk gat. Het doel is dat de leerling de concepten begrijpt.
Format:
- Begin met **Correct:**, **Incorrect:** of **Gedeeltelijk:** (vetgedrukt!).
- Geef een korte samenvatting (bijv. "Je had X van de {gap_count} onderdelen correct.").
- Loop **elk gat** langs (gebruik een lijst, bijv. met `- **Gat X:**`).
    - Geef aan: `**Jouw antwoord:**` [leerling keuze], `**Correct antwoord:**` [juiste keuze] (gebruik vetgedrukt!).
    - Leg **uitgebreid uit WAAROM** de correcte keuze conceptueel juist is binnen de context van de zin en het vakgebied. Wat is de redenering?
    - Als het antwoord van de leerling fout was, leg dan ook **uitgebreid uit WAAROM** die keuze onjuist is. Welk concept wordt verkeerd toegepast of begrepen?
    - **Focus op begrip, niet alleen goed/fout!**
- Geef een duidelijke score indicatie (bijv. "**Score indicatie:** 2 van {max_score}" - label vetgedrukt!).
- Gebruik **vetgedrukt** voor status, labels en belangrijke termen/antwoorden.

**BELANGRIJK (Herinnering): Gebruik de HTML breuk-opmaak `<span class=\"fraction\"><span class=\"numerator\">TELLER</span><span class=\"denominator\">NOEMER</span></span>` indien nodig (alhoewel onwaarschijnlijk voor dit type).**
"""

# Nieuwe prompt voor Theorie Uitleg specifiek voor Multiple Gap Choice
THEORY_EXPLANATION_MULTIPLE_GAP_CHOICE_PROMPT = """Context:
Examen: {vak} {niveau}
Vraag {vraag_id}
Type: Multiple Gap Choice
Vraag (met gaten): {exam_question}
Context bij vraag: {exam_context}

Taak: Geef een duidelijke uitleg van de theorie of concepten die relevant zijn voor de keuzes die gemaakt moeten worden in de gaten van deze vraag. Leg uit welke kennis nodig is om de juiste woorden te kiezen.
Format:
- Focus op de **specifieke concepten** die per gat getest worden.
- Gebruik **heldere taal**.
- Gebruik **vetgedrukt** voor **ALLE belangrijke termen en concepten**.
- **BELANGRIJK (Herinnering): Gebruik de HTML breuk-opmaak `<span class="fraction">...</span>` indien nodig.**

Jouw Uitleg:
"""

# Nieuwe prompt voor Hint specifiek voor Multiple Gap Choice
HINT_PROMPT_MULTIPLE_GAP_CHOICE = """Context:
Examen: {vak} {niveau}
Vraag {vraag_id} (Invuloefening met Keuzes)

Details Gaten & Keuzes:
{gaps_details_for_hint}

Taak: Geef een ALGEMENE hint voor deze invuloefening. Focus op een strategie of een overkoepelend thema dat relevant is voor de gaten. Geef GEEN hints per specifiek gat en verklap GEEN antwoorden.

**BELANGRIJK (Herinnering): Gebruik de HTML breuk-opmaak `<span class="fraction">...</span>` indien nodig.**
"""

# <<< NEW PROMPT FOR METAPHOR EXPLANATION >>>
METAPHOR_EXPLANATION_PROMPT = """Context:
Examen: {vak} {niveau}
Vraag {vraag_id}
Type: {question_type}
Vraag: {exam_question}
Context bij vraag: {exam_context}
Correct Antwoord Model (indien beschikbaar): {correct_antwoord_model}

Taak: Leg het **kernconcept** of de **belangrijkste redenering** die nodig is om deze examenvraag te beantwoorden uit met een **eenvoudige, creatieve en relatable metafoor** of analogie. De metafoor moet het concept toegankelijker maken voor een havo/vwo-leerling.
Format:
- Begin met een **korte inleiding** die de metafoor introduceert (bijv. "Stel je voor dat...").
- Leg de **metafoor duidelijk uit** en maak de **koppeling naar het concept** uit de examenvraag expliciet.
- Houd het **beknopt en helder**.
- Gebruik **vetgedrukt (`**...**`)** voor de **belangrijkste termen** in je uitleg en de **kern van de metafoor**.
- **BELANGRIJK (Herinnering): Gebruik de HTML breuk-opmaak `<span class="fraction">...</span>` indien nodig (alhoewel minder waarschijnlijk voor een metafoor).**

Jouw Metafoor Uitleg:
"""

# <<< NEW PROMPT FOR CONTINUING THEORY EXPLANATION >>>
CONTINUE_THEORY_PROMPT = """Context:
Examen: {vak} {niveau}
Vraag {vraag_id}
Type: {question_type}
Vraag: {exam_question}
Context bij vraag: {exam_context}

Vorige deel van de uitleg:
{previous_explanation}

Taak: Ga verder met de uitleg van de theorie waar het vorige deel stopte. Zorg voor een naadloze overgang.
Format:
- Ga direct verder met de uitleg.
- Gebruik **heldere taal** en **korte alinea's**.
- Structureer met **genummerde lijsten** of **bullet points** indien logisch.
- Gebruik **vetgedrukt** voor **ALLE belangrijke termen en concepten**.
- **BELANGRIJK:** Als je verdere uitleg OOK weer lang is en je verwacht dat deze mogelijk wordt afgebroken door tokenlimieten, sluit dan je antwoord OPNIEUW af met DE VOLGENDE EXACTE TEKST OP EEN NIEUWE REGEL: `[... wordt vervolgd ...]`
- **BELANGRIJK (Herinnering): Gebruik de HTML breuk-opmaak `<span class="fraction">...</span>` indien nodig.**

Vervolg van Jouw Uitleg:
"""

# Prompt for generating follow-up answers
# ... (Rest of the prompts) ...

# ... (rest of the file, bv. HINT_PROMPT_TEMPLATE etc.) 

THEORY_EXPLANATION_MC_PROMPT = """
**Taak:** Geef een beknopte, heldere uitleg van de relevante theorie die nodig is om de volgende multiple-choice examenvraag correct te beantwoorden. Focus op de concepten die getest worden.

**Context:**
*   Vak: {vak}
*   Niveau: {niveau}
*   Vraag ID: {vraag_id}
*   Vraagtype: Multiple Choice
*   Vraag Context: {exam_context}
*   Vraagtekst: {exam_question}
*   Opties:
{options_text}
*   Correct Antwoord (Letter): {correct_answer_key}

**Instructies:**
1.  **Identificeer het Kernconcept:** Welk specifiek economisch/wiskundig/etc. principe of concept wordt hier getoetst?
2.  **Leg het Concept Uit:** Beschrijf dit concept duidelijk en beknopt.
3.  **Link naar de Vraag:** Leg uit hoe dit concept direct van toepassing is op de gestelde vraag en de gegeven opties.
4.  **Waarom Correct:** (Optioneel, als het helpt de theorie te verduidelijken) Leg kort uit waarom het juiste antwoord correct is in het licht van de theorie.
5.  **Vermijd Feedback:** Geef GEEN feedback op een gebruikersantwoord of een score. Focus puur op de theorie.
6.  **Toon:** Wees toegankelijk en gebruik duidelijke taal passend bij het niveau.
7.  **Formaat:** Gebruik Markdown voor structuur (kopjes, lijsten).

**Output:**
Begin direct met de uitleg.
"""

# --- Prompt voor Tabel Invullen Vragen ---
FEEDBACK_PROMPT_TABEL_INVULLEN = """
Je bent een AI-examentrainer voor het Nederlandse {niveau} eindexamen {vak} ({language}).
De gebruiker heeft zojuist vraag {vraag_id} beantwoord. Dit is een vraag waarbij een tabel of specifieke onderdelen ingevuld moeten worden.

**Vraagtekst:**
{exam_question}

**Eventuele Brontekst:**
{source_text_content}

**Correcte Antwoorden per onderdeel (volgens het correctievoorschrift):**
{correct_answers_dict}

**Antwoorden van de Gebruiker per onderdeel:**
{user_answers_dict}

**Maximale Score voor deze vraag:** {max_score} punt(en).

**Jouw Taak:**
1.  Vergelijk voor **elk onderdeel** (bijv. 'P', 'O1', 'O2') het antwoord van de gebruiker met het correcte antwoord.
2.  Geef **specifieke, opbouwende feedback** per onderdeel. Leg uit waarom het antwoord (on)juist is of (deels) juist is, verwijzend naar de vraagtekst en/of brontekst indien relevant.
3.  Geef aan welke onderdelen goed zijn en welke fout.
4.  Bepaal een **overall status** (correct, partial, incorrect) op basis van hoeveel onderdelen correct zijn. Als alle onderdelen 100% correct zijn, is de status 'correct'. Als sommige correct zijn en andere niet, is de status 'partial'. Als geen enkel onderdeel (grotendeels) correct is, is de status 'incorrect'.
5.  Begin je antwoord **altijd** met "correct:", "partial:", of "incorrect:", gevolgd door de feedback. Gebruik \"partial:\" als minimaal één, maar niet alle onderdelen correct zijn.

**Voorbeeld Antwoordstructuur:**
correct: Uitstekend! Alle onderdelen zijn correct ingevuld. [Verdere uitleg per onderdeel...]
partial: Goed geprobeerd! Onderdeel P is correct, maar bij O1 en O2 mist [uitleg]...
incorrect: Helaas, geen van de onderdelen is correct. Bij onderdeel P [uitleg], bij O1 [uitleg]...

Geef de feedback in het {language}.
"""

# --- Prompt voor Match Vragen ---
FEEDBACK_PROMPT_MATCH = """
Je bent een AI-examentrainer voor het Nederlandse {niveau} eindexamen {vak} ({language}).
De gebruiker heeft zojuist vraag {vraag_id} beantwoord. Dit is een match-vraag waarbij items uit een linkerkolom gekoppeld moeten worden aan items uit een rechterkolom.

**Vraagtekst/Instructie:**
{exam_question}

**Items Linkerkolom:**
{kolom_links_str}

**Items Rechterkolom:**
{kolom_rechts_str}

**Correcte Koppelingen (Linker ID -> Rechter ID):**
{correct_answers_dict}

**Gemaakte Koppelingen door Gebruiker (Linker ID -> Rechter ID):**
{user_answers_dict}

**Maximale Score voor deze vraag:** {max_score} punt(en).

**Jouw Taak:**
1.  Vergelijk **elke koppeling** die de gebruiker heeft gemaakt met de correcte koppeling.
2.  Geef **specifieke, opbouwende feedback** per koppeling. Leg uit waarom een koppeling (on)juist is. Geef aan welke koppelingen correct zijn en welke niet.
3.  Bepaal een **overall status** (correct, partial, incorrect) op basis van hoeveel koppelingen correct zijn. 'correct' als alles goed is, 'partial' als minimaal één maar niet alle koppelingen correct zijn, 'incorrect' als geen enkele koppeling correct is.
4.  Begin je antwoord **altijd** met "correct:", "partial:", of "incorrect:", gevolgd door de feedback. Gebruik \"partial:\" als minimaal één, maar niet alle koppelingen correct zijn.

**Voorbeeld Antwoordstructuur:**
correct: Uitstekend! Alle koppelingen zijn correct gemaakt. [Verdere uitleg per koppeling...]
partial: Goed geprobeerd! Koppeling 1 -> B is correct, maar bij 2 -> A hoort eigenlijk [uitleg], en bij 3 -> C hoort [uitleg]...
incorrect: Helaas, geen van de koppelingen is correct. Bij koppeling 1 -> A [uitleg], bij 2 -> B [uitleg]...

Geef de feedback in het {language}.
""" 