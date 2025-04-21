import os
import json
from typing import Dict, List, Optional, Union

# Base directory for exam data
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

# Helper function to safely get and convert ID to int
def _safe_get_int_id(q_dict):
    """Helper to safely get and convert ID to int."""
    if not isinstance(q_dict, dict):
        return None
    # Probeer eerst 'id', dan 'vraag_id'
    q_id = q_dict.get('id')
    if q_id is None:
        q_id = q_dict.get('vraag_id') # Fallback naar 'vraag_id'
    
    if q_id is None:
        return None
    try:
        return int(q_id)
    except (ValueError, TypeError):
         # Optional: Add a warning here if needed
         # print(f"Warning: Could not convert question ID '{q_id}' to integer.")
         return None # Return None if conversion fails

def list_available_exams() -> dict:
    """
    Scan the data directory and subdirectories recursively for JSON files.
    Extracts exam info primarily from the 'examen_info' key within the JSON.
    Falls back to parsing filename (level_subject_period.json) if needed.
    Returns a dictionary like: {'vmbo': {'engels': ['TV1']}}
    """
    exams = {}

    if not os.path.exists(DATA_DIR):
        print(f"Warning: Data directory {DATA_DIR} does not exist")
        return exams

    # Recursively walk through the data directory
    for root, _, files in os.walk(DATA_DIR):
        for filename in files:
            if filename.lower().endswith('.json'):
                file_path = os.path.join(root, filename)
                level = None
                subject_key = None
                time_period = None

                # Attempt 1: Read info from inside the JSON
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, dict) and 'examen_info' in data:
                            info = data['examen_info']
                            level = info.get('niveau')
                            subject_key = info.get('vak')
                            time_period = info.get('tijdvak')
                            # Basic validation
                            if not (level and subject_key and time_period):
                                level = subject_key = time_period = None # Reset if incomplete
                            else:
                                # Ensure lowercase/uppercase consistency
                                level = level.lower()
                                subject_key = subject_key.lower()
                                time_period = time_period.upper() # Keep period uppercase

                except json.JSONDecodeError:
                    print(f"Warning: Skipping invalid JSON file: {file_path}")
                    continue
                except Exception as e:
                    print(f"Warning: Error reading JSON file {file_path}: {e}")
                    continue

                # Attempt 2: Parse filename if info wasn't found/valid in JSON
                if not (level and subject_key and time_period):
                     # Check for direct files like havo_engels_tv1.json
                    if root == DATA_DIR: # Only parse if directly in DATA_DIR
                        parts = filename.lower().replace('.json', '').split('_')
                        if len(parts) >= 3:
                            level = parts[0].lower()
                            subject_key = parts[1].lower()
                            time_period = parts[2].upper()
                        else:
                            print(f"Warning: Could not parse exam info from filename: {filename}")
                            continue # Skip this file if parsing fails
                    else:
                        # Ignore files in subdirs that don't have internal info
                         print(f"Warning: Could not determine exam info for: {file_path}")
                         continue

                # Add valid exam info to the dictionary
                if level and subject_key and time_period:
                    if level not in exams:
                        exams[level] = {}
                    if subject_key not in exams[level]:
                        exams[level][subject_key] = []
                    if time_period not in exams[level][subject_key]:
                        exams[level][subject_key].append(time_period)

    # Sort the time periods for consistent display
    for level in exams:
        for subject in exams[level]:
            exams[level][subject].sort()

    return exams

