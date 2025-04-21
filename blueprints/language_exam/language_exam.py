import os
import google.generativeai as genai
from flask import Blueprint, render_template, request, jsonify, url_for
# Importeer prompts specifiek voor taalexamens
from prompts import (
    SYSTEM_PROMPT,
    FEEDBACK_PROMPT_MC,
    FEEDBACK_PROMPT_WEL_NIET,
    FEEDBACK_PROMPT_OPEN,
    FEEDBACK_PROMPT_CITEER,
    FEEDBACK_PROMPT_NUMMERING,
    FEEDBACK_PROMPT_GAP_FILL,
    FEEDBACK_PROMPT_ORDER,
    HINT_PROMPT_TEMPLATE,
    FOLLOW_UP_PROMPT_TEMPLATE,
    THEORY_EXPLANATION_PROMPT
)
from utils.data_loader import list_available_exams, get_question_data, get_max_question_id

# Create blueprint for language exams
language_exam_bp = Blueprint('language_exam', __name__, template_folder='../templates')

# <<< MODIFIED: Accept optional model_name >>>
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
        print(f"DEBUG (Lang): Using selected model: {selected_model_name}") # Debug log
    else:
        if model_name:
            print(f"DEBUG (Lang): Received invalid model name '{model_name}'. Falling back to default: {default_model}")
        else:
            print(f"DEBUG (Lang): No model name provided. Using default: {default_model}")

    # <<< Dynamically set generation_config based on model >>>
    generation_config = {
        "temperature": 0.2,
        "top_p": 1,
        "top_k": 1,
        "max_output_tokens": fixed_max_tokens # Start with fallback
    }

    if selected_model_name == 'gemini-2.5-flash-preview-04-17': # <<< Use correct full name
        try:
            # Attempt to get the model details to find its limit
            model_info = genai.get_model(selected_model_name)
            limit = model_info.output_token_limit
            if limit:
                budget = int(limit * 0.90) # Calculate 90% budget
                generation_config["max_output_tokens"] = budget
                print(f"DEBUG (Lang): Setting max_output_tokens for {selected_model_name} to 90% budget: {budget} (Limit: {limit})")
            else:
                print(f"WARN (Lang): Could not retrieve output_token_limit for {selected_model_name}. Using fallback max_output_tokens: {fixed_max_tokens}")
        except Exception as e:
            print(f"ERROR (Lang): Failed to get model info for {selected_model_name}: {e}. Using fallback max_output_tokens: {fixed_max_tokens}")
    else:
        # For gemini-2.0-flash or other future models, use the fixed default
        print(f"DEBUG (Lang): Using fixed max_output_tokens for {selected_model_name}: {fixed_max_tokens}")

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

