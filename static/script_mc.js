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
            body: JSON.stringify({ 
                answer: answer, 
                selected_model: currentModel,
                question_type: currentVraagType // <<< ADDED: Explicitly send question type
            }),
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
            
            // <<< REPROCESS MATHJAX for feedback content >>>
            if (window.MathJax && window.MathJax.typesetPromise) {
                 console.log("Typesetting MathJax for feedbackBox...");
                 window.MathJax.typesetPromise([feedbackBox]).catch(function (err) {
                     console.error('MathJax typesetting error for feedback:', err);
                 });
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
                console.log('Wel/Niet Buttons gevonden:', welNietButtons.length); // DEBUG
                welNietButtons.forEach(button => {
                    button.addEventListener('click', function() { // <<< Correcte listener
                        console.log('Wel/Niet knop geklikt!', this.dataset.beweringId, this.dataset.answer); // DEBUG
                        const beweringId = this.dataset.beweringId;
                        const answer = this.dataset.answer;

                        // Update the answer storage
                        userAnswer[beweringId] = answer;

                        // Update visual selection for this specific bewering
                        const parentOptionDiv = this.closest('.wel-niet-option');
                        if (parentOptionDiv) {
                            const buttonsInGroup = parentOptionDiv.querySelectorAll('.wel-niet-button');
                            buttonsInGroup.forEach(btn => btn.classList.remove('active'));
                            this.classList.add('active');
                        }

                        // Check if all are selected to enable submit
                        checkAllWelNietSelected();
                    });
                });
            } else if (currentVraagType === 'open' || currentVraagType === 'citeer' || currentVraagType === 'open_non_language' || currentVraagType === 'calculation') {
                if (submitButton) submitButton.disabled = false; 
            } else if (currentVraagType === 'multiple_gap_choice') {
                if (submitButton) submitButton.disabled = true; 
                function checkAllGapChoicesMade() { /*...*/ }
                const gapSelects = document.querySelectorAll('.gap-select');
                gapSelects.forEach(select => { select.addEventListener('change', checkAllGapChoicesMade); });
                checkAllGapChoicesMade(); 
            } else if (currentVraagType === 'tabel_invullen') {
                const tabelInputs = document.querySelectorAll('#tabelInvullenContainer .tabel-input');
                const answerData = {};
                let allFilled = true;
                tabelInputs.forEach(input => {
                    const key = input.dataset.key;
                    const value = input.value.trim();
                    if (!value) { // Check if the textarea is empty
                        allFilled = false;
                    }
                    answerData[key] = value;
                });
                if (allFilled) { // Only submit if all textareas have content
                    getFeedback(answerData);
                } else {
                    console.warn("Tabel Invullen: Niet alle velden ingevuld.");
                    // Optionally, provide feedback to the user, e.g., highlight empty fields
                    // alert("Vul alstublieft alle velden in voordat u verstuurt."); 
                }
            } else if (['open_nl', 'citeer', 'open', 'nummering', 'open_non_language', 'calculation'].includes(currentVraagType)) {
                const openAnswerInput = document.getElementById('openAnswer');
                if (openAnswerInput && openAnswerInput.value.trim()) {
                    getFeedback(openAnswerInput.value.trim());
                } else {
                     console.warn("Open Vraag: Geen antwoord ingevuld.");
                     // Optionally show a message
                }
            } else if (currentVraagType === 'match') {
                const matchSelects = document.querySelectorAll('.match-select');
                const numLeftItems = document.querySelectorAll('.match-item-left').length;

                function checkAllMatched() {
                     let allSelected = true;
                    let countSelected = 0;
                    matchAnswers = {}; // Reset answers object
                    matchSelects.forEach(select => {
                        const leftId = select.dataset.leftId;
                        if (select.value) { 
                            matchAnswers[leftId] = select.value; // Store selection
                            countSelected++;
                        } else {
                             allSelected = false;
                         }
                     });
                    // Enable button only if every left item has a selection
                    submitButton.disabled = countSelected !== numLeftItems; 
                }

                matchSelects.forEach(select => {
                    select.addEventListener('change', checkAllMatched);
                });

                // Initial check in case of page reload with selections (less likely but good practice)
                checkAllMatched(); 
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
                
                // <<< REPROCESS MATHJAX for metaphor content (attempt 2) >>>
                if (window.MathJax && window.MathJax.typesetPromise) {
                     console.log("Typesetting MathJax for metaphorBox...");
                     window.MathJax.typesetPromise([metaphorBox]).catch(function (err) {
                         console.error('MathJax typesetting error for metaphor:', err);
                     });
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
             // console.log('Checking wel_niet condition. Type:', currentVraagType, 'Container Element:', welNietOptionsContainer); // DEBUG -> REMOVE

             // --- START RE-ADDED CODE BLOCK ---
             // Initialize userAnswer as an object for wel_niet
             const numBeweringen = welNietOptionsContainer.querySelectorAll('.wel-niet-option').length;
             userAnswer = {};
             for (let i = 0; i < numBeweringen; i++) {
                 userAnswer[i] = null; // Initialize all answers to null
             }

             const welNietButtons = welNietOptionsContainer.querySelectorAll('.wel-niet-button');
             welNietButtons.forEach(button => {
                 button.addEventListener('click', function() {
                     const beweringId = this.dataset.beweringId;
                     const answer = this.dataset.answer;

                     // Update the answer storage
                     userAnswer[beweringId] = answer;

                     // Update visual selection for this specific bewering
                     const parentOptionDiv = this.closest('.wel-niet-option');
                     if (parentOptionDiv) {
                         const buttonsInGroup = parentOptionDiv.querySelectorAll('.wel-niet-button');
                         buttonsInGroup.forEach(btn => btn.classList.remove('active'));
                         this.classList.add('active');
                     }

                     // Check if all are selected to enable submit
                     checkAllWelNietSelected();
                 });
             });
             // --- END RE-ADDED CODE BLOCK ---

             if (submitButton) submitButton.disabled = true; // Initial state: disable submit

             // Helper function to check if all wel/niet are selected
             function checkAllWelNietSelected() {
                 let allSelected = true;
                 // Ensure userAnswer is initialized (should be above)
                 if (typeof userAnswer === 'object' && userAnswer !== null) {
                     for (const id in userAnswer) {
                         if (userAnswer[id] === null) {
                             allSelected = false;
                             break;
                         }
                     }
                 } else {
                     allSelected = false; // Not initialized correctly
                 }
                 if (submitButton) submitButton.disabled = !allSelected;
             }
             checkAllWelNietSelected(); // Initial check

         } else if ((currentVraagType === 'open' || currentVraagType === 'citeer' || currentVraagType === 'open_non_language' || currentVraagType === 'calculation') && document.getElementById('openAnswer')) {
            if (submitButton) submitButton.disabled = false; 
         } else if (currentVraagType === 'multiple_gap_choice') {
             if (submitButton) submitButton.disabled = true; 
             function checkAllGapChoicesMade() { /*...*/ }
             const gapSelects = document.querySelectorAll('.gap-select');
             gapSelects.forEach(select => { select.addEventListener('change', checkAllGapChoicesMade); });
             checkAllGapChoicesMade(); 
        } else if (currentVraagType === 'tabel_invullen') {
            const tabelInputs = document.querySelectorAll('#tabelInvullenContainer .tabel-input');
            const answerData = {};
            let allFilled = true;
            tabelInputs.forEach(input => {
                const key = input.dataset.key;
                const value = input.value.trim();
                if (!value) { // Check if the textarea is empty
                    allFilled = false;
                }
                answerData[key] = value;
            });
            if (allFilled) { // Only submit if all textareas have content
                getFeedback(answerData);
            } else {
                console.warn("Tabel Invullen: Niet alle velden ingevuld.");
                // Optionally, provide feedback to the user, e.g., highlight empty fields
                // alert("Vul alstublieft alle velden in voordat u verstuurt."); 
            }
        } else if (['open_nl', 'citeer', 'open', 'nummering', 'open_non_language', 'calculation'].includes(currentVraagType)) {
            const openAnswerInput = document.getElementById('openAnswer');
            if (openAnswerInput && openAnswerInput.value.trim()) {
                getFeedback(openAnswerInput.value.trim());
            } else {
                 console.warn("Open Vraag: Geen antwoord ingevuld.");
                 // Optionally show a message
            }
        } else if (currentVraagType === 'match') {
            const matchSelects = document.querySelectorAll('.match-select');
            const numLeftItems = document.querySelectorAll('.match-item-left').length;

            function checkAllMatched() {
                 let allSelected = true;
                let countSelected = 0;
                matchAnswers = {}; // Reset answers object
                matchSelects.forEach(select => {
                    const leftId = select.dataset.leftId;
                    if (select.value) { 
                        matchAnswers[leftId] = select.value; // Store selection
                        countSelected++;
                    } else {
                         allSelected = false;
                     }
                 });
                // Enable button only if every left item has a selection
                submitButton.disabled = countSelected !== numLeftItems; 
            }

            matchSelects.forEach(select => {
                select.addEventListener('change', checkAllMatched);
            });

            // Initial check in case of page reload with selections (less likely but good practice)
            checkAllMatched(); 
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
             submitButton.addEventListener('click', function() {
                if (currentVraagType === 'mc') {
                    if (userAnswer !== null) {
                        getFeedback(userAnswer);
                    }
                } else if (currentVraagType === 'wel_niet') {
                    const welNietOptions = welNietOptionsContainer.querySelectorAll('.wel-niet-option');
                    const answers = [];
                    welNietOptions.forEach((option, index) => {
                        const activeButton = option.querySelector('.wel-niet-button.active');
                        answers[index] = activeButton ? activeButton.dataset.answer : null; // Store 'Wel', 'Niet', or null
                    });
                     // Check if all have been answered before submitting
                    if (answers.every(ans => ans !== null)) {
                         getFeedback(answers); 
                         } else {
                         console.warn("Wel/Niet: Niet alle beweringen beantwoord.");
                         // Optionally show a message to the user
                    }
                } else if (currentVraagType === 'order') {
                     const orderedItems = Array.from(document.querySelectorAll('#sentenceList .order-item'));
                     const answerOrder = orderedItems.map(item => item.dataset.id); // Get the IDs in the current order
                     getFeedback(answerOrder);
                } else if (currentVraagType === 'gap_fill') {
                     const gapInputs = document.querySelectorAll('#gapFillContainer .gap-input');
                     const answers = [];
                     gapInputs.forEach((input, index) => {
                         answers[index] = input.value.trim() || null; // Store trimmed value or null
                     });
                     // Check if all gaps are filled (or handle differently if empty is allowed)
                     if (answers.every(ans => ans !== null)) {
                          getFeedback(answers);
                     } else {
                         console.warn("Gap Fill: Niet alle gaten ingevuld.");
                         // Optionally show a message to the user
                     }
                } else if (currentVraagType === 'tabel_invullen') {
                    const tabelInputs = document.querySelectorAll('#tabelInvullenContainer .tabel-input');
                    const answerData = {};
                    let allFilled = true;
                    tabelInputs.forEach(input => {
                        const key = input.dataset.key;
                        const value = input.value.trim();
                        if (!value) { // Check if the textarea is empty
                            allFilled = false;
                        }
                        answerData[key] = value;
                    });
                    if (allFilled) { // Only submit if all textareas have content
                        getFeedback(answerData);
                 } else {
                        console.warn("Tabel Invullen: Niet alle velden ingevuld.");
                        // Optionally, provide feedback to the user, e.g., highlight empty fields
                        // alert("Vul alstublieft alle velden in voordat u verstuurt."); 
                    }
                } else if (['open_nl', 'citeer', 'open', 'nummering', 'open_non_language', 'calculation'].includes(currentVraagType)) {
                    const openAnswerInput = document.getElementById('openAnswer');
                    if (openAnswerInput && openAnswerInput.value.trim()) {
                        getFeedback(openAnswerInput.value.trim());
                 } else {
                         console.warn("Open Vraag: Geen antwoord ingevuld.");
                         // Optionally show a message
                    }
                } else if (currentVraagType === 'match') {
                    // matchAnswers is updated by the change listener
                    getFeedback(matchAnswers);
                }
            });
        } else {
            console.error("Submit button not found!");
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
    setupIssueReporting(); // <<< ADDED: Call setup for issue reporting

    // === ADD EVENT LISTENERS *AFTER* initial setup ===
    // <<< REMOVED DUPLICATE EVENT LISTENER CODE BLOCK >>>
    // The listeners are already being added within setupQuestionUI() 
    // so this entire block from here down to the corresponding `});` 
    // before the helper function definitions was redundant and causing issues.
    
}); // <<< THIS IS THE CORRECT END of DOMContentLoaded >>>

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
                
                // <<< REPROCESS MATHJAX for theory content >>>
                if (window.MathJax && window.MathJax.typesetPromise) {
                     console.log("Typesetting MathJax for theoryBox...");
                     window.MathJax.typesetPromise([theoryBox]).catch(function (err) {
                         console.error('MathJax typesetting error for theory:', err);
                     });
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

// <<< START: Issue Reporting Functions >>>
function setupIssueReporting() {
    const reportButton = document.getElementById('reportIssueBtn');
    const reportText = document.getElementById('issueReportText');
    const reportConfirmation = document.getElementById('issueReportConfirmation');
    const reportError = document.getElementById('issueReportError');

    if (reportButton) {
        reportButton.addEventListener('click', function() {
            // Disable button immediately
            reportButton.disabled = true;
            reportError.style.display = 'none'; // Hide previous errors

            // Gather data (already available in global scope from script setup)
            const reportData = {
                subject: document.body.dataset.vak,
                level: document.body.dataset.niveau,
                time_period: document.body.dataset.tijdvak,
                question_id: parseInt(document.body.dataset.vraagId, 10)
                // comment: document.getElementById('issueComment').value // Add this if implementing comments
            };

            // Send data to backend
            fetch('/nl-exam/report_issue', { // <<< ADDED /nl-exam prefix
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(reportData),
            })
            .then(response => {
                if (!response.ok) {
                    // Try to get error message from backend if available
                    return response.json().then(errData => {
                        throw new Error(errData.error || 'Network response was not ok');
                    }).catch(() => {
                         throw new Error('Network response was not ok and no error detail available.'); // Throw generic if parsing fails
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    // Show confirmation, hide original text
                    if(reportText) reportText.style.display = 'none';
                    reportConfirmation.style.display = 'inline'; // Show confirmation text
                    reportButton.style.display = 'none'; // Hide button completely after success
                } else {
                    // Handle potential errors reported by the backend logic
                    throw new Error(data.error || 'Unknown error from server');
                }
            })
            .catch(error => {
                console.error('Error reporting issue:', error);
                reportError.textContent = `Melden mislukt: ${error.message}. Probeer later opnieuw.`;
                reportError.style.display = 'inline';
                reportButton.disabled = false; // Re-enable button on failure
            });
        });
    } else {
        console.warn("Issue reporting button (#reportIssueBtn) not found.");
    }
}
// <<< END: Issue Reporting Functions >>> 