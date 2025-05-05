import re
from latex2mathml.converter import convert # Import the converter
import datetime # Importeer datetime
import logging # <<< ADDED for logging

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
from utils.data_loader import list_available_exams, get_question_data, get_max_question_id
# Importeer relevante prompts (inclusief MC voor non-language)
from non_language_prompts import (
    SYSTEM_PROMPT,
    FEEDBACK_PROMPT_MC,
    FEEDBACK_PROMPT_NON_LANGUAGE_OPEN,
    FEEDBACK_PROMPT_CALCULATION,
    HINT_PROMPT_TEMPLATE,
    FOLLOW_UP_PROMPT_TEMPLATE,
    THEORY_EXPLANATION_PROMPT, # General theory prompt
    METAPHOR_EXPLANATION_PROMPT, # <<< ADDED IMPORT
    CONTINUE_THEORY_PROMPT, # <<< ADDED IMPORT
)
# Import language-specific prompts if needed (though likely not for this BP)
# from prompts_language import ... # Example

# Configure Google Generative AI with API key
api_key = os.getenv('GEMINI_API_KEY')
if api_key:
    genai.configure(api_key=api_key)
else:
    print("WARNING: GEMINI_API_KEY not found in environment variables")

# Definieer de lijst met niet-taalvakken die deze blueprint behandelt
non_language_subjects = ['wiskunde', 'natuurkunde', 'scheikunde', 'economie', 'aardrijkskunde', 'geschiedenis', 'biologie', 'nask', 'nask1', 'maatschappijwetenschappen', 'maatschappijkunde']

# Create blueprint voor niet-taalvakken
non_language_exam_bp = Blueprint('non_language_exam', __name__, template_folder='../templates') # Template folder verwijzing toevoegen

# --- Function to convert LaTeX ($$...$$ and $...$) to MathML using re.sub --- 
def convert_latex_to_mathml(html_content):
    if not html_content or ('$' not in html_content):
        return html_content # Return original if no dollar signs found

    # --- Helper for replacing display math ($$...$$) ---
    def replace_display_latex(match):
        latex_code = match.group(1).strip()
        try:
            mathml_output = convert(latex_code, display="block") 
            # Wrap in a div to ensure block display and allow potential styling
            return f'<div class="mathml-block">{mathml_output}</div>' 
        except Exception as e:
            print(f"Error converting DISPLAY LaTeX to MathML: {e}. LaTeX: {latex_code}")
            return match.group(0) # Return original $$...$$ on error

    # --- Helper for replacing inline math ($...$) ---
    def replace_inline_latex(match):
        latex_code = match.group(1).strip()
        # Avoid converting things that are likely just currency
        if re.fullmatch(r'\d+([.,]\d+)?', latex_code):
             return match.group(0) # Return original if it looks like currency
        try:
            mathml_output = convert(latex_code, display="inline") 
            # Wrap in a span for potential styling
            return f'<span class="mathml-inline">{mathml_output}</span>' 
        except Exception as e:
            print(f"Error converting INLINE LaTeX to MathML: {e}. LaTeX: {latex_code}")
            return match.group(0) # Return original $...$ on error

    # --- Apply replacements --- 
    # IMPORTANT: Process display math ($$...$$) FIRST to avoid conflicts with single $
    processed_content = re.sub(r'\$\$(.*?)\$\$', replace_display_latex, html_content, flags=re.DOTALL)
    # Then process inline math ($...$), ensuring we don't match within already processed blocks or $$...$$
    # Use negative lookbehind/lookahead to avoid matching escaped dollars or parts of display math
    processed_content = re.sub(r'(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)', replace_inline_latex, processed_content, flags=re.DOTALL)

    return processed_content
# --- End LaTeX conversion function --- 

