from flask import Blueprint, render_template, request, jsonify, redirect, url_for
import os
import google.generativeai as genai
import datetime # Importeer datetime
from utils.data_loader import list_available_exams, get_question_data, get_max_question_id
# Importeer alleen de prompts relevant voor taalvakken
from prompts import (
    SYSTEM_PROMPT,
    FEEDBACK_PROMPT_MC,
    FEEDBACK_PROMPT_WEL_NIET,
    FEEDBACK_PROMPT_INVUL,
    FEEDBACK_PROMPT_OPEN,
    FEEDBACK_PROMPT_GAP_FILL,
    FEEDBACK_PROMPT_CITEER,
    FEEDBACK_PROMPT_NUMMERING,
    FEEDBACK_PROMPT_ORDER,
    FEEDBACK_PROMPT_TABEL_INVULLEN,
    FEEDBACK_PROMPT_MATCH,
    HINT_PROMPT_TEMPLATE,
    FOLLOW_UP_PROMPT_TEMPLATE,
    THEORY_EXPLANATION_PROMPT
)

# Configure Google Generative AI with API key
api_key = os.getenv('GEMINI_API_KEY')
if api_key:
    # Configure API key (needs to be done only once ideally, but safe to repeat)
    # Overweeg deze configuratie te centraliseren (bv. in app.py of een init file)
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        print(f"WARNING: Failed to configure GenAI in language_exam blueprint: {e}")
else:
    print("WARNING: GEMINI_API_KEY not found in environment variables")

# Lijst met taalvakken (lowercase) - Deze is specifiek voor deze blueprint
language_subjects = ['duits', 'engels', 'frans', 'nederlands']
# Definieer niet-taalvakken (lowercase) voor routering
# Deze lijst wordt gebruikt in select_exam_page en toon_vraag
non_language_subjects = ['wiskunde', 'natuurkunde', 'scheikunde', 'economie', 'aardrijkskunde', 'geschiedenis', 'biologie', 'nask', 'nask1', 'maatschappijwetenschappen', 'maatschappijkunde']

# Create blueprint (naam blijft 'exam')
# Let op: template_folder verwijst naar de hoofdmap templates, niet een submap
exam_bp = Blueprint('exam', __name__, template_folder='../templates')

@exam_bp.route('/select')
def select_exam_page():
    """Render the exam selection page - CENTRAAL PUNT VOOR ALLE VAKKEN"""
    try:
        exams_all = list_available_exams()
    except Exception as e:
        print(f"Error loading available exams: {e}")
        # Geef een foutmelding weer of render een error-pagina
        return render_template('error.html', message="Kon examens niet laden."), 500
    
    # Filter eventueel verborgen vakken
    exams_filtered = {}
    hidden_subjects = [] # Lege lijst, of verwijder 'economie' als er andere vakken in staan
    for level, subjects_data in exams_all.items():
        filtered_subjects = {subj: periods for subj, periods in subjects_data.items()
                             if subj.lower() not in hidden_subjects}
        if filtered_subjects:
            exams_filtered[level] = filtered_subjects
    exams = exams_filtered
    
    # --- DEBUG PRINT --- 
    print("\n--- DEBUG: All Exams for Selection Page ---")
    import pprint
    pprint.pprint(exams)
    print("--- END DEBUG ---\n")
    # --- END DEBUG PRINT ---

    # <<< START: Specific Display Name Override >>>
    try:
        target_level = 'vmbo'
        target_subject = 'wiskunde'
        original_period = '2024_TV2'
        display_period = '2023_TV1' # Display as 2023 TV1

        if (target_level in exams and 
            target_subject in exams[target_level] and 
            original_period in exams[target_level][target_subject]):
            
            # Find the index of the original period
            try:
                index = exams[target_level][target_subject].index(original_period)
                # Replace it with the desired display period
                exams[target_level][target_subject][index] = display_period
                print(f"INFO: Overrode display for {target_subject}/{target_level}/{original_period} to show {display_period}")
                # Re-sort if necessary (optional, depends on desired final order)
                exams[target_level][target_subject].sort() 
            except ValueError:
                # Should not happen if the 'in' check passed, but good to handle
                print(f"WARN: Could not find index for {original_period} after check, override failed.")

    except Exception as e:
        print(f"ERROR applying display name override: {e}")
    # <<< END: Specific Display Name Override >>>

    level_order = ['vmbo', 'havo', 'vwo']
    subject_order = ['Engels', 'Nederlands', 'Duits', 'Frans', 'Wiskunde', 'Natuurkunde', 'Scheikunde', 'Nask 1'] # Pas volgorde aan naar wens
    level_names = {'vmbo': 'VMBO', 'havo': 'HAVO', 'vwo': 'VWO'}
    current_time = datetime.datetime.now()
    
    # Geef de lijst met niet-taalvakken mee aan de template
    # De template (`select_exam.html`) moet nu logica bevatten om op basis
    # van deze lijst de juiste `url_for` aan te roepen (ofwel 'exam.toon_vraag'
    # ofwel 'non_language_exam.toon_vraag').
    return render_template('select_exam.html', 
                           exams=exams,
                           level_order=level_order,
                           subject_order=subject_order,
                           level_names=level_names,
                           now=current_time,
                           non_language_subjects=non_language_subjects # Lijst nodig voor template logica
                          )