def load_exam_data(subject: str, level: str, time_period: str) -> Optional[Dict]:
    """
    Load the complete exam data (including texts and questions).
    Searches recursively for the correct JSON file based on internal 'examen_info'
    or filename matching level_subject_period.json.
    Returns the entire loaded JSON dictionary or None.
    """
    target_level = level.lower()
    target_subject = subject.lower()
    target_period = time_period.upper()

    if not os.path.exists(DATA_DIR):
        print(f"Error: Data directory {DATA_DIR} does not exist")
        return None

    # Recursively walk through the data directory
    for root, _, files in os.walk(DATA_DIR):
        for filename in files:
            if filename.lower().endswith('.json'):
                file_path = os.path.join(root, filename)
                # --- DEBUG --- 
                # print(f"Checking file: {file_path}") 
                # --- END DEBUG ---
                file_level = None
                file_subject = None
                file_period = None
                found_match = False

                # Attempt 1: Check info inside the JSON
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, dict) and 'examen_info' in data:
                            info = data['examen_info']
                            # Gebruik .strip() om verborgen witruimte te verwijderen
                            file_level = info.get('niveau', '').strip()
                            file_subject = info.get('vak', '').strip()
                            file_period = info.get('tijdvak', '').strip()
                            if file_level and file_subject and file_period:
                                # Vergelijking gebruikt nu ook .strip() op de targets voor zekerheid
                                if (file_level.lower() == target_level.strip() and 
                                    file_subject.lower() == target_subject.strip() and 
                                    file_period.upper() == target_period.strip()):
                                    
                                    return data # Found match based on internal info
                except Exception as e:
                    # --- DEBUG --- 
                    print(f"!!! Exception while checking internal info for {file_path}: {e}")
                    # --- END DEBUG --- 
                    pass # Ignore files that can't be read or parsed

                # Attempt 2: Check filename (level_subject_period.json) if directly in DATA_DIR
                if root == DATA_DIR:
                    parts = filename.lower().replace('.json', '').split('_')
                    if len(parts) >= 3:
                        file_level = parts[0].lower()
                        file_subject = parts[1].lower()
                        file_period = parts[2].upper()
                        if (file_level == target_level and
                            file_subject == target_subject and
                            file_period == target_period):
                             # Need to actually load the data now
                             try:
                                 with open(file_path, 'r', encoding='utf-8') as f:
                                     return json.load(f)
                             except Exception as e:
                                 print(f"Error loading matched file {file_path}: {e}")
                                 return None # Error loading file even though name matched

    # If loop completes without finding a match
    print(f"Error: Exam data not found for {subject}/{level}/{time_period}")
    return None

