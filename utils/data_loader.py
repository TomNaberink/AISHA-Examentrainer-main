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
    question_data = None

    # Scenario 1: Vragen direct onder hoofdniveau (oudere structuur?)
    if 'vragen' in full_exam_data and isinstance(full_exam_data['vragen'], list):
        print("---> get_question_data: Found 'vragen' list at top level. Searching...")
        for q in full_exam_data['vragen']:
            q_id = _safe_get_int_id(q)
            if q_id == question_id:
                question_data = q.copy() # Maak een kopie
                # Probeer opgave info te vinden als die ook op top niveau staat?
                target_opgave = full_exam_data # Minder gestructureerd, maar mogelijk
                print(f"---> Found Q:{question_id} at top level.")
                break # Stop met zoeken

    # Scenario 2: Vragen binnen opgaven (standaard structuur)
    if question_data is None and 'opgaven' in full_exam_data and isinstance(full_exam_data['opgaven'], list):
        print("---> get_question_data: Found 'opgaven' list. Searching within opgaven...")
        for opgave in full_exam_data['opgaven']:
            if isinstance(opgave, dict) and 'vragen' in opgave and isinstance(opgave['vragen'], list):
                for q in opgave['vragen']:
                    q_id = _safe_get_int_id(q)
                    if q_id == question_id:
                        target_opgave = opgave # Onthoud de opgave waar de vraag in zit
                        question_data = q.copy() # Maak een kopie om origineel niet te wijzigen
                        print(f"---> Found Q:{question_id} within opgave {opgave.get('opgave_nr', '?')}")
                        break # Stop binnenste loop
            if question_data: # Als vraag gevonden is in deze opgave
                break # Stop buitenste loop
    
    # --- Verwerk gevonden data --- 
    if question_data:
        print(f"---> get_question_data: Processing found question data.")
        # Voeg relevante opgave-informatie toe aan de vraag-data
        # Dit voorkomt het verliezen van vraag-specifieke velden zoals kolom_links/rechts
        if target_opgave and isinstance(target_opgave, dict):
             # Voeg alleen toe als de key nog NIET in question_data zit, 
             # of als deze specifiek opgave-gerelateerd is.
            opgave_keys_to_add = [
                'opgave_titel', 'opgave_nr', 'context_html', 
                'bron_verwijzing', 'bron_tekst_html', 'bron_tekst_plain',
                'bronverwijzing_tekst' # <<< NIEUW TOEGEVOEGD
            ]
            for key in opgave_keys_to_add:
                if key in target_opgave and key not in question_data:
                    question_data[key] = target_opgave[key]
                elif key in target_opgave and key == 'opgave_titel': # Altijd opgave titel toevoegen/overchrijven
                    question_data[key] = target_opgave[key]
                elif key in target_opgave and key == 'opgave_nr': # Altijd opgave nr toevoegen/overchrijven
                    question_data[key] = target_opgave[key]
                    
            # Voeg teksten toe als die bij opgave horen en niet bij vraag
            # Zoek de tekst behorende bij de tekst_id van de vraag
            question_tekst_id = question_data.get('tekst_id')
            if question_tekst_id and 'teksten' in full_exam_data and isinstance(full_exam_data['teksten'], list):
                 for tekst_data in full_exam_data['teksten']:
                    if isinstance(tekst_data, dict) and tekst_data.get('tekst_id') == question_tekst_id:
                        # Voeg brontekst toe AAN de vraagdata indien nog niet aanwezig
                        if 'bron_tekst_plain' not in question_data and 'bron_tekst_plain' in tekst_data:
                            question_data['bron_tekst_plain'] = tekst_data['bron_tekst_plain']
                        if 'bron_tekst_html' not in question_data and 'inhoud_html' in tekst_data:
                             question_data['bron_tekst_html'] = tekst_data['inhoud_html'] # Gebruik inhoud_html als bron_tekst_html
                        # Voeg bronverwijzing toe AAN de vraagdata indien nog niet aanwezig
                        if 'bron_verwijzing' not in question_data and 'bron_verwijzing' in tekst_data:
                             question_data['bron_verwijzing'] = tekst_data['bron_verwijzing']
                        
                        # <<< NIEUW: Voeg source_text_content toe >>>
                        source_text_content = None
                        if 'bron_tekst_plain' in question_data:
                            source_text_content = question_data['bron_tekst_plain']
                        elif 'bron_tekst_html' in question_data: # Fallback
                            source_text_content = question_data['bron_tekst_html']
                        
                        if source_text_content:
                             question_data['source_text_content'] = source_text_content
                             
                        break # Stop met zoeken naar teksten
                        
        # Fallback/Default voor opgave titel als niet gevonden
        if 'opgave_titel' not in question_data:
            question_data['opgave_titel'] = f"{subject.capitalize()} {level.upper()} {time_period}"
            
        # print("Final question_data being returned:", question_data)
        return question_data
    else:
        print(f"!!! get_question_data: Question ID {question_id} not found in the loaded data.")
        return None

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