@exam_bp.route('/<subject>/<level>/<time_period>/vraag/<int:question_id>')
def toon_vraag(subject, level, time_period, question_id):
    """Display a specific question (Language)"""
    subject_lower = subject.lower()
    
    # <<< DEBUG PRINT >>>
    print(f"--- DEBUG (exam.py): Checking subject_lower: '{subject_lower}' (Type: {type(subject_lower)}) ---")
    print(f"--- DEBUG (exam.py): Checking against non_language_subjects: {non_language_subjects} (Type: {type(non_language_subjects)}) ---")
    print(f"--- DEBUG (exam.py): Result of check 'subject_lower in non_language_subjects': {subject_lower in non_language_subjects} ---")
    # <<< END DEBUG PRINT >>>
    
    if subject_lower not in language_subjects:
        if subject_lower in non_language_subjects:
             return redirect(url_for('non_language_exam.toon_vraag',
                                    subject=subject, level=level,
                                    time_period=time_period, question_id=question_id))
        else:
             print(f"Warning: Unknown subject '{subject}' routed to language blueprint. Redirecting to select.")
             return redirect(url_for('exam.select_exam_page'))
    
    try:
        vraag_data = get_question_data(subject, level, time_period, question_id)
        if not vraag_data:
            # Als specifieke vraag niet gevonden wordt, terug naar selectie
            print(f"Warning: Question data not found for {subject}/{level}/{time_period}/{question_id}")
            return redirect(url_for('exam.select_exam_page'))
        
        max_vraag_id = get_max_question_id(subject, level, time_period)
    except Exception as e:
        print(f"Error loading question data or max_id for {subject}/{level}/{time_period}/{question_id}: {e}")
        return render_template('error.html', message="Kon vraaggegevens niet laden."), 500

    # API URLs verwijzen naar endpoints binnen DEZE blueprint ('exam')
    # Zorg dat deze namen overeenkomen met de functienamen
    try:
        get_feedback_url = url_for('exam.get_feedback', subject=subject, level=level, time_period=time_period, question_id=question_id)
        get_hint_url = url_for('exam.get_hint', subject=subject, level=level, time_period=time_period, question_id=question_id)
        get_follow_up_url = url_for('exam.get_follow_up', subject=subject, level=level, time_period=time_period, question_id=question_id)
        base_question_url = url_for('exam.toon_vraag', subject=subject, level=level, time_period=time_period, question_id=0)[:-1]
    except Exception as e:
         print(f"Error generating URLs for question page: {e}")
         return render_template('error.html', message="Interne fout bij het genereren van links."), 500

    # <<< DEBUG PRINT: Check keys in vraag_data before rendering >>>
    print(f"--- DEBUG Keys in vraag_data for Q{question_id} before rendering: {list(vraag_data.keys()) if vraag_data else 'None'} ---")
    # <<< END DEBUG PRINT >>>

    # Gebruik de TAAL-specifieke template
    return render_template('index_language.html',
                          vraag_data=vraag_data,
                          vraag_id=question_id,
                          max_vraag_id=max_vraag_id,
                          vak=subject,
                          niveau=level,
                          tijdvak=time_period,
                          get_feedback_url=get_feedback_url,
                          get_hint_url=get_hint_url,
                          get_follow_up_url=get_follow_up_url,
                          base_question_url=base_question_url)

