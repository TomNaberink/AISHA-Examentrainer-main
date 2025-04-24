import re
from latex2mathml.converter import convert # Import the converter

# Helper function for re.sub to format fractions
def _format_fraction_match(match):
    # Get text immediately before the match
    preceding_text_start_index = max(0, match.start() - 20) # Look back max 20 chars
    preceding_text = match.string[preceding_text_start_index:match.start()].strip()
    
    numerator = match.group(1).strip()
    denominator = match.group(2).strip()

    # --- CHECK FOR SCORE INDICATION --- 
    if preceding_text.endswith('Score Indicatie:') and numerator.isdigit() and denominator.isdigit():
        # If preceded by "Score Indicatie:" and both parts are numbers, format as text
        return f' {numerator} van {denominator}' # Add leading space for separation
    # --- END CHECK --- 
    
    # Basic check to avoid creating empty spans if capture failed unexpectedly
    elif numerator and denominator:
        # Format as HTML fraction
        return f'<span class="fraction"><span class="numerator">{numerator}</span><span class="denominator">{denominator}</span></span>'
    else:
        # Return original match if capture failed, preventing empty spans
        return match.group(0)

from flask import Blueprint, render_template, request, jsonify, redirect, url_for
import os
import google.generativeai as genai
import datetime # Importeer datetime
from utils.data_loader import list_available_exams, get_question_data, get_max_question_id
# Importeer relevante prompts (inclusief MC voor non-language)
from prompts import (
    SYSTEM_PROMPT,
    FEEDBACK_PROMPT_NON_LANGUAGE_OPEN,
    FEEDBACK_PROMPT_CALCULATION,
    FEEDBACK_PROMPT_MC,
    FEEDBACK_PROMPT_MULTIPLE_GAP_CHOICE,
    HINT_PROMPT_TEMPLATE,
    FOLLOW_UP_PROMPT_TEMPLATE,
    THEORY_EXPLANATION_PROMPT,
    METAPHOR_EXPLANATION_PROMPT,
    CONTINUE_THEORY_PROMPT,
    THEORY_EXPLANATION_MC_PROMPT
)

# Configure Google Generative AI with API key
api_key = os.getenv('GEMINI_API_KEY')
if api_key:
    genai.configure(api_key=api_key)
else:
    print("WARNING: GEMINI_API_KEY not found in environment variables")

# Definieer de lijst met niet-taalvakken die deze blueprint behandelt
non_language_subjects = ['wiskunde', 'natuurkunde', 'scheikunde', 'economie', 'aardrijkskunde', 'geschiedenis', 'biologie', 'nask', 'maatschappijwetenschappen', 'maatschappijkunde']

# Create blueprint voor niet-taalvakken
non_language_exam_bp = Blueprint('non_language_exam', __name__, template_folder='../templates') # Template folder verwijzing toevoegen

# --- Function to convert LaTeX ($$...$$) to MathML using re.sub --- 
def convert_latex_to_mathml(html_content):
    if not html_content or '$$' not in html_content:
        return html_content # Return original if no LaTeX delimiters found
    
    def replace_latex(match):
        latex_code = match.group(1).strip()
        try:
            # Use display='block' for $$...$$
            mathml_output = convert(latex_code, display="block") 
            # Wrap in a div to ensure block display and allow potential styling
            return f'<div class="mathml-block">{mathml_output}</div>' 
        except Exception as e:
            print(f"Error converting LaTeX to MathML: {e}. LaTeX: {latex_code}")
            return match.group(0) # Return original match on error

    # Use re.sub with the helper function
    # Make the regex non-greedy (.*?) to handle multiple formulas
    processed_content = re.sub(r'\$\$(.*?)\$\$', replace_latex, html_content, flags=re.DOTALL)
    return processed_content
# --- End LaTeX conversion function --- 

