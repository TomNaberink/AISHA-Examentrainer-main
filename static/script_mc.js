document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM fully loaded and parsed"); // DEBUG
    // === Lees variabelen uit data attributen ===
    const bodyData = document.body.dataset;
    const vraag_id = parseInt(bodyData.vraagId, 10); // Zorg dat ID een getal is
    const currentSubject = bodyData.vak;
    const currentLevel = bodyData.niveau;
    const currentTimePeriod = bodyData.tijdvak;
    const currentVraagType = bodyData.vraagType;
    const currentMaxScore = parseInt(bodyData.maxScore, 10); // Zorg dat score een getal is
    const max_vraag_id = parseInt(bodyData.maxVraagId, 10); // Zorg dat ID een getal is
    const get_feedback_url = bodyData.feedbackUrl;
    const get_hint_url = bodyData.hintUrl;
    const get_follow_up_url = bodyData.followUpUrl;
    const get_theory_url = bodyData.theoryUrl; // Kan leeg zijn
    const base_question_url = bodyData.baseQuestionUrl;
    const home_url = bodyData.homeUrl; // <<< Read the new home URL
    // <<< REVISED: Read JSON from dedicated script tag >>>
    let currentVraagData = {}; // Default to empty object
    try {
        const jsonDataScript = document.getElementById('vraagDataJson');
        if (jsonDataScript) {
            currentVraagData = JSON.parse(jsonDataScript.textContent || '{}');
        } else {
            console.error("Could not find the #vraagDataJson script tag!");
        }
    } catch (e) {
        // Log the error and the content that failed to parse
        console.error("Error parsing vraag_data JSON from script tag:", e);
        const scriptContent = document.getElementById('vraagDataJson')?.textContent;
        console.error("Script tag content that failed parsing:", scriptContent);
        // Optionally, leave currentVraagData as {} or handle the error differently
    }
    // ==========================================

    // References to elements
    const mcOptionsContainer = document.getElementById('mcOptionsContainer');
    const welNietOptionsContainer = document.getElementById('welNietOptionsContainer');
    let submitButton = document.getElementById('submitAnswer');
    const hintButton = document.getElementById('hintButton');
    const feedbackBox = document.getElementById('feedbackBox');
    const feedbackContent = document.getElementById('feedbackContent');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const errorIndicator = document.getElementById('errorIndicator');
    const hintBox = document.getElementById('hintBox');
    const hintContent = document.getElementById('hintContent');
    const hintLoadingIndicator = document.getElementById('hintLoadingIndicator');
    const hideHintButton = document.getElementById('hideHintButton');
    const followUpChat = document.getElementById('followUpChat');
    const followUpQuestion = document.getElementById('followUpQuestion');
    const sendFollowUp = document.getElementById('sendFollowUp');
    const followUpAnswerBox = document.getElementById('followUpAnswerBox');
    const followUpAnswerContent = document.getElementById('followUpAnswerContent');
    const followUpLoadingIndicator = document.getElementById('followUpLoadingIndicator');
    const theoryButton = document.getElementById('theoryButton'); // Voeg ID toe aan HTML indien nog niet gedaan
    const theoryBox = document.getElementById('theoryBox'); // Voeg ID toe aan HTML
    const theoryContent = document.getElementById('theoryContent'); // Voeg ID toe aan HTML
    const theoryLoadingIndicator = document.getElementById('theoryLoadingIndicator'); // Voeg ID toe aan HTML
    const hideTheoryBtn = document.getElementById('hideTheoryBtn'); // <<< CORRECTED VARIABLE NAME
    
    // Nieuwe elementen voor antwoordmodel en theorie
    const showModelAnswerBtn = document.getElementById('showModelAnswerBtn');
    const modelAnswerBox = document.getElementById('modelAnswerBox');
    const hideModelAnswerBtn = document.getElementById('hideModelAnswerBtn');
    const getTheoryBtn = document.getElementById('getTheoryBtn');
    const theoryErrorIndicator = document.getElementById('theoryErrorIndicator'); // Definieer deze
    const getMetaphorBtn = document.getElementById('getMetaphorBtn'); // <<< ADDED
    const metaphorBox = document.getElementById('metaphorBox'); // <<< ADDED
    const metaphorContent = document.getElementById('metaphorContent'); // <<< ADDED
    const metaphorLoadingIndicator = document.getElementById('metaphorLoadingIndicator'); // <<< ADDED
    const metaphorErrorIndicator = document.getElementById('metaphorErrorIndicator'); // <<< ADDED
    const hideMetaphorBtn = document.getElementById('hideMetaphorBtn'); // <<< ADDED
    const modelToggleSwitch = document.getElementById('modelToggleSwitch'); // <<< ADDED: Get toggle switch
    
    // Navigation buttons
    const prevButton = document.getElementById('prev-question-btn');
    const nextButton = document.getElementById('next-question-btn');
    const submitExamButton = document.getElementById('submitExamBtn'); // <<< Get submit exam button
    const completionModal = document.getElementById('completionModal'); // <<< Get modal
    
    // <<< ADDED CHECKS: Ensure modal and its buttons exist before assigning variables >>>
    let closeModalButton = null;
    let goHomeBtn = null;
    if (completionModal) {
        closeModalButton = completionModal.querySelector('.close-button');
        goHomeBtn = document.getElementById('goHomeBtn'); 
    } else {
        console.error("Completion modal element (#completionModal) not found!");
    }
    // <<< END CHECKS >>>

    // User's answer storage
    let userAnswer = null;
    let lastFeedback = null;
    let questionStatus = {}; // Object om status per vraag op te slaan
    // <<< Moved model constants to global scope >>>
    // const defaultModel = 'gemini-2.5-flash-preview-04-17'; 
    // const fastModel = 'gemini-2.0-flash';               
    // const smartModel = 'gemini-2.5-flash-preview-04-17';  
    let selectedAiModel; // Will be initialized in setupModelToggle

    // Function to get the currently selected model name
    // <<< MOVED TO GLOBAL SCOPE >>>

    // Function to initialize and handle toggle switch changes
    function setupModelToggle() {
        const fastModel = 'gemini-2.0-flash';               
        const smartModel = 'gemini-2.5-flash-preview-04-17';  
        const defaultModel = smartModel; // Sync with global default

        if (!modelToggleSwitch) {
            console.warn("Model toggle switch not found.");
            selectedAiModel = localStorage.getItem('selectedAiModel') || defaultModel;
            console.log("Initial model (no toggle found, from localStorage or default):", selectedAiModel);
            return; 
        }

        const savedModel = localStorage.getItem('selectedAiModel');
        if (savedModel === fastModel) {
            modelToggleSwitch.checked = false;
            selectedAiModel = fastModel;
        } else {
            modelToggleSwitch.checked = true;
            selectedAiModel = smartModel; 
            if (!savedModel || savedModel !== smartModel) {
                localStorage.setItem('selectedAiModel', smartModel);
            }
        }
        console.log("Initial model toggle state set. Selected model:", selectedAiModel);

        modelToggleSwitch.addEventListener('change', function() {
            selectedAiModel = this.checked ? smartModel : fastModel;
            localStorage.setItem('selectedAiModel', selectedAiModel);
            console.log("Model selection changed to:", selectedAiModel);
        });
    }

    // Functie om status op te slaan en knop bij te werken
    function updateQuestionStatus(qId, status) {
        questionStatus[qId] = status;
        updateNavButtonStatus(qId, status);
        try { 
            localStorage.setItem('questionStatus_' + currentSubject + '_' + currentLevel + '_' + currentTimePeriod, JSON.stringify(questionStatus)); 
        } catch (e) { 
            console.error('Error saving status to localStorage', e); 
        }
    }

    // Functie om de klasse van een navigatieknop bij te werken
    function updateNavButtonStatus(qId, status) {
        const navButton = document.querySelector(`.nav-item[data-vraag-id="${qId}"]`);
        if (navButton) {
            navButton.classList.remove('correct', 'partial', 'incorrect', 'answered');
            if (status && status !== 'unknown' && status !== 'error') {
                navButton.classList.add(status);
            }
        }
    }

    // Initialiseer status van knoppen bij laden van pagina
    function initializeStatuses() {
        try {
            const savedStatus = localStorage.getItem('questionStatus_' + currentSubject + '_' + currentLevel + '_' + currentTimePeriod);
            if (savedStatus) {
                questionStatus = JSON.parse(savedStatus);
                Object.keys(questionStatus).forEach(qId => {
                    updateNavButtonStatus(qId, questionStatus[qId]);
                });
            }
        } catch (e) { 
            console.error('Error loading status from localStorage', e); 
            questionStatus = {};
        }
        
        updateNavButtonStatus(vraag_id, questionStatus[vraag_id]);
        const currentNavButton = document.querySelector(`.nav-item[data-vraag-id="${vraag_id}"]`);
        if(currentNavButton) {
             document.querySelectorAll('.nav-item.active').forEach(b => {
                if (b !== currentNavButton) {
                    b.classList.remove('active');
                }
             });
             if(!currentNavButton.classList.contains('active')) {
                 currentNavButton.classList.add('active');
             }
        }
    }

    // Function to get feedback for an answer
    function getFeedback(answer) {
        userAnswer = answer;
        const currentModel = getSelectedModel();
        
        loadingIndicator.style.display = 'block';
        errorIndicator.style.display = 'none';
        feedbackContent.innerHTML = '';
        feedbackBox.style.display = 'block';
        
        if (submitButton) submitButton.disabled = true;
        
        fetch(get_feedback_url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ answer: answer, selected_model: currentModel }),
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            loadingIndicator.style.display = 'none';
            feedbackBox.classList.remove('correct', 'incorrect', 'partial', 'error');
            
            if (data.feedback) {
                lastFeedback = data.feedback;
                let feedbackText = data.feedback;
                console.log("JS Debug: Feedback text BEFORE replace:", feedbackText);
                feedbackText = feedbackText.replace(/\*\*(.+?)\*\*/gs, '<strong>$1</strong>');
                feedbackText = feedbackText.replace(/\n\n/g, '<br><br>');
                console.log("JS Debug: Feedback text AFTER replace:", feedbackText);
                feedbackContent.innerHTML = feedbackText;
                feedbackBox.style.display = 'block';
                followUpChat.style.display = 'block';
            } else {
                errorIndicator.style.display = 'block';
                errorIndicator.textContent = data.error || 'Er is een fout opgetreden bij het genereren van feedback.';
                feedbackBox.classList.add('error');
                feedbackBox.style.display = 'block';
            }
            
            if (data.status && data.status !== 'pending' && data.status !== 'error') {
                updateQuestionStatus(vraag_id, data.status);
                feedbackBox.classList.add(data.status);
            } else if (!data.feedback) {
                updateQuestionStatus(vraag_id, 'error');
            }
            
            if (currentVraagType === 'mc') {
                const mcButtons = mcOptionsContainer.querySelectorAll('.mc-option-button');
                mcButtons.forEach(btn => btn.disabled = true);
            } else if (currentVraagType === 'wel_niet') {
                const welNietButtons = welNietOptionsContainer.querySelectorAll('.wel-niet-button');
                welNietButtons.forEach(btn => btn.disabled = true);
            }
        })
        .catch(error => {
            console.error('Error getting feedback:', error);
            loadingIndicator.style.display = 'none';
            errorIndicator.style.display = 'block';
            errorIndicator.textContent = 'Er is een netwerkfout opgetreden.';
            updateQuestionStatus(vraag_id, 'error'); 
        });
    }

    // Function to get a hint
    function getHint() {
        const currentModel = getSelectedModel();
        hintBox.style.display = 'block';
        hintContent.innerHTML = '';
        hintLoadingIndicator.style.display = 'block';
        
        fetch(`${get_hint_url}?selected_model=${currentModel}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            hintLoadingIndicator.style.display = 'none';
            if (data.hint) {
                const parsedHint = marked.parse(data.hint);
                hintContent.innerHTML = parsedHint;
            } else {
                hintContent.innerHTML = '<p>Sorry, er kon geen hint worden gegenereerd.</p>';
            }
        })
        .catch(error => {
            console.error('Error getting hint:', error);
            hintLoadingIndicator.style.display = 'none';
            hintContent.innerHTML = '<p>Er is een fout opgetreden bij het ophalen van de hint.</p>';
        });
    }

    // Function to get a metaphor explanation
    function getMetaphorExplanation() {
        const currentModel = getSelectedModel();
        metaphorBox.style.display = 'block';
        metaphorContent.innerHTML = ''; 
        metaphorErrorIndicator.style.display = 'none';
        metaphorLoadingIndicator.style.display = 'block';

        const get_metaphor_url = `/nl-exam/${currentSubject}/${currentLevel}/${currentTimePeriod}/vraag/${vraag_id}/get_metaphor_explanation`;
        const urlWithModel = `${get_metaphor_url}?selected_model=${currentModel}`;

        fetch(urlWithModel)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                metaphorLoadingIndicator.style.display = 'none';
                if (data.metaphor) {
                    let metaphorText = data.metaphor;
                    console.log("JS Debug: Metaphor text BEFORE replace:", metaphorText);
                    metaphorText = metaphorText.replace(/\*\*(.+?)\*\*/gs, '<strong>$1</strong>');
                    metaphorText = metaphorText.replace(/\n\n/g, '<br><br>');
                    console.log("JS Debug: Metaphor text AFTER replace:", metaphorText);
                    metaphorContent.innerHTML = metaphorText;
                    metaphorErrorIndicator.style.display = 'none';
                } else if (data.error) {
                    metaphorContent.innerHTML = '';
                    metaphorErrorIndicator.textContent = data.error;
                    metaphorErrorIndicator.style.display = 'block';
                } else {
                     metaphorContent.innerHTML = '<p>Geen metafoor beschikbaar.</p>';
                     metaphorErrorIndicator.style.display = 'none';
                }
            })
            .catch(error => {
                console.error('Error getting metaphor explanation:', error);
                metaphorLoadingIndicator.style.display = 'none';
                metaphorContent.innerHTML = '';
                metaphorErrorIndicator.textContent = 'Fout bij ophalen metafoor uitleg.';
                metaphorErrorIndicator.style.display = 'block';
            });
    }

    // Function to send a follow-up question
    function sendFollowUpQuestion() {
        const question = followUpQuestion.value.trim();
        if (!question) return;
        const currentModel = getSelectedModel();
        
        followUpAnswerBox.style.display = 'block';
        followUpAnswerContent.innerHTML = '';
        followUpLoadingIndicator.style.display = 'block';
        sendFollowUp.disabled = true;
        
        fetch(get_follow_up_url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ question: question, feedback: lastFeedback, selected_model: currentModel }),
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            followUpLoadingIndicator.style.display = 'none';
            if (data.answer) {
                let followUpAnswer = data.answer;
                console.log("JS Debug: Follow-up text BEFORE replace:", followUpAnswer);
                followUpAnswer = followUpAnswer.replace(/\*\*(.+?)\*\*/gs, '<strong>$1</strong>');
                followUpAnswer = followUpAnswer.replace(/\n\n/g, '<br><br>');
                console.log("JS Debug: Follow-up text AFTER replace:", followUpAnswer);
                followUpAnswerContent.innerHTML = followUpAnswer;
            } else {
                followUpAnswerContent.innerHTML = '<p>Sorry, er kon geen antwoord worden gegenereerd.</p>';
            }
            
            followUpQuestion.value = '';
            sendFollowUp.disabled = true;
        })
        .catch(error => {
            console.error('Error getting follow-up answer:', error);
            followUpLoadingIndicator.style.display = 'none';
            followUpAnswerContent.innerHTML = '<p>Er is een fout opgetreden bij het ophalen van het antwoord.</p>';
            sendFollowUp.disabled = false;
        });
    }

    // === Modal Functions (Re-added) ===
    function showModal() {
        console.log("DEBUG: showModal() CALLED!");
        console.trace();
        if (completionModal) {
            completionModal.style.display = 'flex'; 
        }
    }

    function closeModal() {
        if (completionModal) {
            completionModal.style.display = 'none';
        }
    }
    // =====================

    // Function to set up UI elements based on question type
    function setupQuestionUI() {
        console.log("Setting up UI for type:", currentVraagType);
        console.log('DEBUG: completionModal element:', completionModal);
        
        if (completionModal) {
            completionModal.style.display = 'none'; 
            console.log("DEBUG: Explicitly hid completion modal.");
        } else {
             console.warn("DEBUG: Cannot hide modal - completionModal element not found.");
        }
        
        if (submitButton) {
             const newSubmitButton = submitButton.cloneNode(true);
             submitButton.parentNode.replaceChild(newSubmitButton, submitButton);
             submitButton = newSubmitButton; 
             submitButton.disabled = false; 
        }
       
        if (currentVraagType === 'mc' && mcOptionsContainer) {
             const mcButtons = mcOptionsContainer.querySelectorAll('.mc-option-button');
             mcButtons.forEach(button => {
                 button.addEventListener('click', function() { 
                     mcButtons.forEach(btn => { btn.classList.remove('active'); });
                     this.classList.add('active');
                     userAnswer = this.dataset.option;
                     if (submitButton) submitButton.disabled = false;
                 });
             });
             if (submitButton) submitButton.disabled = true;
        } else if (currentVraagType === 'wel_niet' && welNietOptionsContainer) {
             if (submitButton) submitButton.disabled = true;
             function checkAllWelNietSelected() {
                 let allSelected = true;
                 for (const id in userAnswer) {
                     if (userAnswer[id] === null) {
                         allSelected = false;
                         break;
                     }
                 }
                 if (submitButton) submitButton.disabled = !allSelected;
             }
             checkAllWelNietSelected(); 
        } else if ((currentVraagType === 'open' || currentVraagType === 'citeer' || currentVraagType === 'open_non_language' || currentVraagType === 'calculation') && document.getElementById('openAnswer')) {
            if (submitButton) submitButton.disabled = false; 
        } else if (currentVraagType === 'multiple_gap_choice') {
             if (submitButton) submitButton.disabled = true; 
             function checkAllGapChoicesMade() { /*...*/ }
             const gapSelects = document.querySelectorAll('.gap-select');
             gapSelects.forEach(select => { select.addEventListener('change', checkAllGapChoicesMade); });
             checkAllGapChoicesMade(); 
        }

        // --- Process Context Box --- 
        const contextBox = document.querySelector('.context-box');
        console.log('DEBUG JS: Attempting to process context box...');
        if (contextBox) { 
            console.log('DEBUG JS: Found contextBox element:', contextBox);
            console.log('DEBUG JS: Value of currentVraagData.context_html:', currentVraagData?.context_html);
            
            const hasContextHtml = Boolean(currentVraagData?.context_html);
            console.log('DEBUG JS: Condition (currentVraagData.context_html) evaluates to:', hasContextHtml);
            
            if (hasContextHtml) {
                contextBox.innerHTML = currentVraagData.context_html;
                contextBox.style.display = 'block';
                console.log('DEBUG JS: Set contextBox display to block.');
            } else {
                contextBox.style.display = 'none';
                console.log('DEBUG JS: Set contextBox display to none because condition was false.');
            }
        } else {
            console.warn("Context box element not found during setup.");
        }

        // === ATTACH ALL EVENT LISTENERS HERE ===

        if (submitButton) {
            submitButton.addEventListener('click', () => {
                let collectedAnswer = null;
                 if (currentVraagType === 'mc') {
                    const selectedOption = mcOptionsContainer.querySelector('.mc-option-button.active');
                    if (selectedOption) collectedAnswer = selectedOption.getAttribute('data-option');
                 } else if (currentVraagType === 'wel_niet') {
                 } else if (currentVraagType === 'open' || currentVraagType === 'citeer' || currentVraagType === 'open_non_language' || currentVraagType === 'calculation') {
                    const textarea = document.getElementById('openAnswer');
                    if(textarea) collectedAnswer = textarea.value;
                 } else if (currentVraagType === 'multiple_gap_choice') {
                    collectedAnswer = {};
                    let allSelected = true;
                    const selects = document.querySelectorAll('.gap-select');
                    selects.forEach(select => {
                        const gapId = select.getAttribute('data-gap-id');
                        collectedAnswer[gapId] = select.value;
                        if (!select.value) allSelected = false;
                    });
                    if (!allSelected) collectedAnswer = null;
                 }
                
                if (collectedAnswer !== null && (typeof collectedAnswer !== 'object' || Object.keys(collectedAnswer).length > 0) ) {
                    getFeedback(collectedAnswer);
                } else {
                    console.log("No answer provided or selected on submit");
                    if (currentVraagType === 'multiple_gap_choice') alert("Selecteer een antwoord voor elk gat.");
                }
            });
        }

        if (hintButton) {
            hintButton.addEventListener('click', getHint);
        }
        if (hideHintButton) {
            hideHintButton.addEventListener('click', () => { hintBox.style.display = 'none'; });
        }

        if (sendFollowUp) {
            sendFollowUp.addEventListener('click', sendFollowUpQuestion);
        }
        if (followUpQuestion) {
            followUpQuestion.addEventListener('input', () => { sendFollowUp.disabled = followUpQuestion.value.trim() === ''; });
        }

        if (showModelAnswerBtn && modelAnswerBox) {
            showModelAnswerBtn.addEventListener('click', () => { 
                modelAnswerBox.style.display = 'block'; 
                showModelAnswerBtn.style.display = 'none'; 
            });
        }
        if (hideModelAnswerBtn && modelAnswerBox) {
            hideModelAnswerBtn.addEventListener('click', () => { 
                modelAnswerBox.style.display = 'none'; 
                if(showModelAnswerBtn) showModelAnswerBtn.style.display = 'inline-block'; 
            });
        }

        if (getTheoryBtn && theoryBox) {
            getTheoryBtn.addEventListener('click', getTheoryExplanation);
        }
        if (hideTheoryBtn && theoryBox) {
            hideTheoryBtn.addEventListener('click', () => { theoryBox.style.display = 'none'; });
        }
        
        if (getMetaphorBtn && metaphorBox) {
            getMetaphorBtn.addEventListener('click', getMetaphorExplanation);
        }
        if (hideMetaphorBtn && metaphorBox) {
            hideMetaphorBtn.addEventListener('click', () => { metaphorBox.style.display = 'none'; });
        }

        if (prevButton) {
            prevButton.addEventListener('click', () => {
                const prevId = vraag_id - 1;
                if (prevId >= 1) window.location.href = `${base_question_url}${prevId}`;
            });
        }
        if (nextButton) {
            nextButton.addEventListener('click', () => {
                const nextId = vraag_id + 1;
                if (nextId <= max_vraag_id) window.location.href = `${base_question_url}${nextId}`;
            });
        }
        
        const submitExamListener = () => {
            console.log("DEBUG: #submitExamBtn clicked! Attempting to show modal.");
            if (completionModal) {
                showModal();
            } else {
                 console.error("Cannot show modal: #completionModal not found.");
                 alert("Fout bij tonen eindscherm.");
            }
        };
        
        if (submitExamButton) {
            submitExamButton.removeEventListener('click', submitExamListener);
            console.log("DEBUG: Removed any existing listener from #submitExamBtn.");

            if (vraag_id === max_vraag_id) { 
                console.log(`DEBUG: On last question (${vraag_id}). Attaching modal listener to #submitExamBtn.`);
                submitExamButton.addEventListener('click', submitExamListener);
            } else {
                 console.log(`DEBUG: Not on last question (${vraag_id} !== ${max_vraag_id}). Submit listener is NOT attached.`);
            }
        } else {
             console.log(`DEBUG: #submitExamBtn element not found on this page (vraag_id=${vraag_id}).`);
        }
        
        if (completionModal) {
            if (closeModalButton) {
                closeModalButton.addEventListener('click', closeModal);
            } else {
                console.warn("Modal close button (.close-button) not found inside modal.");
            }
            if (goHomeBtn) {
                goHomeBtn.addEventListener('click', () => {
                    if (home_url) { window.location.href = home_url; } 
                    else { console.error("Home URL not found!"); window.location.href = '/'; }
                });
            } else {
                 console.warn("Modal go home button (#goHomeBtn) not found inside modal.");
            }
            completionModal.addEventListener('click', (event) => {
                if (event.target === completionModal) closeModal();
            });
        } 
    }

    initializeStatuses();
    setupModelToggle();
    setupQuestionUI();

    // === ADD EVENT LISTENERS *AFTER* initial setup ===

    if (submitButton) {
        submitButton.addEventListener('click', () => {
            let collectedAnswer = null;
            if (currentVraagType === 'mc') {
                const selectedOption = mcOptionsContainer.querySelector('.mc-option-button.selected');
                if (selectedOption) {
                    collectedAnswer = selectedOption.getAttribute('data-option');
                }
            } else if (currentVraagType === 'wel_niet') {
                const selectedOption = welNietOptionsContainer.querySelector('.wel-niet-button.selected');
                if (selectedOption) {
                    collectedAnswer = selectedOption.getAttribute('data-option');
                }
            } else if (currentVraagType === 'open' || currentVraagType === 'citeer' || currentVraagType === 'open_non_language' || currentVraagType === 'calculation') {
                const textarea = document.getElementById('openAnswer');
                collectedAnswer = textarea.value;
            } else if (currentVraagType === 'multiple_gap_choice') {
                 collectedAnswer = {};
                 const selects = document.querySelectorAll('.gap-select');
                 selects.forEach(select => {
                     const gapId = select.getAttribute('data-gap-id');
                     collectedAnswer[gapId] = select.value;
                 });
                 if (!checkAllGapChoicesMade(collectedAnswer, selects.length)) {
                     console.warn("Not all gaps filled when submitting");
                 }
            }

            if (collectedAnswer !== null && collectedAnswer !== '') {
                getFeedback(collectedAnswer);
            } else {
                console.log("No answer provided or selected on submit");
            }
        });
    }

    if (hintButton) {
        hintButton.addEventListener('click', getHint);
    }
    
    if (hideHintButton) {
        hideHintButton.addEventListener('click', () => {
            hintBox.style.display = 'none';
        });
    }

    if (sendFollowUp) {
        sendFollowUp.addEventListener('click', sendFollowUpQuestion);
    }
    
    if(followUpQuestion) {
        followUpQuestion.addEventListener('input', () => {
            sendFollowUp.disabled = followUpQuestion.value.trim() === '';
        });
    }

    if (showModelAnswerBtn) {
        showModelAnswerBtn.addEventListener('click', () => {
            modelAnswerBox.style.display = 'block';
            showModelAnswerBtn.style.display = 'none';
        });
    }
    if (hideModelAnswerBtn) {
        hideModelAnswerBtn.addEventListener('click', () => {
            modelAnswerBox.style.display = 'none';
            if (showModelAnswerBtn) {
                 showModelAnswerBtn.style.display = 'inline-block'; 
            }
        });
    }

    if (getTheoryBtn) {
        getTheoryBtn.addEventListener('click', getTheoryExplanation);
    }
    if (hideTheoryBtn) {
        hideTheoryBtn.addEventListener('click', () => {
            theoryBox.style.display = 'none';
        });
    }
    
    if (getMetaphorBtn) {
        getMetaphorBtn.addEventListener('click', getMetaphorExplanation);
    }
    if (hideMetaphorBtn) {
        hideMetaphorBtn.addEventListener('click', () => {
            metaphorBox.style.display = 'none';
        });
    }

    if (prevButton) {
        prevButton.addEventListener('click', () => {
            const prevId = vraag_id - 1;
            if (prevId >= 1) {
                window.location.href = `${base_question_url}${prevId}`;
            }
        });
    }
    if (nextButton) {
        nextButton.addEventListener('click', () => {
            const nextId = vraag_id + 1;
            if (nextId <= max_vraag_id) {
                window.location.href = `${base_question_url}${nextId}`;
            }
        });
    }
    
    if (closeModalButton) {
        closeModalButton.addEventListener('click', closeModal);
    }
    
    if (goHomeBtn) {
        goHomeBtn.addEventListener('click', () => {
            if (home_url) {
                 window.location.href = home_url;
            } else {
                 console.error("Home URL not found!");
                 window.location.href = '/'; 
            }
        });
    }
    
    if (completionModal) {
        completionModal.addEventListener('click', (event) => {
            if (event.target === completionModal) {
                closeModal();
            }
        });
    }
    
});