def configure_genai():
    """Configures and returns the Generative AI model and potential error."""
    generation_config = {
        "temperature": 0.2,
        "top_p": 1,
        "top_k": 1,
    }
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]

    # API Key check (moved outside configure call)
    if not os.environ.get("GEMINI_API_KEY"):
         print("CRITICAL: GEMINI_API_KEY environment variable not set.")
         # Retourneer een duidelijke foutmelding die de API call kan afhandelen
         return None, "Error: API Key not configured."

    try:
        # Configure GenAI (indien nog niet gedaan, anders is dit meestal idempotent)
        # genai.configure(api_key=os.environ["GEMINI_API_KEY"]) # Reeds gedaan bij laden blueprint

        model = genai.GenerativeModel(model_name="gemini-2.5-flash-preview-04-17", # Gebruik een geschikt model
                                  generation_config=generation_config,
                                  safety_settings=safety_settings)

        # --- Dynamically set max_output_tokens ---
        try:
            limit = model.output_token_limit
            budget = int(limit * 0.90) # 90% budget
            print(f"DEBUG: Model limit={limit}, Setting max_output_tokens budget={budget}") # Log voor verificatie
            generation_config["max_output_tokens"] = budget
        except AttributeError:
            print("WARNING: Could not retrieve output_token_limit. Using default or previously set value.")
            # Fallback if limit attribute doesn't exist (should not happen with recent SDKs)
            generation_config["max_output_tokens"] = 8192 # Default fallback if needed
        except Exception as e:
             print(f"WARNING: Error setting dynamic token budget: {e}. Using default or previously set value.")
             generation_config["max_output_tokens"] = 8192 # Default fallback if needed
        # --- End dynamic setting ---
        
        # Re-create the model instance with the final generation_config
        model = genai.GenerativeModel(model_name="gemini-2.5-flash-preview-04-17",
                                      generation_config=generation_config, # Pass updated config
                                      safety_settings=safety_settings)
        return model, None
    except Exception as e:
        # Log de fout en retourneer een foutmelding
        print(f"CRITICAL: Failed to initialize GenerativeModel: {e}")
        import traceback
        traceback.print_exc()
        return None, f"Error: Failed to load AI model."