@non_language_exam_bp.route('/<subject>/<level>/<time_period>/vraag/<int:question_id>')
def toon_vraag(subject, level, time_period, question_id):
    """Display a specific question for non-language exams"""
    vraag_data = get_question_data(subject, level, time_period, question_id)
    if not vraag_data:
        # Redirect naar de hoofdpagina (/) die doorverwijst naar de centrale selectiepagina
        return redirect(url_for('index'))
    
    # <<< COMMENTED OUT - Potential cause of missing context >>>
    if 'context_html' in vraag_data and vraag_data['context_html']:
        vraag_data['context_html'] = convert_latex_to_mathml(vraag_data['context_html'])
    # --- End processing --- 
    
    # <<< ADD PROCESSING FOR VRAAGTEKST >>>
    if 'vraagtekst_html' in vraag_data and vraag_data['vraagtekst_html']:
        vraag_data['vraagtekst_html'] = convert_latex_to_mathml(vraag_data['vraagtekst_html'])
    # <<< END ADDED PROCESSING >>>

    # --- Re-enable server-side LaTeX processing --- 
    if 'correct_antwoord_model' in vraag_data and vraag_data['correct_antwoord_model']:
        vraag_data['correct_antwoord_model'] = convert_latex_to_mathml(vraag_data['correct_antwoord_model'])
    # --- End processing --- 

    # <<< ADD PROCESSING FOR MC OPTIONS >>>
    if vraag_data.get('type') == 'mc' and 'options' in vraag_data:
        for option in vraag_data['options']:
            if 'text' in option and option['text']:
                option['text'] = convert_latex_to_mathml(option['text'])
    # <<< END ADDED PROCESSING >>>
    
    max_vraag_id = get_max_question_id(subject, level, time_period)
    question_type = vraag_data.get('type', '').lower()
    
    # --- Dynamically determine Theory Explanation URL based on question type --- 
    theory_endpoint = None
    if question_type == 'calculation':
        theory_endpoint = 'non_language_exam.get_theory_explanation_calculation'
    elif question_type == 'open_non_language':
        theory_endpoint = 'non_language_exam.get_theory_explanation_open'
    elif question_type == 'multiple_gap_choice':
        theory_endpoint = 'non_language_exam.get_theory_explanation_multiple_gap_choice'
    elif question_type == 'mc':
        theory_endpoint = 'non_language_exam.get_theory_explanation_open'
    # Add more types here if they get specific theory explanation endpoints
    
    get_theory_url = None
    if theory_endpoint:
        try:
            get_theory_url = url_for(theory_endpoint, 
                                      subject=subject, level=level, 
                                      time_period=time_period, question_id=question_id)
        except Exception as e:
            print(f"Error building theory URL for endpoint {theory_endpoint}: {e}")
            get_theory_url = None # Fallback if URL generation fails
    # --- End dynamic URL generation --- 

    # API URLs moeten verwijzen naar endpoints binnen DEZE blueprint (non_language_exam)
    get_feedback_url = url_for('non_language_exam.get_feedback', 
                              subject=subject, level=level, 
                              time_period=time_period, question_id=question_id)
    get_hint_url = url_for('non_language_exam.get_hint', 
                          subject=subject, level=level, 
                          time_period=time_period, question_id=question_id)
    get_follow_up_url = url_for('non_language_exam.get_follow_up', 
                               subject=subject, level=level, 
                               time_period=time_period, question_id=question_id)
    # get_theory_url is now determined dynamically above

    # Base URL for question navigation binnen deze blueprint (non_language_exam)
    base_question_url = url_for('non_language_exam.toon_vraag', 
                              subject=subject, level=level, 
                              time_period=time_period, question_id=0)[:-1]
    
    # <<< ADDED: Log context_html value JUST BEFORE rendering >>>
    print(f"--- DEBUG: Value of context_html BEFORE render_template: {vraag_data.get('context_html', 'KEY_NOT_FOUND')}")
    
    # Gebruik de NIET-TAAL specifieke template
    return render_template('index_non_language.html',
                           vraag_data=vraag_data,
                           vraag_id=question_id,
                           max_vraag_id=max_vraag_id,
                           vak=subject,
                           niveau=level,
                           tijdvak=time_period,
                           get_feedback_url=get_feedback_url,
                           get_hint_url=get_hint_url,
                           get_follow_up_url=get_follow_up_url,
                           get_theory_url=get_theory_url, # Pass the dynamically determined URL
                           base_question_url=base_question_url,
                           correct_antwoord_model=vraag_data.get('correct_antwoord_model')
                           )

def configure_genai(model_name=None):
    # Define allowed models and a default
    allowed_models = {
        'gemini-2.5-flash-preview-04-17', # Slimste (user label 2.5)
        'gemini-2.0-flash'                  # Snelste (user label 2.0)
    }
    default_model = 'gemini-2.5-flash-preview-04-17' # Default to the Slimste (2.5) model
    fixed_max_tokens = 2048 # Default/fallback max tokens
    
    # Determine the model to use
    selected_model_name = default_model
    if model_name in allowed_models:
        selected_model_name = model_name
        print(f"DEBUG: Using selected model: {selected_model_name}") # Debug log
    else:
        if model_name:
            print(f"DEBUG: Received invalid model name '{model_name}'. Falling back to default: {default_model}")
        else:
            print(f"DEBUG: No model name provided. Using default: {default_model}")

    # <<< Dynamically set generation_config based on model >>>
    generation_config = {
        "temperature": 0.2,
        "top_p": 1,
        "top_k": 1,
        "max_output_tokens": fixed_max_tokens # Start with fallback
    }

    if selected_model_name == 'gemini-2.5-flash-preview-04-17': # <<< Use correct full name
        try:
            # <<< FIX: Prepend 'models/' to the name >>>
            formatted_model_name = f"models/{selected_model_name}"
            # Attempt to get the model details to find its limit
            model_info = genai.get_model(formatted_model_name) # Use formatted name
            limit = model_info.output_token_limit
            if limit:
                budget = int(limit * 0.80) # Calculate 80% budget
                generation_config["max_output_tokens"] = budget
                print(f"DEBUG: Setting max_output_tokens for {selected_model_name} to 80% budget: {budget} (Limit: {limit})")
            else:
                print(f"WARN: Could not retrieve output_token_limit for {selected_model_name}. Using fallback max_output_tokens: {fixed_max_tokens}")
        except Exception as e:
            print(f"ERROR: Failed to get model info for {selected_model_name}: {e}. Using fallback max_output_tokens: {fixed_max_tokens}")
    else:
        # For gemini-2.0-flash or other future models, use the fixed default
        print(f"DEBUG: Using fixed max_output_tokens for {selected_model_name}: {fixed_max_tokens}")

    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]
    try:
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    except KeyError:
        return None, "Error: GEMINI_API_KEY environment variable not set."
    except Exception as e:
        return None, f"An unexpected error occurred during GenAI configuration: {e}"
    
    # <<< Use the selected_model_name >>>
    model = genai.GenerativeModel(model_name=selected_model_name,
                                  generation_config=generation_config,
                                  safety_settings=safety_settings)
    return model, None