@language_exam_bp.route('/<subject>/<level>/<time_period>/vraag/<int:question_id>/get_feedback', methods=['POST'])
def get_feedback(subject, level, time_period, question_id):
    """Generate feedback for a user's answer (Language Exam)"""
    # <<< Get model selection from request >>>
    user_answer = request.json.get('answer')
    selected_model = request.json.get('selected_model') # Get selected model

    if user_answer is None:
        return jsonify({'error': 'No answer provided'}), 400
    
    try:
        question_data = get_question_data(subject, level, time_period, question_id)
        if not question_data:
            return jsonify({'error': 'Question not found'}), 404
    except Exception as e:
        print(f"Error loading question data in get_feedback (lang): {e}")
        return jsonify({'error': 'Failed to load question data.', 'status': 'error'}), 500

    prompt = ""
    question_type = question_data.get('type', '').lower()
    source_text_snippet = question_data.get('bron_tekst_html', 'Geen brontekst beschikbaar.')
    if len(source_text_snippet) > 300:
        source_text_snippet = source_text_snippet[:300] + "..."

    # === Prompt Selection for Language Exams ===
    if question_type == 'mc':
        options_text = "\n".join([f"{k}: {v}" for k, v in question_data.get('opties', {}).items()])
        # Find the text for the user's answer
        user_answer_text = question_data.get('opties', {}).get(user_answer, '') 
        prompt = FEEDBACK_PROMPT_MC.format(
            vraag_id=question_id,
            exam_question=question_data.get('vraagtekst', ''),
            source_text_snippet=source_text_snippet,
            options_text=options_text,
            correct_answer=question_data.get('correct_antwoord', ''),
            max_score=question_data.get('max_score', 1),
            user_answer_key=user_answer,
            user_answer_text=user_answer_text, # Use the found text
            niveau=level,
            vak=subject,
            language="English" if subject == 'engels' else "German" if subject == 'duits' else "French" if subject == 'frans' else "Dutch" # Default to Dutch?
        )
    # ... (add other language question type prompts similarly)
    elif question_type == 'wel_niet':
        beweringen_text = "\n".join([f"- {b}" for b in question_data.get('beweringen', [])])
        # Verwacht user_answer als dictionary: {"bewering_index": "Wel"/"Niet"}
        user_answers_formatted = "\n".join([f"- Bewering {idx+1}: {ans}" for idx, ans in user_answer.items()])
        prompt = FEEDBACK_PROMPT_WEL_NIET.format(
            vraag_id=question_id,
            exam_question=question_data.get('vraagtekst', ''),
            beweringen_text=beweringen_text,
            correct_antwoord=str(question_data.get('correct_antwoord', '')), # Ensure string
            max_score=question_data.get('max_score', 1),
            user_answers_formatted=user_answers_formatted,
            niveau=level,
            vak=subject,
            language="English" # Example, adjust as needed
        )
    elif question_type == 'open' or question_type == 'open_nl':
         prompt = FEEDBACK_PROMPT_OPEN.format(
            vraag_id=question_id,
            exam_question=question_data.get('vraagtekst', ''),
            source_text_snippet=source_text_snippet,
            user_answer=user_answer,
            correct_answer=question_data.get('correct_antwoord', ''),
            max_score=question_data.get('max_score', 1),
            niveau=level,
            vak=subject,
            language="English" # Adjust
        )
    elif question_type == 'citeer':
         prompt = FEEDBACK_PROMPT_CITEER.format(
            vraag_id=question_id,
            exam_question=question_data.get('vraagtekst', ''),
            source_text_snippet=source_text_snippet,
            user_answer=user_answer,
            correct_answer=question_data.get('correct_antwoord', ''),
            max_score=question_data.get('max_score', 1),
            niveau=level,
            vak=subject,
            language="English" # Adjust
        )
    # ... Add other language-specific types like nummering, gap_fill, order
    else:
        # Fallback or error for unsupported types in language blueprint
        print(f"Warning: Unsupported question type '{question_type}' in language blueprint for Q{question_id}")
        return jsonify({'feedback': f'Feedback wordt nog niet ondersteund voor vraagtype "{question_type}".', 'status': 'unknown'})
    # === End Prompt Selection ===

    # --- Initial Answer Status --- 
    status = 'pending'
    try:
        correct_answer = question_data.get('correct_antwoord')
        if question_type == 'mc' and isinstance(user_answer, str) and isinstance(correct_answer, str): 
            status = 'correct' if user_answer.lower() == correct_answer.lower() else 'incorrect'
        # Add logic for other auto-gradable types if needed
    except Exception as e:
        print(f"Error determining initial status for lang question {question_id}: {e}")
        status = 'error'
    # --- End Initial Status --- 

    # --- Generative AI Call ---
    # <<< Pass selected_model to configure_genai >>>
    model, error = configure_genai(model_name=selected_model)
    if error:
        return jsonify({"feedback": error, "status": "error"}), 500

    try:
        print(f"\nDEBUG (Lang): Calling Gemini for Q{question_id} type {question_type}...")
        full_prompt = SYSTEM_PROMPT + "\n\n" + prompt
        response = model.generate_content(full_prompt)
        
        # Process feedback text (remove backticks, potentially parse status)
        raw_feedback_text = response.text
        cleaned_feedback_text = raw_feedback_text.replace('`', '')
        
        # Parse status from feedback (similar to non-language)
        ai_determined_status = status 
        feedback_lower_strip = cleaned_feedback_text.lower().strip()
        if feedback_lower_strip.startswith('**correct:**') or (feedback_lower_strip.startswith('correct:') and ai_determined_status == 'pending'):
            ai_determined_status = 'correct'
        elif feedback_lower_strip.startswith('**incorrect:**') or (feedback_lower_strip.startswith('incorrect:') and ai_determined_status == 'pending'):
            ai_determined_status = 'incorrect'
        elif feedback_lower_strip.startswith('**gedeeltelijk:**') or (feedback_lower_strip.startswith('gedeeltelijk:') and ai_determined_status == 'pending'):
            ai_determined_status = 'partial'
        # Add more statuses if applicable
        else:
            if ai_determined_status == 'pending':
                print(f"Warning: AI feedback (Lang) Q{question_id} did not start with expected status. Status remains pending.")
        
        return jsonify({'feedback': cleaned_feedback_text, 'status': ai_determined_status})

    except Exception as e:
        print(f"Error generating language feedback: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Error generating AI feedback'}), 500

@language_exam_bp.route('/<subject>/<level>/<time_period>/vraag/<int:question_id>/get_hint', methods=['GET'])
def get_hint(subject, level, time_period, question_id):
    """Generate a hint for the current question (Language Exam)"""
    # <<< Get model selection from request query parameters >>>
    selected_model = request.args.get('selected_model') 
    
    try:
        question_data = get_question_data(subject, level, time_period, question_id)
        if not question_data:
            return jsonify({'error': 'Question not found'}), 404

        # Simplified prompt for language hints, might need refinement
        source_text_snippet = question_data.get('bron_tekst_html', '')
        if len(source_text_snippet) > 300:
            source_text_snippet = source_text_snippet[:300] + "..."
        else:
            source_text_snippet = "N.v.t." if not source_text_snippet else source_text_snippet
            
        options_text = ""
        if question_data.get('type', '').lower() == 'mc':
             options_text = "\n".join([f"{k}: {v}" for k, v in question_data.get('opties', {}).items()])
             
        prompt_text = HINT_PROMPT_TEMPLATE.format(
            vraag_id=question_id,
            vak=subject,
            niveau=level,
            exam_question=question_data.get('vraagtekst', ''), 
            source_text_snippet=source_text_snippet,
            options_text=options_text 
        )

        # Roep Gemini aan
        try:
            # <<< Pass selected_model to configure_genai >>>
            model, error_message = configure_genai(model_name=selected_model)
            if error_message:
                return jsonify({"error": error_message}), 500

            print(f"\nDEBUG (Lang): Calling Gemini for Hint Q{question_id}..." )
            full_prompt = SYSTEM_PROMPT + "\n\n" + prompt_text
            response = model.generate_content(full_prompt)
            hint = response.text.replace('`', '') # Clean hint
            print(f"---> Hint Received: {hint[:100]}...")
            return jsonify({'hint': hint})
        
        except Exception as e:
            print(f"CRITICAL: Error generating hint for Lang Q{question_id}: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': 'Fout bij genereren hint.', 'status': 'error'}), 500

    except Exception as e:
        print(f"Error in get_hint route for Lang Q{question_id}: {e}")
        return jsonify({'error': 'Interne serverfout.', 'status': 'error'}), 500

@language_exam_bp.route('/<subject>/<level>/<time_period>/vraag/<int:question_id>/get_follow_up', methods=['POST'])
def get_follow_up(subject, level, time_period, question_id):
    """Generate a follow-up answer (Language Exam)"""
    # <<< Get model selection from request >>>
    follow_up_question = request.json.get('question')
    selected_model = request.json.get('selected_model') # Get selected model
    
    if not follow_up_question:
        return jsonify({'error': 'No question provided'}), 400
    
    previous_feedback = request.json.get('feedback')
    question_data = get_question_data(subject, level, time_period, question_id)
    if not question_data:
        return jsonify({'error': 'Question not found'}), 404
    
    safe_previous_feedback = str(previous_feedback or '').replace('{', '{{}}').replace('}', '}}')
    source_text_snippet = question_data.get('bron_tekst_html', '') 
    if source_text_snippet: source_text_snippet = source_text_snippet[:300] + "..."
    else: source_text_snippet = "N.v.t."

    prompt = FOLLOW_UP_PROMPT_TEMPLATE.format(
        vraag_id=question_id,
        vak=subject,
        niveau=level,
        exam_question=question_data.get('vraagtekst', ''),
        source_text_snippet=source_text_snippet,
        correct_answer=question_data.get('correct_antwoord', ''),
        previous_feedback=safe_previous_feedback,
        follow_up_question=follow_up_question 
    )
    
    try:
        # <<< Pass selected_model to configure_genai >>>
        model, error_message = configure_genai(model_name=selected_model)
        if error_message:
            return jsonify({"error": error_message}), 500

        full_prompt = SYSTEM_PROMPT + "\n\n" + prompt
        response = model.generate_content(full_prompt)
        answer = response.text.replace('`', '') # Clean answer
        
        print(f"\nDEBUG FOLLOW-UP (Lang) Q{question_id}: RAW AI Answer text:")
        print(answer)
        
        return jsonify({'answer': answer})
        
    except Exception as e:
        print(f"CRITICAL Error generating language follow-up answer for Q{question_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error generating follow-up answer: {str(e)}'}), 500

@language_exam_bp.route('/<subject>/<level>/<time_period>/vraag/<int:question_id>/get_theory_explanation', methods=['GET'])
def get_theory_explanation(subject, level, time_period, question_id):
    """Generate a theory explanation for the current question (Language Exam)"""
    # <<< Get model selection from request query parameters >>>
    selected_model = request.args.get('selected_model') 
    
    try:
        question_data = get_question_data(subject, level, time_period, question_id)
        if not question_data:
            return jsonify({'error': 'Question not found'}), 404

        # Use the theory prompt (might need language-specific versions later)
        prompt_text = THEORY_EXPLANATION_PROMPT.format(
            vraag_id=question_id,
            vak=subject,
            niveau=level,
            question_type=question_data.get('type', 'unknown'),
            exam_question=question_data.get('vraagtekst', ''),
            exam_context=question_data.get('bron_tekst_html', 'Geen context beschikbaar.') # Use source text as context for lang
        )

        # Roep Gemini aan
        try:
            # <<< Pass selected_model to configure_genai >>>
            model, error_message = configure_genai(model_name=selected_model)
            if error_message:
                return jsonify({"error": error_message}), 500

            print(f"\nDEBUG (Lang): Calling Gemini for Theory Explanation Q{question_id}..." )
            full_prompt = SYSTEM_PROMPT + "\n\n" + prompt_text
            response = model.generate_content(full_prompt)
            explanation = response.text.replace('`', '') # Clean explanation
            print(f"---> Theory Explanation Received: {explanation[:100]}...")
            return jsonify({'explanation': explanation})
        
        except Exception as e:
            print(f"CRITICAL: Error generating theory explanation (lang) for Q{question_id}: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': 'Fout bij genereren theorie uitleg.', 'status': 'error'}), 500

    except Exception as e:
        print(f"Error in get_theory_explanation route (lang) for Q{question_id}: {e}")
        return jsonify({'error': 'Interne serverfout.', 'status': 'error'}), 500 