// === GLOBAL HELPER FUNCTIONS ===

// Function to get the currently selected model name (MOVED HERE)
function getSelectedModel() {
    const modelToggleSwitch = document.getElementById('modelToggleSwitch'); 
    const fastModel = 'gemini-2.0-flash';               
    const smartModel = 'gemini-2.5-flash-preview-04-17'; 
    const defaultModel = smartModel;

    if (modelToggleSwitch) {
        return modelToggleSwitch.checked ? smartModel : fastModel;
    } 
    console.warn("getSelectedModel couldn't find toggle switch, using localStorage or default.");
    return localStorage.getItem('selectedAiModel') || defaultModel; 
}

function checkAllGapChoicesMade(answers, totalGaps) {
    return Object.keys(answers).length === totalGaps && Object.values(answers).every(val => val !== '');
}

function setupSortableList(containerId, onUpdateCallback) {
    const container = document.getElementById(containerId);
    if (container) {
        Sortable.create(container, {
            animation: 150,
            ghostClass: 'sortable-ghost',
            onEnd: function (evt) {
                if (onUpdateCallback) {
                    onUpdateCallback(evt);
                }
            }
        });
    }
}

// --- Function to get Theory Explanation --- 
function getTheoryExplanation() {
    console.log("DEBUG JS: getTheoryExplanation() called.");
    
    const theoryUrlFromBody = document.body.dataset.theoryUrl;
    const currentModel = getSelectedModel(); 
    
    console.log("DEBUG JS: Theory URL from body:", theoryUrlFromBody);
    console.log("DEBUG JS: Selected model for theory:", currentModel);
    
    if (!theoryUrlFromBody) {
        console.error("Cannot fetch theory: get_theory_url is missing or empty in body data!");
        if (theoryBox) theoryBox.style.display = 'block'; 
        if (theoryErrorIndicator) {
             theoryErrorIndicator.textContent = 'Kon theorie URL niet vinden.';
             theoryErrorIndicator.style.display = 'block';
        }
         if (theoryLoadingIndicator) theoryLoadingIndicator.style.display = 'none';
        return;
    }
    
    const theoryBox = document.getElementById('theoryBox'); // Need to get elements here too
    const theoryErrorIndicator = document.getElementById('theoryErrorIndicator');
    const theoryLoadingIndicator = document.getElementById('theoryLoadingIndicator');
    const theoryContent = document.getElementById('theoryContent');

    if (theoryBox) theoryBox.style.display = 'block';
    if (theoryErrorIndicator) theoryErrorIndicator.style.display = 'none';
    if (theoryLoadingIndicator) theoryLoadingIndicator.style.display = 'block';
    if (theoryContent) theoryContent.innerHTML = '';

    fetch(`${theoryUrlFromBody}?selected_model=${currentModel}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (theoryLoadingIndicator) theoryLoadingIndicator.style.display = 'none';
            if (data.explanation) {
                let theoryText = data.explanation;
                theoryText = theoryText.replace(/\*\*(.+?)\*\*/gs, '<strong>$1</strong>');
                theoryText = theoryText.replace(/\n\n/g, '<br><br>');
                if (theoryContent) theoryContent.innerHTML = theoryText;
                if (theoryErrorIndicator) theoryErrorIndicator.style.display = 'none';
            } else if (data.error) {
                if (theoryContent) theoryContent.innerHTML = '';
                if (theoryErrorIndicator) {
                    theoryErrorIndicator.textContent = data.error;
                    theoryErrorIndicator.style.display = 'block';
                }
            } else {
                if (theoryContent) theoryContent.innerHTML = '<p>Geen theorie beschikbaar.</p>';
                if (theoryErrorIndicator) theoryErrorIndicator.style.display = 'none';
            }
        })
        .catch(error => {
            console.error('Error getting theory explanation:', error);
            if (theoryLoadingIndicator) theoryLoadingIndicator.style.display = 'none';
            if (theoryContent) theoryContent.innerHTML = '';
            if (theoryErrorIndicator) {
                 theoryErrorIndicator.textContent = 'Fout bij ophalen theorie uitleg.';
                 theoryErrorIndicator.style.display = 'block';
            }
        });
} 