def get_question_data(subject: str, level: str, time_period: str, question_id: int) -> Optional[Dict]:
    """
    Get the data for a specific question from the loaded exam data.
    Includes relevant text source and opgave info if available.
    Returns the question dictionary or None if not found.
    """
    full_exam_data = load_exam_data(subject, level, time_period)
    print(f"--- DEBUG get_question_data for {subject}/{level}/{time_period} Q:{question_id} ---")
    if not full_exam_data:
        print("!!! get_question_data: full_exam_data is None or empty!")
        return None

    # --- Logica om de juiste opgave en vraag te vinden --- 
    target_opgave = None
    vragen_list = None
    question_data = None

    if 'opgaven' in full_exam_data and isinstance(full_exam_data['opgaven'], list):
        print("---> get_question_data: Found 'opgaven' list. Searching within opgaven...")
        for opgave in full_exam_data['opgaven']:
            if isinstance(opgave, dict) and 'vragen' in opgave and isinstance(opgave['vragen'], list):
                 # Zoek de vraag binnen deze opgave
                 current_opgave_vragen = opgave['vragen']
                 # Gebruik de helper functie voor veilige ID vergelijking
                 found_question = next((q for q in current_opgave_vragen if _safe_get_int_id(q) == question_id), None)
                 if found_question:
                     question_data = found_question
                     target_opgave = opgave # Onthoud de opgave waar de vraag in zat
                     # Voeg opgave info toe aan de vraag data
                     question_data['opgave_nr'] = opgave.get('opgave_nr')
                     question_data['opgave_titel'] = opgave.get('opgave_titel')
                     if 'context_html' in target_opgave:
                         question_data['context_html'] = target_opgave.get('context_html')
                     vragen_list = current_opgave_vragen # Dit is de lijst voor max_id etc.
                     break # Stop met zoeken door opgaven
    
    # Fallback: Als 'opgaven' structuur niet bestaat of vraag niet gevonden, probeer direct 'vragen' key
    if question_data is None:
        print("---> get_question_data: Question not found in 'opgaven'. Trying root 'vragen' key...")
        if 'vragen' in full_exam_data and isinstance(full_exam_data['vragen'], list):
            vragen_list = full_exam_data['vragen']
            # Gebruik de helper functie voor veilige ID vergelijking
            question_data = next((q for q in vragen_list if _safe_get_int_id(q) == question_id), None)
            if question_data:
                 print(f"---> get_question_data: Question id={question_id} FOUND in root 'vragen' list.")
        else:
             print("!!! get_question_data: Could not find a valid 'vragen' list anywhere!")
             return None # Geen vragenlijst en geen vraag gevonden

    # Als de vraag nog steeds niet gevonden is
    if question_data is None:
        print(f"!!! get_question_data: Question with id={question_id} NOT FOUND!")
        # Optionally print the first few question IDs found in the last checked list:
        if vragen_list:
             # Gebruik de helper functie ook hier voor veilige ID extractie
             ids_found = [_safe_get_int_id(q) for q in vragen_list[:5]]
             # Filter Nones voor een schonere print
             ids_found_filtered = [id_val for id_val in ids_found if id_val is not None]
             print(f"First few valid IDs found in last checked list: {ids_found_filtered}")
        return None 

    # --- Voeg eventuele Brontekst toe (logica voor taalvakken) --- 
    text_id = question_data.get('tekst_id')
    if text_id and 'teksten' in full_exam_data:
        source_text = next((t for t in full_exam_data.get('teksten', []) if t.get('tekst_id') == text_id), None)
        if source_text:
            question_data['bron_tekst_html'] = source_text.get('inhoud_html', '')
            if 'titel' in source_text:
                 question_data['tekst_titel'] = source_text.get('titel', '')
                 print("---> get_question_data: Added bron_tekst_html and tekst_titel to question_data.")

    # Print de uiteindelijke question_data voor debuggen
    final_keys = list(question_data.keys()) if question_data else []
    print(f"---> get_question_data: Final question_data keys BEFORE RETURN for id={question_data.get('id', 'N/A')}: {final_keys}")

    return question_data # Return the original dict (plus potentially bron_tekst)

def get_max_question_id(subject: str, level: str, time_period: str) -> int:
    """
    Get the highest question ID from the exam data.
    Handles both structures ('opgaven' list or root 'vragen' list).
    Returns 0 if no questions are found or data fails to load.
    """
    full_exam_data = load_exam_data(subject, level, time_period)
    max_id = 0

    if not full_exam_data:
        print(f"Warning: Could not load exam data for {subject}/{level}/{time_period} to get max ID.")
        return max_id # 0

    all_questions = []

    # Try 'opgaven' structure first
    if 'opgaven' in full_exam_data and isinstance(full_exam_data['opgaven'], list):
        print(f"---> get_max_question_id: Found 'opgaven' for {subject}/{level}/{time_period}. Collecting questions...")
        for opgave in full_exam_data['opgaven']:
            if isinstance(opgave, dict) and 'vragen' in opgave and isinstance(opgave['vragen'], list):
                all_questions.extend(opgave['vragen'])

    # Fallback: Try root 'vragen' key if 'opgaven' didn't yield questions OR if 'opgaven' list was empty
    if not all_questions and 'vragen' in full_exam_data and isinstance(full_exam_data['vragen'], list):
         print(f"---> get_max_question_id: Using root 'vragen' for {subject}/{level}/{time_period}.")
         all_questions = full_exam_data['vragen']

    if not all_questions:
        print(f"Warning: No questions list found for {subject}/{level}/{time_period} to determine max ID.")
        return max_id # 0

    # Find the max ID from the collected questions
    for q in all_questions:
        q_id = _safe_get_int_id(q) # Use the same helper function
        if q_id is not None and q_id > max_id:
            max_id = q_id

    print(f"---> get_max_question_id: Determined max_id = {max_id} for {subject}/{level}/{time_period}.")
    return max_id 