@non_language_exam_bp.route('/<subject>/<level>/<time_period>/vraag/<int:question_id>/get_feedback', methods=['POST'])
def get_feedback(subject, level, time_period, question_id):
    """Generate feedback for a user's answer (Non-Language)"""
    # <<< Get model selection from request >>>
    user_answer = request.json.get('answer')
    selected_model = request.json.get('selected_model') # Get selected model
    
    if user_answer is None: # Check for None, not just falsiness
        return jsonify({'error': 'No answer provided'}), 400
    
    try:
        question_data = get_question_data(subject, level, time_period, question_id)
        if not question_data:
            return jsonify({'error': 'Question not found'}), 404
    except Exception as e:
        print(f"Error loading question data in get_feedback (non-lang): {e}")
        return jsonify({'error': 'Failed to load question data.', 'status': 'error'}), 500

    prompt = ""
    question_type = question_data.get('type', '').lower()
    vak_lower = subject.lower()
    exam_context = question_data.get('context_html', 'Geen context beschikbaar.') # Haal context op

    # --- Security Check: Ensure this is a NON-language subject --- 
    print(f"DEBUG FEEDBACK CHECK: Checking subject '{vak_lower}' against list: {non_language_subjects}")
    if vak_lower not in non_language_subjects:
        print(f"Warning: Unsupported non-language subject '{subject}'")
        # Geef generieke melding terug ipv 501 error
        return jsonify({'feedback': f'Feedback wordt nog niet ondersteund voor vak "{subject}".', 'status': 'unknown'})

    # Brontekst is optioneel voor niet-taalvakken, maar kan nuttig zijn
    source_text_snippet = question_data.get('bron_tekst_html', '')
    if source_text_snippet: 
        source_text_snippet = source_text_snippet[:300] + "..."
    else: 
        source_text_snippet = "N.v.t."

    # === Prompt Selectie voor Niet-Taalvakken ===
    if question_type == 'mc':
        # Correctly format options from the list structure
        options_list = question_data.get('options', [])
        options_text_formatted = "\n".join([f"{opt.get('id', '?')}: {opt.get('text', '')}" for opt in options_list])
        # Find the text for the user's answer
        user_answer_text_found = ''
        for opt in options_list:
            if str(opt.get('id', '')) == str(user_answer):
                user_answer_text_found = opt.get('text', '')
                break

        prompt = FEEDBACK_PROMPT_MC.format(
            vraag_id=question_id,
            exam_question=question_data.get('vraagtekst_html', ''), # Use _html key
            source_text_snippet=source_text_snippet, # Keep this, might be relevant sometimes
            options_text=options_text_formatted, # Use correctly formatted text
            correct_answer=question_data.get('correct_answer', ''), # Use correct_answer key
            max_score=question_data.get('max_score', 1),
            user_answer_key=user_answer,
            user_answer_text=user_answer_text_found, # Use the found text
            niveau=level,
            vak=subject
            # language="Dutch" # Language might not be needed here
        )
    elif question_type == 'open_non_language':
        prompt = FEEDBACK_PROMPT_NON_LANGUAGE_OPEN.format(
            vraag_id=question_id,
            vak=subject,
            niveau=level,
            exam_question=question_data.get('vraagtekst_html', ''),
            exam_context=exam_context, # Geef context mee
            user_antwoord=user_answer,
            correct_antwoord=question_data.get('correct_antwoord_model', ''),
            max_score=question_data.get('max_score', 1)
        )
    elif question_type == 'calculation':
        prompt = FEEDBACK_PROMPT_CALCULATION.format(
            vraag_id=question_id,
            vak=subject,
            niveau=level,
            exam_question=question_data.get('vraagtekst_html', ''),
            exam_context=exam_context, # Geef context mee
            user_antwoord=user_answer,
            correct_antwoord=question_data.get('correct_antwoord_model', ''),
            max_score=question_data.get('max_score', 1)
        )
    elif question_type == 'multiple_gap_choice':
        # --- Logica voor Multiple Gap Choice --- 
        gaps_list = question_data.get('gaps', [])
        if not gaps_list:
            return jsonify({'error': 'Gaps data missing in question JSON for multiple_gap_choice'}), 500
        
        # Verwacht user_answer als dictionary: {"gap_id": "gekozen_antwoord"}
        if not isinstance(user_answer, dict):
             return jsonify({'error': 'Invalid answer format for multiple_gap_choice. Expected a dictionary.'}), 400
        
        # Maak strings voor de prompt
        gaps_details_list = []
        user_answers_formatted_list = []
        for gap in gaps_list:
            gap_id_str = str(gap.get('id', '?'))
            zin = gap.get('zin_html', '')
            choices = ", ".join(gap.get('choices', []))
            correct = gap.get('correct_choice', '')
            gaps_details_list.append(f"- Gat ({gap_id_str}): '{zin}' -> Keuzes: [{choices}] -> Correct: **{correct}**")
            
            user_choice = user_answer.get(gap_id_str, '[Niet beantwoord]')
            user_answers_formatted_list.append(f"- Gat ({gap_id_str}): {user_choice}")

        gaps_details = "\n".join(gaps_details_list)
        user_answers_formatted = "\n".join(user_answers_formatted_list)
        
        prompt = FEEDBACK_PROMPT_MULTIPLE_GAP_CHOICE.format(
            vraag_id=question_id,
            vak=subject,
            niveau=level,
            exam_question=question_data.get('vraagtekst_html', ''),
            # exam_context=exam_context, # Context meestal niet relevant voor dit type?
            gaps_details=gaps_details,
            user_answers_formatted=user_answers_formatted,
            correct_antwoord_model=question_data.get('correct_antwoord_model', ''), # Overzicht correcte antwoorden
            max_score=question_data.get('max_score', 1),
            gap_count=len(gaps_list)
        )
    else:
        # Fallback for unknown types in non-language blueprint
        print(f"Warning: Unsupported question type '{question_type}' in non-language blueprint for Q{question_id}")
        # Geef generieke melding terug ipv 501 error
        return jsonify({'feedback': f'Feedback wordt nog niet ondersteund voor vraagtype "{question_type}".', 'status': 'unknown'})
            
    # === Einde Prompt Selectie ===

    # --- Bepaal Initiële Antwoord Status (voor logging/fallback) --- 
    status = 'pending' # Default: AI bepaalt de status
    correct_answer = question_data.get('correct_antwoord')
    
    try:
        if question_type == 'mc':
            if isinstance(user_answer, str) and isinstance(correct_answer, str): 
                status = 'correct' if user_answer.lower() == correct_answer.lower() else 'incorrect'
            else:
                 status = 'unknown' # Kon niet vergelijken
        # Voor andere types laten we AI status bepalen, status blijft 'pending'
        
    except Exception as e:
        print(f"Error determining initial status for non-lang question {question_id}: {e}")
        status = 'error' # Fout bij status bepaling vooraf
    # --- Einde Initiële Status Bepaling ---

    # --- Generative AI Call --- 
    # <<< Pass selected_model to configure_genai >>>
    model, error = configure_genai(model_name=selected_model)
    if error:
        return jsonify({"feedback": error, "status": "error"}), 500

    try:
        print(f"\nDEBUG (Non-Lang): Calling Gemini for Q{question_id} type {question_type}...")
        full_prompt = SYSTEM_PROMPT + "\n\n" + prompt
        response = model.generate_content(full_prompt)
        raw_feedback_text = response.text # Get the raw text first
        print(f"\nDEBUG (Non-Lang): Received RAW feedback from Gemini for Q{question_id}:\n")
        print(raw_feedback_text)

        # --- Clean up stray characters BEFORE assigning to cleaned_feedback_text --- 
        temp_text = raw_feedback_text.replace(': *', ':') # Remove stray asterisk after colon+space
        temp_text = temp_text.replace('`', '') # Remove backticks
        cleaned_feedback_text = temp_text # Use the cleaned text
        
        # --- DEBUG: Print the cleaned feedback (Now should be same as RAW, minus strays) --- 
        print(f"\nDEBUG (Non-Lang): CLEANED feedback for Q{question_id} (Expecting ** from AI):")
        print(cleaned_feedback_text)
        print("--- END CLEANED DEBUG ---\n")

        # --- Parse Status from CLEANED Feedback (expecting ** from AI) --- 
        parsed_feedback = cleaned_feedback_text
        ai_determined_status = status
        feedback_lower_strip = cleaned_feedback_text.lower().strip()
        if feedback_lower_strip.startswith('**correct:**'):
            ai_determined_status = 'correct'
        elif feedback_lower_strip.startswith('correct:') and ai_determined_status == 'pending':
             ai_determined_status = 'correct'
        elif feedback_lower_strip.startswith('**incorrect:**'):
            ai_determined_status = 'incorrect'
        elif feedback_lower_strip.startswith('incorrect:') and ai_determined_status == 'pending':
             ai_determined_status = 'incorrect'
        elif feedback_lower_strip.startswith('**gedeeltelijk:**'):
            ai_determined_status = 'partial'
        elif feedback_lower_strip.startswith('gedeeltelijk:') and ai_determined_status == 'pending':
             ai_determined_status = 'partial'
        else:
            if ai_determined_status == 'pending': 
                print(f"Warning: AI feedback Q{question_id} did not start with expected status ('correct:', 'incorrect:', 'gedeeltelijk:', potentially with **). Status remains pending.")
        
        # <<< Convert LaTeX in feedback to MathML >>>
        parsed_feedback = convert_latex_to_mathml(parsed_feedback)
        
        return jsonify({'feedback': parsed_feedback, 'status': ai_determined_status})
    
    # Ensure the except block is present and correctly handles errors
    except Exception as e:
        print(f"Error generating non-language feedback: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Error generating AI feedback'}), 500

@non_language_exam_bp.route('/<subject>/<level>/<time_period>/vraag/<int:question_id>/get_hint', methods=['GET'])
def get_hint(subject, level, time_period, question_id):
    """Generate a hint for the current question (Non-Language)"""
    # <<< Get model selection from request query parameters >>>
    selected_model = request.args.get('selected_model') 
    
    try:
        question_data = get_question_data(subject, level, time_period, question_id)
        if not question_data:
            return jsonify({'error': 'Question not found'}), 404

        # Bepaal welke prompt te gebruiken op basis van vraagtype
        question_type = question_data.get('type', '').lower()
        prompt_text = ""

        if question_type == 'multiple_gap_choice':
            gaps_list = question_data.get('gaps', [])
            gaps_details_list = []
            for gap in gaps_list:
                zin = gap.get('zin_html', '').replace('<strong>', '').replace('</strong>', '')
                choices = ", ".join(gap.get('choices', []))
                gaps_details_list.append(f"- Zin: '{zin}' -> Keuzes: [{choices}]")
            gaps_details_for_hint = "\n".join(gaps_details_list)

            prompt_text = FEEDBACK_PROMPT_MULTIPLE_GAP_CHOICE.format(
                vraag_id=question_id,
                vak=subject,
                niveau=level,
                gaps_details_for_hint=gaps_details_for_hint
            )
        else:
            # Gebruik generieke hint prompt voor andere (niet-taal) types
            # Let op: HINT_PROMPT_TEMPLATE is erg gericht op MC, misschien aanpassen?
            # VEILIGHEIDSCONTROLE: Haal source_text_content op met fallback
            source_text_content = question_data.get('source_text_content', 'N.v.t.') 
            if len(source_text_content) > 300: # Nog steeds inkorten indien wel aanwezig
                source_text_content = source_text_content[:300] + "..."
            
            prompt_text = HINT_PROMPT_TEMPLATE.format(
                vraag_id=question_id,
                vak=subject,
                niveau=level,
                exam_question=question_data.get('vraagtekst_html', ''), # Gebruik _html versie
                source_text_content=source_text_content, # <<< GEWIJZIGD van source_text_snippet
                options_text="" # Geen MC opties hier
            )

        # Roep Gemini aan
        try:
            # <<< Pass selected_model to configure_genai >>>
            model, error_message = configure_genai(model_name=selected_model)
            if error_message:
                return jsonify({"error": error_message}), 500

            print(f"\nDEBUG (Non-Lang): Calling Gemini for Hint Q{question_id} (Type: {question_type})...")
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

@non_language_exam_bp.route('/<subject>/<level>/<time_period>/vraag/<int:question_id>/get_follow_up', methods=['POST'])
def get_follow_up(subject, level, time_period, question_id):
    """Generate a follow-up answer (Non-Language)"""
    # <<< Get model selection from request >>>
    follow_up_question = request.json.get('question')
    selected_model = request.json.get('selected_model') # Get selected model
    
    if not follow_up_question:
        return jsonify({'error': 'No question provided'}), 400
    
    previous_feedback = request.json.get('feedback')
    question_data = get_question_data(subject, level, time_period, question_id)
    if not question_data:
        return jsonify({'error': 'Question not found'}), 404
    
    # Escape potentially problematic characters in previous feedback
    safe_previous_feedback = str(previous_feedback or '').replace('{', '{{').replace('}', '}}')

    # Haal source_text_snippet op (zal leeg zijn voor non-language)
    source_text_snippet = question_data.get('bron_tekst_html', '') 
    if source_text_snippet: source_text_snippet = source_text_snippet[:300] + "..."
    else: source_text_snippet = "N.v.t." # Maak expliciet N.v.t. voor prompt

    # Gebruik de correcte keys voor non-language vragen
    exam_question_text = question_data.get('vraagtekst_html', '[Vraagtekst niet beschikbaar]')
    correct_answer_model = question_data.get('correct_antwoord_model', '[Model niet beschikbaar]')

    prompt = FOLLOW_UP_PROMPT_TEMPLATE.format(
        vraag_id=question_id,
        vak=subject,
        niveau=level,
        exam_question=exam_question_text, # Gebruik _html versie
        source_text_snippet=source_text_snippet,
        correct_answer=correct_answer_model, # Gebruik correct_antwoord_model
        previous_feedback=safe_previous_feedback, # Use escaped version
        follow_up_question=follow_up_question 
    )
    
    # Restore original AI call block with try...except
    try:
        # <<< Pass selected_model to configure_genai >>>
        model, error_message = configure_genai(model_name=selected_model)
        if error_message:
            return jsonify({"error": error_message}), 500

        # Definieer full_prompt eerst
        full_prompt = SYSTEM_PROMPT + "\n\n" + prompt 

        print("\n--- DEBUG FOLLOW-UP: Prompt wordt verstuurd --- ") # DEBUG
        # print(full_prompt) # DEBUG: Log de volledige prompt - NU NA DEFINITIE
        # print("--- EINDE PROMPT --- ") # DEBUG

        response = model.generate_content(full_prompt)
        
        # print("--- DEBUG FOLLOW-UP: AI Call Voltooid --- ") # DEBUG
        # print(f"DEBUG FOLLOW-UP: Prompt Feedback: {response.prompt_feedback}") # DEBUG: Check voor block reden
        
        # *** Add fraction formatting using regex ***
        ai_answer_text = response.text
        print(f"\nDEBUG FOLLOW-UP: RAW AI Answer text for Q{question_id}:")
        print(ai_answer_text)
        # print("--- END RAW AI Answer ---")

        # --- Clean up stray characters BEFORE assigning to cleaned_answer_text --- 
        temp_text = ai_answer_text.replace(': *', ':') # Remove stray asterisk after colon+space
        temp_text = temp_text.replace('`', '') # Remove backticks
        cleaned_answer_text = temp_text # Use the cleaned text
        
        # --- DEBUG: Print the final answer text (Now should be same as RAW, minus strays) --- 
        print(f"\nDEBUG FOLLOW-UP: CLEANED Answer text for Q{question_id} (Expecting ** from AI):")
        print(cleaned_answer_text)
        print("--- END CLEANED FOLLOW-UP DEBUG ---")

        return jsonify({'answer': cleaned_answer_text})
    
    # Ensure this except block exists and handles errors for the follow-up route
    except Exception as e:
        print(f"CRITICAL Error generating non-language follow-up answer for Q{question_id}: {e}")
        import traceback
        traceback.print_exc() # Print detailed traceback to Flask console
        return jsonify({'error': f'Error generating follow-up answer: {str(e)}'}), 500

# Near the top, perhaps after imports
CONTINUATION_MARKER = "[... wordt vervolgd ...]"

@non_language_exam_bp.route('/<subject>/<level>/<time_period>/vraag/<int:question_id>/get_theory_explanation_calculation', methods=['GET'])
def get_theory_explanation_calculation(subject, level, time_period, question_id):
    """Generate a theory explanation for the current question (Non-Language)"""
    # <<< Get model selection from request query parameters >>>
    selected_model = request.args.get('selected_model')
    
    try:
        question_data = get_question_data(subject, level, time_period, question_id)
        if not question_data:
            return jsonify({'error': 'Question not found'}), 404

        # Bepaal welke prompt te gebruiken op basis van vraagtype
        question_type = question_data.get('type', '').lower()
        prompt_text = ""

        if question_type == 'calculation':
            prompt_text = THEORY_EXPLANATION_PROMPT.format(
                vraag_id=question_id,
                vak=subject,
                niveau=level,
                question_type=question_type,
                exam_question=question_data.get('vraagtekst_html', ''),
                exam_context=question_data.get('context_html', 'Geen context beschikbaar.')
            )
        else:
            # Gebruik generieke hint prompt voor andere (niet-taal) types
            # Let op: HINT_PROMPT_TEMPLATE is erg gericht op MC, misschien aanpassen?
            source_text_snippet = question_data.get('bron_tekst_html', '') # Leeg voor non-language
            if source_text_snippet: source_text_snippet = source_text_snippet[:300] + "..."
            else: source_text_snippet = "N.v.t."
            
            prompt_text = HINT_PROMPT_TEMPLATE.format(
                vraag_id=question_id,
                vak=subject,
                niveau=level,
                exam_question=question_data.get('vraagtekst_html', ''), # Gebruik _html versie
                source_text_content=source_text_snippet, # <<< GEWIJZIGD van source_text_snippet
                options_text="" # Geen MC opties hier
            )

        # Roep Gemini aan
        try:
            # <<< Pass selected_model to configure_genai >>>
            model, error_message = configure_genai(model_name=selected_model)
            if error_message:
                return jsonify({"error": error_message}), 500

            print(f"\nDEBUG (Non-Lang): Calling Gemini for Theory Explanation (Calculation) Q{question_id} (Type: {question_type})...")
            full_prompt = SYSTEM_PROMPT + "\n\n" + prompt_text
            response = model.generate_content(full_prompt)
            explanation = response.text
            # <<< DEBUG: Log raw response >>>
            print(f"RAW AI Theory Response:\n{explanation}\n--- END RAW ---")
            # <<< END DEBUG >>>

            # <<< Convert LaTeX in explanation to MathML >>>
            explanation = convert_latex_to_mathml(explanation)

            # <<< MODIFIED: Check if marker is anywhere in the text >>>
            is_complete = True
            cleaned_explanation = explanation
            if CONTINUATION_MARKER in explanation:
                is_complete = False
                # Remove the marker from the text sent to the frontend (replace first occurrence)
                cleaned_explanation = explanation.replace(CONTINUATION_MARKER, '', 1).strip()
            # <<< END MODIFIED >>>

            print(f"---> Theory Explanation Received (Complete: {is_complete}): {cleaned_explanation[:100]}...")
            # <<< MODIFIED: Return JSON with is_complete flag >>>
            return jsonify({'explanation': cleaned_explanation, 'is_complete': is_complete})
        
        except Exception as e:
            print(f"CRITICAL: Error generating theory explanation (calculation) for Q{question_id}: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': 'Fout bij genereren theorie uitleg.', 'status': 'error'}), 500

    except Exception as e:
        print(f"Error in get_theory_explanation_calculation route for Q{question_id}: {e}")
        return jsonify({'error': 'Interne serverfout.', 'status': 'error'}), 500

@non_language_exam_bp.route('/<subject>/<level>/<time_period>/vraag/<int:question_id>/get_theory_explanation_open', methods=['GET'])
def get_theory_explanation_open(subject, level, time_period, question_id):
    """Generate a theory explanation for the current question (Non-Language)"""
    # <<< Get model selection from request query parameters >>>
    selected_model = request.args.get('selected_model')
    
    try:
        question_data = get_question_data(subject, level, time_period, question_id)
        if not question_data:
            return jsonify({'error': 'Question not found'}), 404

        # Bepaal welke prompt te gebruiken op basis van vraagtype
        question_type = question_data.get('type', '').lower()
        prompt_text = ""

        if question_type == 'open_non_language':
            # VEILIGHEIDSCONTROLE: Haal source_text_content op met fallback
            source_text_content = question_data.get('source_text_content', 'N.v.t.') 
            
            prompt_text = THEORY_EXPLANATION_PROMPT.format(
                vraag_id=question_id,
                vak=subject,
                niveau=level,
                question_type=question_type,
                exam_question=question_data.get('vraagtekst_html', ''),
                source_text_content=source_text_content, # << Gebruik veilige waarde
                exam_context=question_data.get('context_html', 'Geen context beschikbaar.')
            )
        elif question_type == 'mc':
            # Format options for the MC theory prompt
            options_list = question_data.get('options', [])
            options_text_formatted = "\n".join([f"{opt.get('id', '?')}: {opt.get('text', '')}" for opt in options_list])
            correct_answer_key = question_data.get('correct_answer', '?')
            
            prompt_text = THEORY_EXPLANATION_MC_PROMPT.format(
                vraag_id=question_id,
                vak=subject,
                niveau=level,
                exam_context=question_data.get('context_html', 'Geen context beschikbaar.'),
                exam_question=question_data.get('vraagtekst_html', ''),
                options_text=options_text_formatted,
                correct_answer_key=correct_answer_key
            )
        else:
            # Fallback to generic THEORY prompt, NOT HINT prompt
            print(f"Warning: Unexpected question type '{question_type}' in get_theory_explanation_open. Using generic THEORY_EXPLANATION_PROMPT.")
            prompt_text = THEORY_EXPLANATION_PROMPT.format(
                vraag_id=question_id,
                vak=subject,
                niveau=level,
                question_type=question_type, # Pass the actual type
                exam_question=question_data.get('vraagtekst_html', ''),
                exam_context=question_data.get('context_html', 'Geen context beschikbaar.')
            )

        # Roep Gemini aan
        try:
            # <<< Pass selected_model to configure_genai >>>
            model, error_message = configure_genai(model_name=selected_model)
            if error_message:
                return jsonify({"error": error_message}), 500

            print(f"\nDEBUG (Non-Lang): Calling Gemini for Theory Explanation (Open) Q{question_id} (Type: {question_type})...")
            full_prompt = SYSTEM_PROMPT + "\n\n" + prompt_text
            response = model.generate_content(full_prompt)
            explanation = response.text
            # <<< DEBUG: Log raw response >>>
            print(f"RAW AI Theory Response (Open):\n{explanation}\n--- END RAW ---")
            # <<< END DEBUG >>>

            # <<< Convert LaTeX in explanation to MathML >>>
            explanation = convert_latex_to_mathml(explanation)

            # <<< MODIFIED: Check if marker is anywhere in the text >>>
            is_complete = True
            cleaned_explanation = explanation
            if CONTINUATION_MARKER in explanation:
                is_complete = False
                # Remove the marker from the text sent to the frontend (replace first occurrence)
                cleaned_explanation = explanation.replace(CONTINUATION_MARKER, '', 1).strip()
            # <<< END MODIFIED >>>

            print(f"---> Theory Explanation Received (Complete: {is_complete}): {cleaned_explanation[:100]}...")
            # <<< MODIFIED: Return JSON with is_complete flag >>>
            return jsonify({'explanation': cleaned_explanation, 'is_complete': is_complete})
        
        except Exception as e:
            print(f"CRITICAL: Error generating theory explanation (open) for Q{question_id}: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': 'Fout bij genereren theorie uitleg.', 'status': 'error'}), 500

    except Exception as e:
        print(f"Error in get_theory_explanation_open route for Q{question_id}: {e}")
        return jsonify({'error': 'Interne serverfout.', 'status': 'error'}), 500

@non_language_exam_bp.route('/<subject>/<level>/<time_period>/vraag/<int:question_id>/get_theory_explanation_multiple_gap_choice', methods=['GET'])
def get_theory_explanation_multiple_gap_choice(subject, level, time_period, question_id):
    """Generate a theory explanation for the current question (Non-Language)"""
    # <<< Get model selection from request query parameters >>>
    selected_model = request.args.get('selected_model')
    
    try:
        question_data = get_question_data(subject, level, time_period, question_id)
        if not question_data:
            return jsonify({'error': 'Question not found'}), 404

        # Bepaal welke prompt te gebruiken op basis van vraagtype
        question_type = question_data.get('type', '').lower()
        prompt_text = ""

        if question_type == 'multiple_gap_choice':
            # <<< Verwijzing naar correcte prompt voor MGC theorie >>>
            # Gebruik THEORY_EXPLANATION_PROMPT, niet FEEDBACK_PROMPT_MULTIPLE_GAP_CHOICE
            prompt_text = THEORY_EXPLANATION_PROMPT.format(
                vraag_id=question_id,
                vak=subject,
                niveau=level,
                question_type=question_type,
                exam_question=question_data.get('vraagtekst_html', ''),
                exam_context=question_data.get('context_html', 'Geen context beschikbaar.')
            )
        else:
            # Gebruik generieke hint prompt voor andere (niet-taal) types
            # Let op: HINT_PROMPT_TEMPLATE is erg gericht op MC, misschien aanpassen?
            source_text_snippet = question_data.get('bron_tekst_html', '') # Leeg voor non-language
            if source_text_snippet: source_text_snippet = source_text_snippet[:300] + "..."
            else: source_text_snippet = "N.v.t."
            
            prompt_text = HINT_PROMPT_TEMPLATE.format(
                vraag_id=question_id,
                vak=subject,
                niveau=level,
                exam_question=question_data.get('vraagtekst_html', ''), # Gebruik _html versie
                source_text_content=source_text_snippet, # <<< GEWIJZIGD van source_text_snippet
                options_text="" # Geen MC opties hier
            )

        # Roep Gemini aan
        try:
            # <<< Pass selected_model to configure_genai >>>
            model, error_message = configure_genai(model_name=selected_model)
            if error_message:
                return jsonify({"error": error_message}), 500

            print(f"\nDEBUG (Non-Lang): Calling Gemini for Theory Explanation (MGC) Q{question_id} (Type: {question_type})...")
            full_prompt = SYSTEM_PROMPT + "\n\n" + prompt_text
            response = model.generate_content(full_prompt)
            explanation = response.text
            # <<< DEBUG: Log raw response >>>
            print(f"RAW AI Theory Response (MGC):\n{explanation}\n--- END RAW ---")
            # <<< END DEBUG >>>

            # <<< Convert LaTeX in explanation to MathML >>>
            explanation = convert_latex_to_mathml(explanation)

            # <<< MODIFIED: Check if marker is anywhere in the text >>>
            is_complete = True
            cleaned_explanation = explanation
            if CONTINUATION_MARKER in explanation:
                is_complete = False
                # Remove the marker from the text sent to the frontend (replace first occurrence)
                cleaned_explanation = explanation.replace(CONTINUATION_MARKER, '', 1).strip()
            # <<< END MODIFIED >>>

            print(f"---> Theory Explanation Received (Complete: {is_complete}): {cleaned_explanation[:100]}...")
             # <<< MODIFIED: Return JSON with is_complete flag >>>
            return jsonify({'explanation': cleaned_explanation, 'is_complete': is_complete})

        except Exception as e:
            print(f"CRITICAL: Error generating theory explanation (MGC) for Q{question_id}: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': 'Fout bij genereren theorie uitleg.', 'status': 'error'}), 500

    except Exception as e:
        print(f"Error in get_theory_explanation_multiple_gap_choice route for Q{question_id}: {e}")
        return jsonify({'error': 'Interne serverfout.', 'status': 'error'}), 500

@non_language_exam_bp.route('/<subject>/<level>/<time_period>/vraag/<int:question_id>/get_metaphor_explanation', methods=['GET'])
def get_metaphor_explanation(subject, level, time_period, question_id):
    """Generate a metaphor explanation for the current question (Non-Language)"""
    # <<< Get model selection from request query parameters >>>
    selected_model = request.args.get('selected_model')
    
    try:
        question_data = get_question_data(subject, level, time_period, question_id)
        if not question_data:
            return jsonify({'error': 'Question not found'}), 404

        # Bepaal vraagtype en context
        question_type = question_data.get('type', 'unknown')
        exam_question=question_data.get('vraagtekst_html', '')
        exam_context=question_data.get('context_html', 'Geen context beschikbaar.')
        correct_antwoord_model=question_data.get('correct_antwoord_model', 'Niet beschikbaar')
        
        # Formatteer de prompt
        prompt_text = METAPHOR_EXPLANATION_PROMPT.format(
            vraag_id=question_id,
            vak=subject,
            niveau=level,
            question_type=question_type,
            exam_question=exam_question,
            exam_context=exam_context,
            correct_antwoord_model=correct_antwoord_model
        )

        # Roep Gemini aan
        try:
            # <<< Pass selected_model to configure_genai >>>
            model, error_message = configure_genai(model_name=selected_model)
            if error_message:
                return jsonify({"error": error_message}), 500

            print(f"\nDEBUG (Non-Lang): Calling Gemini for Metaphor Explanation Q{question_id}...")
            full_prompt = SYSTEM_PROMPT + "\n\n" + prompt_text
            response = model.generate_content(full_prompt)
            raw_metaphor_text = response.text 
            print(f"---> RAW Metaphor Received: {raw_metaphor_text[:150]}...")

            # --- Clean up stray characters --- 
            temp_text = raw_metaphor_text.replace(': *', ':') 
            temp_text = temp_text.replace('`', '')
            cleaned_metaphor_text = temp_text
            
            print(f"---> CLEANED Metaphor: {cleaned_metaphor_text[:150]}...")
            return jsonify({'metaphor': cleaned_metaphor_text}) # Return as 'metaphor'
        
        except Exception as e:
            print(f"CRITICAL: Error generating metaphor explanation for Q{question_id}: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': 'Fout bij genereren metafoor uitleg.', 'status': 'error'}), 500

    except Exception as e:
        print(f"Error in get_metaphor_explanation route for Q{question_id}: {e}")
        return jsonify({'error': 'Interne serverfout.', 'status': 'error'}), 500

# <<< NEW ROUTE FOR THEORY CONTINUATION >>>
@non_language_exam_bp.route('/<subject>/<level>/<time_period>/vraag/<int:question_id>/get_theory_continuation', methods=['POST'])
def get_theory_continuation(subject, level, time_period, question_id):
    """Generate the next part of a potentially long theory explanation."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request body'}), 400

        previous_explanation = data.get('previous_explanation')
        selected_model = data.get('selected_model')

        if previous_explanation is None: # Allow empty string, but not None
            return jsonify({'error': 'Missing previous_explanation'}), 400

        # Fetch original question data for context in the prompt
        question_data = get_question_data(subject, level, time_period, question_id)
        if not question_data:
            return jsonify({'error': 'Original question data not found'}), 404
        
        question_type = question_data.get('type', 'unknown')
        exam_question=question_data.get('vraagtekst_html', '')
        exam_context=question_data.get('context_html', 'Geen context beschikbaar.')

        # Format the continuation prompt
        prompt_text = CONTINUE_THEORY_PROMPT.format(
            vraag_id=question_id,
            vak=subject,
            niveau=level,
            question_type=question_type,
            exam_question=exam_question,
            exam_context=exam_context,
            previous_explanation=previous_explanation # Pass the previous part
        )

        # Call Generative AI
        model, error_message = configure_genai(model_name=selected_model)
        if error_message:
            return jsonify({"error": error_message}), 500

        print(f"\nDEBUG (Non-Lang): Calling Gemini for Theory Continuation Q{question_id}...")
        full_prompt = SYSTEM_PROMPT + "\n\n" + prompt_text
        response = model.generate_content(full_prompt)
        explanation_chunk = response.text
        # <<< DEBUG: Log raw response >>>
        print(f"RAW AI Theory Continuation Chunk:\n{explanation_chunk}\n--- END RAW ---")
        # <<< END DEBUG >>>
        
        # Convert potential LaTeX in the new chunk
        explanation_chunk = convert_latex_to_mathml(explanation_chunk)

        # <<< MODIFIED: Check if marker is anywhere in the chunk >>>
        is_complete = True
        cleaned_chunk = explanation_chunk
        if CONTINUATION_MARKER in explanation_chunk:
            is_complete = False
            # Remove the marker from the chunk sent to the frontend (replace first occurrence)
            cleaned_chunk = explanation_chunk.replace(CONTINUATION_MARKER, '', 1).strip()
        # <<< END MODIFIED >>>

        print(f"---> Theory Continuation Chunk Received (Complete: {is_complete}): {cleaned_chunk[:100]}...")
        # Return the chunk and completion status
        return jsonify({'explanation_chunk': cleaned_chunk, 'is_complete': is_complete})

    except Exception as e:
        print(f"CRITICAL: Error generating theory continuation for Q{question_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Fout bij genereren vervolg van theorie uitleg.', 'status': 'error'}), 500