@non_language_exam_bp.route('/<subject>/<level>/<time_period>/vraag/<int:question_id>')
def toon_vraag(subject, level, time_period, question_id):
    """Display a specific question for non-language exams"""
    subject_lower = subject.lower()

    # <<< DEBUG PRINT >>>
    print(f"--- DEBUG (non_lang): Checking subject_lower: '{subject_lower}' ---")
    print(f"--- DEBUG (non_lang): non_language_subjects: {non_language_subjects} ---")
    # <<< END DEBUG PRINT >>>

    # Check if the subject is actually non-language, redirect if not (shouldn't happen normally)
    if subject_lower not in non_language_subjects:
        # Check if it's a known language subject instead
        if subject_lower in language_subjects: # Assuming language_subjects is imported or accessible
            return redirect(url_for('exam.toon_vraag',
                                    subject=subject, level=level,
                                    time_period=time_period, question_id=question_id))
        else:
            # Subject is completely unknown
            print(f"Warning: Unknown subject '{subject}' routed to non-language blueprint. Redirecting to select.")
            return redirect(url_for('exam.select_exam_page'))

    try:
        vraag_data = get_question_data(subject, level, time_period, question_id)
        if not vraag_data:
            print(f"Warning: Question data not found for non-language {subject}/{level}/{time_period}/{question_id}")
            return redirect(url_for('exam.select_exam_page'))

        max_vraag_id = get_max_question_id(subject, level, time_period)

        # --- Process HTML fields to fix image paths ---
        fields_to_process = ['context_html', 'vraagtekst_html', 'correct_antwoord_model']
        for field in fields_to_process:
            if field in vraag_data and isinstance(vraag_data[field], str):
                original_html = vraag_data[field]
                # Use regex to find src="filename.ext" and replace it
                # This pattern looks for src followed by = and quotes, capturing the filename
                # It specifically avoids replacing URLs that already start with http:// or https://
                vraag_data[field] = re.sub(
                    r'src="(?!(?:http|https))([^"]+)"',
                    lambda match: f'src="{url_for("static", filename=f"images/{match.group(1)}")}"',
                    original_html
                )
                # Debug print to see the change
                if original_html != vraag_data[field]:
                    print(f"DEBUG: Replaced image path in field '{field}' for Q{question_id}")
                    print(f"  Original: {original_html[:100]}...") # Print first 100 chars
                    print(f"  Replaced: {vraag_data[field][:150]}...") # Print first 150 chars

        # --- End image path processing ---

    except Exception as e:
        print(f"Error loading non-language question data or max_id for {subject}/{level}/{time_period}/{question_id}: {e}")
        return render_template('error.html', message="Kon vraaggegevens niet laden."), 500

    # Generate URLs for API endpoints within THIS blueprint ('non_language_exam')
    try:
        get_feedback_url = url_for('non_language_exam.get_feedback', subject=subject, level=level, time_period=time_period, question_id=question_id)
        get_hint_url = url_for('non_language_exam.get_hint', subject=subject, level=level, time_period=time_period, question_id=question_id)
        get_follow_up_url = url_for('non_language_exam.get_follow_up', subject=subject, level=level, time_period=time_period, question_id=question_id)
        base_question_url = url_for('non_language_exam.toon_vraag', subject=subject, level=level, time_period=time_period, question_id=0)[:-1]

        # --- Determine the correct Theory Explanation URL based on question type ---
        question_type = vraag_data.get('type', '').lower()
        get_theory_url = None # Default to None
        if question_type == 'calculation':
            get_theory_url = url_for('non_language_exam.get_theory_explanation_calculation', subject=subject, level=level, time_period=time_period, question_id=question_id)
        elif question_type == 'open_non_language' or question_type == 'mc': # MC uses the 'open' explanation route now
             get_theory_url = url_for('non_language_exam.get_theory_explanation_open', subject=subject, level=level, time_period=time_period, question_id=question_id)
        elif question_type == 'multiple_gap_choice':
             get_theory_url = url_for('non_language_exam.get_theory_explanation_multiple_gap_choice', subject=subject, level=level, time_period=time_period, question_id=question_id)
        else:
            print(f"WARN: No specific theory explanation route found for type '{question_type}' in Q{question_id}")
        # --- End Theory URL determination ---

    except Exception as e:
         print(f"Error generating URLs for non-language question page: {e}")
         return render_template('error.html', message="Interne fout bij het genereren van links."), 500

    # <<< DEBUG PRINT: Check keys in vraag_data before rendering >>>
    print(f"--- DEBUG Keys in non-language vraag_data for Q{question_id} before rendering: {list(vraag_data.keys()) if vraag_data else 'None'} ---")
    # <<< END DEBUG PRINT >>>

    # Render the NON-LANGUAGE specific template
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
                           base_question_url=base_question_url,
                           correct_antwoord_model=vraag_data.get('correct_antwoord_model'),
                           get_theory_url=get_theory_url)

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
    
    # <<< DEBUG: Print the model name being passed to GenerativeModel >>>
    # print(f"DEBUG configure_genai: Initializing GenerativeModel with model_name='{selected_model_name}'")
    # <<< END DEBUG >>>
    
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
    request_question_type = request.json.get('question_type')  # Extract but not used - prevents KeyError
    
    if user_answer is None: # Check for None, not just falsiness
        return jsonify({'error': 'No answer provided'}), 400
    
    try:
        question_data = get_question_data(subject, level, time_period, question_id)
        if not question_data:
            return jsonify({'error': 'Question not found'}), 404
    except Exception as e:
        print(f"Error loading question data in get_feedback (non-lang): {e}")
        return jsonify({'error': 'Failed to load question data.', 'status': 'error'}), 500

    # Helper function to escape curly braces in text content
    def escape_braces(text):
        if not text:
            return ""
        return str(text).replace('{', '{{').replace('}', '}}')

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
        options_text_raw = "\n".join([f"{opt.get('id', '?')}: {opt.get('text', '')}" for opt in options_list])
        
        # Find the text for the user's answer - escape braces in all text fields
        user_answer_text_found = ''
        for opt in options_list:
            if str(opt.get('id', '')) == str(user_answer):
                user_answer_text_found = opt.get('text', '')
                break
        
        # Escape curly braces in all text fields to prevent format errors
        escaped_exam_question = escape_braces(question_data.get('vraagtekst_html', ''))
        escaped_source_text = escape_braces(source_text_snippet)
        escaped_options_text = escape_braces(options_text_raw)
        escaped_correct_answer = escape_braces(question_data.get('correct_answer', ''))
        escaped_user_answer_text = escape_braces(user_answer_text_found)

        # <<< DEBUG: Print values being passed to format >>>
        # print("--- DEBUG: Formatting FEEDBACK_PROMPT_MC ---")
        # print(f"  vraag_id: {question_id}")
        # print(f"  exam_question (escaped, first 100): {escaped_exam_question[:100]}...")
        # print(f"  source_text_snippet (escaped, first 100): {escaped_source_text[:100]}...")
        # print(f"  options_text (escaped, first 200): {escaped_options_text[:200]}...")
        # print(f"  correct_answer (escaped): {escaped_correct_answer}")
        # print(f"  max_score: {question_data.get('max_score', 1)}")
        # print(f"  user_answer_key: {user_answer}")
        # print(f"  user_answer_text (escaped, first 100): {escaped_user_answer_text[:100]}...")
        # print(f"  niveau: {level}")
        # print(f"  vak: {subject}")
        # print("--- END DEBUG Format Values ---")
        # <<< END DEBUG >>>

        prompt = FEEDBACK_PROMPT_MC.format(
            vraag_id=question_id,
            exam_question=escaped_exam_question, 
            source_text_snippet=escaped_source_text,
            options_text=escaped_options_text, 
            correct_answer=escaped_correct_answer, 
            max_score=question_data.get('max_score', 1),
            user_answer_key=user_answer,
            user_answer_text=escaped_user_answer_text, 
            niveau=level,
            vak=subject
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
        
        # <<< USE FEEDBACK_PROMPT_CALCULATION as fallback for MGC feedback prompt (since specific MGC feedback prompt doesn't exist) >>>
        # This might not be ideal, but prevents import errors. Needs a dedicated prompt later.
        print("WARN: Using FEEDBACK_PROMPT_CALCULATION for Multiple Gap Choice feedback as specific prompt is missing.")
        prompt = FEEDBACK_PROMPT_CALCULATION.format(
            vraag_id=question_id,
            vak=subject,
            niveau=level,
            exam_question=question_data.get('vraagtekst_html', ''), 
            # Pass formatted user answers instead of raw user_antwoord
            user_antwoord=user_answers_formatted, 
            # Pass gap details as correct answer model (approximation)
            correct_antwoord=gaps_details, 
            max_score=question_data.get('max_score', 1)
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
        # <<< DEBUG: Print model and prompt before calling generate_content >>>
        # print(f"\\nDEBUG get_feedback (Non-Lang): Attempting API call for Q{question_id} type {question_type}")
        # print(f"  - Using Model: {model.model_name if hasattr(model, 'model_name') else 'Unknown Model Object'}") # Print model name if available
        # print(f"  - Full Prompt (first 500 chars):\\n{prompt[:500]}...")
        # <<< END DEBUG >>>

        response = model.generate_content(prompt)
        raw_feedback_text = response.text # Get the raw text first
        print(f"\nDEBUG (Non-Lang): Received RAW feedback from Gemini for Q{question_id}:")
        print(raw_feedback_text)

        # --- Clean up stray characters BEFORE assigning to cleaned_feedback_text --- 
        temp_text = raw_feedback_text.replace(': *', ':') # Remove stray asterisk after colon+space
        temp_text = temp_text.replace('`', '') # Remove backticks
        cleaned_feedback_text = temp_text # Use the cleaned text
        
        # --- DEBUG: Print the cleaned feedback (Now should be same as RAW, minus strays) --- 
        # print(f"\\nDEBUG (Non-Lang): CLEANED feedback for Q{question_id} (Expecting ** from AI):")
        # print(cleaned_feedback_text)
        # print("--- END CLEANED DEBUG ---\\n")

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
        
        # <<< REMOVE LEADING ASTERISKS from feedback lines >>>
        parsed_feedback = re.sub(r'^\*\s+', '', parsed_feedback, flags=re.MULTILINE)

        return jsonify({'feedback': parsed_feedback, 'status': ai_determined_status})
    
    # <<< DEBUG: Catch specific exceptions during API call >>>
    except Exception as e:
        print(f"CRITICAL ERROR in get_feedback (Non-Lang) during model.generate_content for Q{question_id}:")
        print(f"  - Error Type: {type(e).__name__}")
        print(f"  - Error Details: {e}")
        # Optionally print traceback for more detail
        # import traceback
        # traceback.print_exc()
        return jsonify({"feedback": "Er is een fout opgetreden bij het communiceren met de AI. Probeer het later opnieuw.", "status": "error"}), 500
    # <<< END DEBUG >>>

@non_language_exam_bp.route('/<subject>/<level>/<time_period>/vraag/<int:question_id>/get_hint', methods=['GET'])
def get_hint(subject, level, time_period, question_id):
    """Generate a hint for the current question (Non-Language)"""
    # <<< Get model selection from request query parameters >>>
    selected_model = request.args.get('selected_model') 
    request_question_type = request.args.get('question_type')  # Extract but not used - prevents KeyError if frontend sends it
    
    try:
        question_data = get_question_data(subject, level, time_period, question_id)
        if not question_data:
            return jsonify({'error': 'Question not found'}), 404

        # Helper function to escape curly braces in text content
        def escape_braces(text):
            if not text:
                return ""
            return str(text).replace('{', '{{').replace('}', '}}')

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

            # Fallback to HINT_PROMPT_TEMPLATE since FEEDBACK_PROMPT_MULTIPLE_GAP_CHOICE may not exist
            prompt_text = HINT_PROMPT_TEMPLATE.format(
                vraag_id=question_id,
                vak=subject,
                niveau=level,
                exam_question=escape_braces(question_data.get('vraagtekst_html', '')),
                source_text_snippet=escape_braces("N.v.t."),
                options_text=escape_braces(gaps_details_for_hint)
            )
        else:
            # Gebruik generieke hint prompt voor andere (niet-taal) types
            # Let op: HINT_PROMPT_TEMPLATE is erg gericht op MC, misschien aanpassen?
            # <<< CORRECTIE: Gebruik 'bron_tekst_html' of 'context_html' voor source_text_content >>>
            source_text_snippet = question_data.get('bron_tekst_html', question_data.get('context_html', '')) # Use bron_tekst or context as source
            if source_text_snippet: 
                source_text_snippet = source_text_snippet[:300] + "..." # Truncate if exists
            else: 
                source_text_snippet = "N.v.t." # Set to N.v.t. if neither exists
            
            prompt_text = HINT_PROMPT_TEMPLATE.format(
                vraag_id=question_id,
                vak=subject,
                niveau=level,
                exam_question=escape_braces(question_data.get('vraagtekst_html', '')), # Gebruik _html versie
                source_text_snippet=escape_braces(source_text_snippet), # <<< CORRECTED KEY to match prompt template and error
                options_text=escape_braces("") # Geen MC opties hier
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
    request_question_type = request.json.get('question_type')  # Extract but not used - prevents KeyError if frontend sends it
    
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
        exam_question=exam_question_text, # Gebruik _html versie
        source_text_snippet=source_text_snippet,
        correct_answer=correct_answer_model, # Gebruik correct_antwoord_model
        previous_feedback=safe_previous_feedback, # Use escaped version
        user_follow_up_question=follow_up_question # <<< CORRECTED KEY
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
                context=question_data.get('context_html', 'Geen context beschikbaar.')
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
                source_text_snippet=source_text_snippet, # <<< CORRECTED KEY to match prompt template and error
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

        # <<< ALWAYS use the general THEORY_EXPLANATION_PROMPT >>>
        prompt_text = THEORY_EXPLANATION_PROMPT.format(
            vraag_id=question_id, # Keep vraag_id for reference if needed by prompt internally
            vak=subject,
            niveau=level,
            context=question_data.get('context_html', 'Geen context beschikbaar.')
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

            # <<< Clean up text BEFORE converting LaTeX >>> 
            temp_text = explanation.replace(': *', ':').replace('`', '')
            explanation_clean = temp_text

            # <<< Convert LaTeX in explanation to MathML >>>
            explanation_final = convert_latex_to_mathml(explanation_clean)

            # <<< REMOVE LEADING ASTERISKS from lines >>>
            explanation_final = re.sub(r'^\*\s+', '', explanation_final, flags=re.MULTILINE)

            # <<< MODIFIED: Check if marker is anywhere in the text >>>
            is_complete = True
            cleaned_explanation = explanation_final
            if CONTINUATION_MARKER in explanation_final:
                is_complete = False
                # Remove the marker from the text sent to the frontend (replace first occurrence)
                cleaned_explanation = explanation_final.replace(CONTINUATION_MARKER, '', 1).strip()
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

        # <<< ALWAYS use the general THEORY_EXPLANATION_PROMPT >>>
        prompt_text = THEORY_EXPLANATION_PROMPT.format(
            vraag_id=question_id, # Keep vraag_id for reference if needed by prompt internally
            vak=subject,
            niveau=level,
            context=question_data.get('context_html', 'Geen context beschikbaar.')
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

            # <<< Clean up text BEFORE converting LaTeX >>>
            temp_text = explanation.replace(': *', ':').replace('`', '')
            explanation_clean = temp_text

            # <<< Convert LaTeX in explanation to MathML >>>
            explanation_final = convert_latex_to_mathml(explanation_clean)

            # <<< REMOVE LEADING ASTERISKS from lines >>>
            explanation_final = re.sub(r'^\*\s+', '', explanation_final, flags=re.MULTILINE)

            # <<< MODIFIED: Check if marker is anywhere in the text >>>
            is_complete = True
            cleaned_explanation = explanation_final
            if CONTINUATION_MARKER in explanation_final:
                is_complete = False
                # Remove the marker from the text sent to the frontend (replace first occurrence)
                cleaned_explanation = explanation_final.replace(CONTINUATION_MARKER, '', 1).strip()
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

# <<< START: General Theory Explanation Route (Fallback) >>>
@non_language_exam_bp.route('/<subject>/<level>/<time_period>/vraag/<int:question_id>/get_theory_explanation', methods=['GET'])
def get_theory_explanation_general(subject, level, time_period, question_id):
    """Generate a general theory explanation for the current non-language question (fallback)."""
    selected_model = request.args.get('selected_model')
    print(f"DEBUG: General theory route hit for Q{question_id}, model: {selected_model}")

    try:
        question_data = get_question_data(subject, level, time_period, question_id)
        if not question_data:
            return jsonify({'error': 'Vraag niet gevonden'}), 404

        # Use THEORY_EXPLANATION_PROMPT instead of THEORY_PROMPT_OPEN_NON_LANGUAGE
        prompt_text = THEORY_EXPLANATION_PROMPT.format(
            vraag_id=question_id,
            vak=subject,
            niveau=level,
            context=question_data.get('context_html', 'Geen context beschikbaar.')
        )

        model, error_message = configure_genai(model_name=selected_model)
        if error_message:
            return jsonify({"error": error_message}), 500

        print(f"\nDEBUG (Non-Lang): Calling Gemini for GENERAL Theory Q{question_id}...")
        full_prompt = SYSTEM_PROMPT + "\n\n" + prompt_text
        response = model.generate_content(full_prompt)
        explanation_raw = response.text
        print(f"---> General Theory Received (Raw): {explanation_raw[:100]}...")
        
        # Clean up text (remove backticks, etc.)
        temp_text = explanation_raw.replace(': *', ':').replace('`', '')
        explanation_clean = temp_text

        # Convert LaTeX in explanation to MathML if needed (optional but good for math)
        explanation_final = convert_latex_to_mathml(explanation_clean)

        # <<< REMOVE LEADING ASTERISKS from lines (attempt 2) >>>
        explanation_final = re.sub(r'^\*\s+', '', explanation_final, flags=re.MULTILINE)

        return jsonify({'explanation': explanation_final})

    except Exception as e:
        print(f"CRITICAL: Error generating GENERAL theory explanation for Q{question_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Fout bij genereren algemene theorie uitleg.', 'status': 'error'}), 500
# <<< END: General Theory Explanation Route >>>

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
        # <<< USE THE CORRECT METAPHOR PROMPT >>>
        prompt_text = METAPHOR_EXPLANATION_PROMPT.format(
            vraag_id=question_id,
            vak=subject,
            niveau=level,
            # question_type=question_type, # Not needed by this prompt
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
            
            # <<< Convert LaTeX in metaphor text >>>
            final_metaphor_text = convert_latex_to_mathml(cleaned_metaphor_text)

            # <<< REMOVE LEADING ASTERISKS from lines >>>
            final_metaphor_text = re.sub(r'^\*\s+', '', final_metaphor_text, flags=re.MULTILINE)

            print(f"---> CLEANED Metaphor: {final_metaphor_text[:150]}...")
            return jsonify({'metaphor': final_metaphor_text}) # Return as 'metaphor'
        
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
        # correct_antwoord_model=question_data.get('correct_antwoord_model', 'Niet beschikbaar') # Not needed for continuation prompt

        # Format the continuation prompt
        # <<< USE THE CORRECT CONTINUATION PROMPT >>>
        prompt_text = CONTINUE_THEORY_PROMPT.format(
            vraag_id=question_id,
            vak=subject,
            niveau=level,
            # question_type=question_type, # Not needed
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

# <<< START: Issue Reporting Route >>>
# Set up logging for issue reports
log_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs', 'issue_reports.log')
os.makedirs(os.path.dirname(log_file_path), exist_ok=True) # Ensure logs directory exists

issue_logger = logging.getLogger('issue_reporter')
issue_logger.setLevel(logging.INFO)
# Prevent adding multiple handlers if blueprint reloads in debug mode
if not issue_logger.handlers:
    file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    file_handler.setFormatter(formatter)
    issue_logger.addHandler(file_handler)

@non_language_exam_bp.route('/report_issue', methods=['POST'])
def report_issue():
    """Logs reported issues with questions to a file."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request body'}), 400

        subject = data.get('subject', 'N/A')
        level = data.get('level', 'N/A')
        time_period = data.get('time_period', 'N/A')
        question_id = data.get('question_id', 'N/A')
        # comment = data.get('comment', '') # Add if comment field is implemented later

        log_message = f"Issue reported for: Subject={subject}, Level={level}, TimePeriod={time_period}, QuestionID={question_id}"
        # if comment:
        #     log_message += f", Comment: {comment}"

        issue_logger.info(log_message)
        print(f"DEBUG: Logged issue report: {log_message}") # Also print to console for immediate feedback

        return jsonify({'status': 'success', 'message': 'Issue reported successfully'}), 200

    except Exception as e:
        print(f"CRITICAL: Error in /report_issue route: {e}")
        import traceback
        traceback.print_exc()
        # Also log the error to the issue log if possible
        try:
            issue_logger.error(f"Failed to process issue report. Error: {e}", exc_info=True)
        except Exception as log_e:
            print(f"CRITICAL: Failed to even log the error in report_issue: {log_e}")
            
        return jsonify({'status': 'error', 'error': 'Internal server error processing report'}), 500
# <<< END: Issue Reporting Route >>>