@exam_bp.route('/<subject>/<level>/<time_period>/vraag/<int:question_id>/get_feedback', methods=['POST'])
def get_feedback(subject, level, time_period, question_id):
    """Generate feedback for a user's answer (Language)"""
    user_answer = request.json.get('answer')
    if user_answer is None:
        return jsonify({'error': 'No answer provided'}), 400
    
    try:
        question_data = get_question_data(subject, level, time_period, question_id)
        if not question_data:
            return jsonify({'error': 'Question not found'}), 404
    except Exception as e:
        print(f"Error loading question data in get_feedback: {e}")
        return jsonify({'error': 'Failed to load question data.', 'status': 'error'}), 500
    
    prompt = ""
    question_type = question_data.get('type', '').lower()
    vak_lower = subject.lower()

    # --- Security Check: Ensure this is a language subject --- 
    if vak_lower not in language_subjects:
        print(f"Error: Language blueprint 'get_feedback' called for non-language subject: {subject}")
        return jsonify({'error': 'Internal routing error', 'status': 'error'}), 500
    # ---------------------------------------------------------

    # <<< Determine full language name for prompt context >>>
    language_map = {
        'nederlands': 'Dutch',
        'duits': 'German',
        'frans': 'French',
        'engels': 'English'
    }
    prompt_language = language_map.get(vak_lower, 'Dutch') # Default to Dutch if somehow unknown

    # <<< NEW LOGIC for source text >>>
    source_text_for_analysis = "Geen brontekst beschikbaar."
    if question_data.get('bron_tekst_plain'):
        source_text_for_analysis = question_data['bron_tekst_plain']
        print(f"DEBUG: Using bron_tekst_plain for analysis (length: {len(source_text_for_analysis)})")
    elif question_data.get('bron_tekst_html'): # Fallback to HTML if plain text is missing
        source_text_for_analysis = question_data['bron_tekst_html']
        print(f"DEBUG: Using bron_tekst_html for analysis (length: {len(source_text_for_analysis)})")
    # <<< END NEW LOGIC >>>

    # === Prompt Selectie voor Taalvakken ===
    if question_type == 'mc':
        prompt = FEEDBACK_PROMPT_MC.format(
            vraag_id=question_id,
            exam_question=question_data.get('vraagtekst', ''),
            source_text_content=source_text_for_analysis,
            options_text="\n".join([f"{k}: {v}" for k, v in question_data.get('opties', {}).items()]),
            correct_answer=question_data.get('correct_antwoord', ''),
            max_score=question_data.get('max_score', 1),
            user_answer_key=user_answer,
            user_answer_text=question_data.get('opties', {}).get(user_answer, ''),
            language=prompt_language,
            niveau=level,
            vak=subject
        )
    elif question_type == 'wel_niet':
        correct_list = question_data.get('correct_antwoord', [])
        user_list = user_answer if isinstance(user_answer, list) else []
        total_beweringen = len(correct_list)
        correct_beweringen = 0
        calculated_score = 0 # Initialize score
        if total_beweringen > 0:
            for i in range(min(len(correct_list), len(user_list))):
                # Zorg voor consistente vergelijking (bijv. lowercase strings of booleans)
                correct_val = str(correct_list[i]).lower() == 'true' if isinstance(correct_list[i], bool) else str(correct_list[i]).lower()
                user_val = str(user_list[i]).lower() == 'true' if isinstance(user_list[i], bool) else str(user_list[i]).lower()
                if correct_val == user_val:
                    correct_beweringen += 1
            # Bereken de score (lineaire schaling als voorbeeld)
            max_score_q = question_data.get('max_score', 1)
            calculated_score = round((correct_beweringen / total_beweringen) * max_score_q) if total_beweringen > 0 else 0

        prompt = FEEDBACK_PROMPT_WEL_NIET.format(
            vraag_id=question_id,
            exam_question=question_data.get('vraagtekst', ''),
            source_text_content=source_text_for_analysis,
            beweringen="\n".join([f"- {b}" for b in question_data.get('beweringen', [])]),
            correct_antwoord=str(question_data.get('correct_antwoord', [])),
            user_antwoord=str(user_answer),
            max_score=max_score_q,
            calculated_score=calculated_score,
            niveau=level,
            vak=subject,
            language=prompt_language
        )
    elif question_type == 'gap_fill':
        options_list = question_data.get('options_display', [])
        options_text_formatted = "\n".join([f"- {opt}" for opt in options_list])
        prompt = FEEDBACK_PROMPT_GAP_FILL.format(
            vraag_id=question_id,
            exam_question=question_data.get('vraagtekst', ''),
            source_text_content=source_text_for_analysis,
            options_text_formatted=options_text_formatted,
            correct_antwoord=question_data.get('correct_antwoord', []),
            user_antwoord=user_answer,
            max_score=question_data.get('max_score', 1),
            niveau=level,
            vak=subject,
            language=prompt_language
        )
    elif question_type == 'citeer':
        prompt = FEEDBACK_PROMPT_CITEER.format(
            vraag_id=question_id,
            exam_question=question_data.get('vraagtekst', ''),
            source_text_content=source_text_for_analysis,
            correct_antwoord=question_data.get('correct_antwoord', ''),
            user_antwoord=user_answer,
            max_score=question_data.get('max_score', 1),
            niveau=level,
            vak=subject,
            language=prompt_language
        )
    elif question_type == 'nummering':
        prompt = FEEDBACK_PROMPT_NUMMERING.format(
            vraag_id=question_id,
            exam_question=question_data.get('vraagtekst', ''),
            source_text_content=source_text_for_analysis,
            correct_antwoord=question_data.get('correct_antwoord', ''),
            user_antwoord=user_answer,
            max_score=question_data.get('max_score', 1),
            niveau=level,
            vak=subject,
            language=prompt_language
        )
    elif question_type == 'open':
        prompt = FEEDBACK_PROMPT_OPEN.format(
            vraag_id=question_id,
            exam_question=question_data.get('vraagtekst', ''),
            source_text_content=source_text_for_analysis,
            correct_antwoord=question_data.get('correct_antwoord', ''),
            user_antwoord=user_answer,
            max_score=question_data.get('max_score', 1),
            niveau=level,
            vak=subject,
            language=prompt_language
        )
    elif question_type == 'order':
        zinnen_text = "\n".join([f"- [{z['id']}] {z['tekst']}" for z in question_data.get('zinnen', [])])
        prompt = FEEDBACK_PROMPT_ORDER.format(
            vraag_id=question_id,
            exam_question=question_data.get('vraagtekst', ''),
            source_text_content=source_text_for_analysis,
            zinnen_text=zinnen_text,
            correct_volgorde=question_data.get('correct_volgorde', []),
            user_volgorde=user_answer,
            max_score=question_data.get('max_score', 1),
            niveau=level,
            vak=subject,
            language=prompt_language
        )
    elif question_type == 'tabel_invullen':
        # Format correct answers dictionary for display in prompt
        correct_answers_str = "\n".join([f"- {k}: {v}" for k, v in question_data.get('correct_antwoord', {}).items()])
        # Format user answers dictionary for display in prompt
        user_answers_str = "\n".join([f"- {k}: {v}" for k, v in user_answer.items()]) if isinstance(user_answer, dict) else str(user_answer)
        
        prompt = FEEDBACK_PROMPT_TABEL_INVULLEN.format(
            vraag_id=question_id,
            exam_question=question_data.get('vraagtekst', ''),
            source_text_content=source_text_for_analysis,
            correct_answers_dict=correct_answers_str,
            user_answers_dict=user_answers_str,
            max_score=question_data.get('max_score', 1),
            niveau=level,
            vak=subject,
            language=prompt_language
        )
    elif question_type == 'match':
        # Format columns and answers for display in prompt
        kolom_links_str = "\n".join([f"- {item['id']}: {item['tekst']}" for item in question_data.get('kolom_links', [])])
        kolom_rechts_str = "\n".join([f"- {item['id']}: {item['tekst']}" for item in question_data.get('kolom_rechts', [])])
        correct_answers_str = "\n".join([f"- {k} -> {v}" for k, v in question_data.get('correct_antwoord', {}).items()])
        user_answers_str = "\n".join([f"- {k} -> {v}" for k, v in user_answer.items()]) if isinstance(user_answer, dict) else str(user_answer)
        
        prompt = FEEDBACK_PROMPT_MATCH.format(
            vraag_id=question_id,
            exam_question=question_data.get('vraagtekst', ''),
            kolom_links_str=kolom_links_str,
            kolom_rechts_str=kolom_rechts_str,
            correct_answers_dict=correct_answers_str,
            user_answers_dict=user_answers_str,
            max_score=question_data.get('max_score', 1),
            niveau=level,
            vak=subject,
            language=prompt_language
        )
    
    if not prompt:
        print(f"Error: No prompt found for language question type '{question_type}' for subject {subject}")
        return jsonify({'feedback': f'Interne fout: Geen prompt gevonden voor vraagtype "{question_type}".', 'status': 'error'})

    # --- Bepaal Antwoord Status (voor Taalvakken) --- 
    status = 'unknown'
    correct_answer = question_data.get('correct_antwoord')
    correct_volgorde = question_data.get('correct_volgorde')

    try:
        if question_type == 'mc':
            if isinstance(user_answer, str) and isinstance(correct_answer, str): 
                status = 'correct' if user_answer.lower() == correct_answer.lower() else 'incorrect'
            else: status = 'unknown'
        elif question_type in ['wel_niet', 'gap_fill']:
            if isinstance(user_answer, list) and isinstance(correct_answer, list) and len(user_answer) == len(correct_answer):
                correct_count = sum(1 for ua, ca in zip(user_answer, correct_answer)
                                    if str(ua).lower() == str(ca).lower())
                if correct_count == len(correct_answer): status = 'correct'
                elif correct_count > 0: status = 'partial'
                else: status = 'incorrect'
            else: status = 'unknown'
        elif question_type in ['citeer', 'nummering']:
            user_ans_str = str(user_answer).strip().lower()
            correct_ans_str = str(correct_answer).strip().lower()
            status = 'correct' if user_ans_str == correct_ans_str else 'incorrect'
        elif question_type == 'open':
            status = 'pending' # AI bepaalt status
        elif question_type == 'order':
            if isinstance(user_answer, list) and isinstance(correct_volgorde, list) and len(user_answer) == len(correct_volgorde):
                status = 'correct' if user_answer == correct_volgorde else 'incorrect'
            else: status = 'unknown'
        elif question_type == 'tabel_invullen':
            if isinstance(user_answer, dict) and isinstance(correct_answer, dict):
                correct_count = 0
                total_items = len(correct_answer)
                if total_items > 0:
                    for key in correct_answer:
                        # Basic check: does user answer for key match correct answer?
                        # Improvement: Could use fuzzy matching or allow slight variations later.
                        user_val = str(user_answer.get(key, '')).strip().lower()
                        correct_val = str(correct_answer.get(key, '')).strip().lower()
                        if user_val == correct_val:
                            correct_count += 1
                    
                    if correct_count == total_items:
                        status = 'correct'
                    elif correct_count > 0:
                        status = 'partial'
                    else:
                        status = 'incorrect'
                else:
                    status = 'incorrect' # No correct answers defined?
            else:
                status = 'unknown' # Incorrect answer format
        elif question_type == 'match':
            if isinstance(user_answer, dict) and isinstance(correct_answer, dict):
                correct_count = 0
                total_items = len(correct_answer) 
                if total_items > 0:
                    for left_id, correct_right_id in correct_answer.items():
                        user_right_id = user_answer.get(str(left_id)) # Ensure key is string if needed
                        # Basic check: does user's selected right ID match the correct right ID?
                        if str(user_right_id) == str(correct_right_id):
                            correct_count += 1
                    
                    if correct_count == total_items:
                        status = 'correct'
                    elif correct_count > 0:
                        status = 'partial'
                    else:
                        status = 'incorrect'
                else:
                    status = 'incorrect' # No correct answers defined?
            else:
                # Handle case where user_answer might not be a dict (e.g., if JS failed)
                status = 'unknown' # Or 'incorrect' depending on desired strictness

    except Exception as e:
        print(f"Error determining status for language question {question_id}: {e}")
        status = 'error'
    # --- Einde Status Bepaling ---
    
    # --- Generative AI Call --- 
    model, error_message = configure_genai()
    if error_message:
        # Stuur de foutmelding door naar de frontend
        return jsonify({"feedback": error_message, "status": "error"}), 500

    try:
        print(f"\nDEBUG (Lang): Calling Gemini for Q{question_id} type {question_type}...")
        full_prompt = SYSTEM_PROMPT + "\n\n" + prompt
        # TODO: Overweeg timeouts en specifiekere exception handling voor API calls
        response = model.generate_content(full_prompt)
        
        # <<< START Verbeterde Debug Logging >>>
        print(f"\nDEBUG (Lang): FULL Response object from Gemini for Q{question_id}:")
        print(response) # Log het hele response object
        print(f"\nDEBUG (Lang): Prompt Feedback for Q{question_id}:")
        print(response.prompt_feedback) # Log prompt feedback (voor safety blocks)
        print(f"\nDEBUG (Lang): Response Text for Q{question_id}:")
        feedback_text = response.text # Haal text op NA loggen hele object
        print(feedback_text)
        print("--- END DEBUG ---\n")
        # <<< EINDE Verbeterde Debug Logging >>>

        # --- Parse Status uit AI Feedback (alleen voor 'open', 'tabel_invullen', 'match' nu) --- 
        parsed_feedback = feedback_text
        ai_determined_status = status # Start with rule-based status

        # Allow AI to override status for 'open', 'tabel_invullen' and 'match' based on its detailed check
        # Although for match, the rule-based check is usually sufficient.
        if question_type in ['open', 'tabel_invullen', 'match'] and status not in ['error', 'unknown']: 
            feedback_lower = feedback_text.lower().strip()
            if feedback_lower.startswith('correct:'):
                ai_determined_status = 'correct'
                parsed_feedback = feedback_text[len('correct:'):].strip()
            elif feedback_lower.startswith('incorrect:'):
                ai_determined_status = 'incorrect'
                parsed_feedback = feedback_text[len('incorrect:'):].strip()
            elif feedback_lower.startswith('partial:'):
                ai_determined_status = 'partial'
                parsed_feedback = feedback_text[len('partial:'):].strip()
            # If AI doesn't prefix, use the rule-based status
            else:
                print(f"Warning: AI feedback for {question_type} Q{question_id} did not start with expected status prefix. Using rule-based status: {status}")
                # For match, we trust our rule-based status more if AI fails format
                ai_determined_status = status 

        # Gebruik de (mogelijk door AI aangepaste) status
        final_status = ai_determined_status 

        return jsonify({'feedback': parsed_feedback, 'status': final_status}) # Gebruik final_status
    
    except Exception as e:
        print(f"Error generating language feedback with GenAI: {e}")
        import traceback
        traceback.print_exc()
        # Geef een generieke, gebruikersvriendelijke foutmelding terug
        return jsonify({'error': 'Er is een fout opgetreden bij het genereren van AI feedback. Probeer het later opnieuw.', 'status': 'error'}), 500

@exam_bp.route('/<subject>/<level>/<time_period>/vraag/<int:question_id>/get_hint', methods=['GET'])
def get_hint(subject, level, time_period, question_id):
    """Generate a hint for the current question (Language)"""
    # <<< Get model selection from request query parameters >>>
    selected_model = request.args.get('selected_model') 
    
    try:
        question_data = get_question_data(subject, level, time_period, question_id)
        if not question_data:
            return jsonify({'error': 'Question not found'}), 404

        # <<< NEW LOGIC for source text >>>
        source_text_for_analysis = "Geen brontekst beschikbaar."
        if question_data.get('bron_tekst_plain'):
            source_text_for_analysis = question_data['bron_tekst_plain']
        elif question_data.get('bron_tekst_html'): # Fallback to HTML
            source_text_for_analysis = question_data['bron_tekst_html']
        # <<< END NEW LOGIC >>>
            
        options_text = ""
        if question_data.get('type', '').lower() == 'mc':
             options_text = "\n".join([f"{k}: {v}" for k, v in question_data.get('opties', {}).items()])
             
        prompt_text = HINT_PROMPT_TEMPLATE.format(
            vraag_id=question_id,
            vak=subject,
            niveau=level,
            exam_question=question_data.get('vraagtekst', ''), 
            # source_text_snippet=source_text_snippet, # REMOVED
            source_text_content=source_text_for_analysis, # ADDED
            options_text=options_text 
        )

        # Roep Gemini aan
        try:
            # <<< Pass selected_model to configure_genai >>>
            # model, error_message = configure_genai(model_name=selected_model) # Use central config if available
            model, error_message = configure_genai() # Using simplified config for now
            if error_message:
                return jsonify({"error": error_message}), 500

            print(f"\nDEBUG (Lang Hint): Calling Gemini for Hint Q{question_id}...")
            full_prompt = SYSTEM_PROMPT + "\n\n" + prompt_text
            response = model.generate_content(full_prompt)
            hint = response.text
            print(f"---> Hint Received: {hint[:100]}...")
            return jsonify({'hint': hint})
        
        except Exception as e:
            print(f"CRITICAL: Error generating hint for Q{question_id}: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': 'Fout bij genereren hint.', 'status': 'error'}), 500

    except Exception as e:
        print(f"Error in get_hint route for Q{question_id}: {e}")
        return jsonify({'error': 'Interne serverfout.', 'status': 'error'}), 500

@exam_bp.route('/<subject>/<level>/<time_period>/vraag/<int:question_id>/get_follow_up', methods=['POST'])
def get_follow_up(subject, level, time_period, question_id):
    """Generate a follow-up answer (Language)"""
    follow_up_question = request.json.get('question')
    # <<< Get model selection from request >>>
    selected_model = request.json.get('selected_model') # Get selected model
    
    if not follow_up_question:
        return jsonify({'error': 'No question provided'}), 400
    
    previous_feedback = request.json.get('feedback')
    question_data = get_question_data(subject, level, time_period, question_id)
    if not question_data:
        return jsonify({'error': 'Question not found'}), 404
    
    safe_previous_feedback = str(previous_feedback or '').replace('{', '{{}}').replace('}', '}}')
    
    # <<< NEW LOGIC for source text >>>
    source_text_for_analysis = "Geen brontekst beschikbaar."
    if question_data.get('bron_tekst_plain'):
        source_text_for_analysis = question_data['bron_tekst_plain']
    elif question_data.get('bron_tekst_html'): # Fallback to HTML
        source_text_for_analysis = question_data['bron_tekst_html']
    # <<< END NEW LOGIC >>>

    prompt = FOLLOW_UP_PROMPT_TEMPLATE.format(
        vraag_id=question_id,
        vak=subject,
        niveau=level,
        exam_question=question_data.get('vraagtekst', ''),
        # source_text_snippet=source_text_snippet, # REMOVED
        source_text_content=source_text_for_analysis, # ADDED
        correct_answer=question_data.get('correct_antwoord', ''),
        previous_feedback=safe_previous_feedback,
        follow_up_question=follow_up_question 
    )
    
    # Call Generative AI
    try:
        # <<< Pass selected_model to configure_genai >>>
        # model, error_message = configure_genai(model_name=selected_model) # Use central config if available
        model, error_message = configure_genai() # Using simplified config for now
        if error_message:
            return jsonify({"error": error_message}), 500
        
        print(f"\nDEBUG (Lang Follow-up): Calling Gemini for Follow-up Q{question_id}...")
        full_prompt = SYSTEM_PROMPT + "\n\n" + prompt
        response = model.generate_content(full_prompt)
        answer = response.text
        print(f"---> Follow-up Answer Received: {answer[:100]}...")
        return jsonify({'answer': answer})
    
    except Exception as e:
        print(f"CRITICAL: Error generating follow-up for Q{question_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Fout bij genereren follow-up.', 'status': 'error'}), 500

@exam_bp.route('/<subject>/<level>/<time_period>/vraag/<int:question_id>/get_theory_explanation', methods=['GET'])
def get_theory_explanation(subject, level, time_period, question_id):
    """Generate theory explanation related to the question (Language)"""
    try:
        question_data = get_question_data(subject, level, time_period, question_id)
        if not question_data:
            return jsonify({'error': 'Question not found'}), 404
    except Exception as e:
        print(f"Error loading question data in get_theory_explanation: {e}")
        return jsonify({'error': 'Failed to load question data.'}), 500

    vraagtekst = question_data.get('vraagtekst', '')
    correct_answer = question_data.get('correct_antwoord', '')
    context = f"Vraag: {vraagtekst}\nCorrect antwoord: {correct_answer}"
    
    prompt = THEORY_EXPLANATION_PROMPT.format(
        vak=subject,
        niveau=level,
        context=context
    )

    model, error_message = configure_genai()
    if error_message:
        return jsonify({"error": error_message}), 500

    try:
        print(f"\nDEBUG (Lang): Calling Gemini for Theory Explanation Q{question_id}...")
        full_prompt = SYSTEM_PROMPT + "\n\n" + prompt
        response = model.generate_content(full_prompt)
        explanation = response.text
        print(f"\nDEBUG (Lang): Received theory explanation from Gemini for Q{question_id}.")

        return jsonify({'explanation': explanation})
    except Exception as e:
        print(f"Error generating language theory explanation: {e}")
        return jsonify({'error': 'Fout bij genereren theorie uitleg.'}), 500 