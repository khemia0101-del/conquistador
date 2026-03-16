/**
 * Conquistador Chatbot Widget — Alpine.js + WebSocket with guided fallback
 */
function chatbot() {
    return {
        isOpen: false,
        messages: [],
        input: '',
        typing: false,
        ws: null,
        mode: 'ai', // 'ai' or 'guided'

        // Guided flow state
        step: 0,
        leadData: {
            service_type: '',
            symptoms: '',
            zip_code: '',
            name: '',
            phone: '',
            carrier: '',
            preferred_time: '',
            urgency: 'routine'
        },

        // Quick-reply buttons for current step
        quickReplies: [],

        toggle() {
            this.isOpen = !this.isOpen;
            if (this.isOpen && this.messages.length === 0) {
                this.connect();
            }
        },

        connect() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const url = `${protocol}//${window.location.host}/ws/chat`;

            try {
                this.ws = new WebSocket(url);

                this.ws.onopen = () => {
                    this.mode = 'ai';
                    if (this.messages.length === 0) {
                        this.ws.send('hi');
                        this.typing = true;
                    }
                };

                this.ws.onmessage = (event) => {
                    this.typing = false;
                    this.messages.push({ role: 'assistant', content: event.data });
                    this.$nextTick(() => this.scrollToBottom());
                };

                this.ws.onclose = () => {
                    this.ws = null;
                };

                this.ws.onerror = () => {
                    this.typing = false;
                    this.ws = null;
                    // Fall back to guided mode
                    this.startGuidedFlow();
                };
            } catch (e) {
                this.startGuidedFlow();
            }
        },

        startGuidedFlow() {
            this.mode = 'guided';
            this.step = 0;
            this.messages = [];
            this.showGuidedStep();
        },

        showGuidedStep() {
            const steps = [
                // Step 0: Greeting + service type
                {
                    msg: "Hi! I'm the Conquistador assistant. What do you need help with today?",
                    replies: [
                        { label: 'Heating Oil Delivery', value: 'heating_oil' },
                        { label: 'HVAC / Furnace Repair', value: 'hvac_repair' },
                        { label: 'AC Repair', value: 'ac_service' },
                        { label: 'New System Installation', value: 'hvac_install' },
                        { label: 'Maintenance / Tune-Up', value: 'furnace_maintenance' },
                        { label: 'Emergency — No Heat!', value: 'emergency' }
                    ]
                },
                // Step 1: Diagnosis questions (dynamic based on service type)
                null, // handled in processGuidedInput
                // Step 2: Zip code
                {
                    msg: "Thanks for those details. What is your zip code so we can find a contractor near you?",
                    replies: []
                },
                // Step 3: Name & phone
                {
                    msg: null, // set dynamically after zip validation
                    replies: []
                },
                // Step 4: Carrier
                {
                    msg: "Which phone carrier do you use? This helps us send you text updates.",
                    replies: [
                        { label: 'Verizon', value: 'verizon' },
                        { label: 'AT&T', value: 'att' },
                        { label: 'T-Mobile', value: 'tmobile' },
                        { label: 'Other / Not Sure', value: 'other' }
                    ]
                },
                // Step 5: Scheduling
                {
                    msg: "When would you like the contractor to come out?",
                    replies: [
                        { label: 'As soon as possible', value: 'asap' },
                        { label: 'Tomorrow', value: 'tomorrow' },
                        { label: 'Within a few days', value: 'few_days' },
                        { label: "I'm flexible", value: 'flexible' }
                    ]
                },
                // Step 6: Confirmation
                null // handled in processGuidedInput
            ];

            if (this.step === 1) {
                // Dynamic diagnosis step
                this.showDiagnosisStep();
                return;
            }

            if (this.step === 3) {
                // Name & phone step
                this.addBotMessage("Great, we serve your area! Can I get your name and phone number? (e.g., John Smith, 717-555-1234)");
                this.quickReplies = [];
                return;
            }

            if (this.step === 6) {
                this.showConfirmation();
                return;
            }

            const stepData = steps[this.step];
            if (stepData) {
                this.addBotMessage(stepData.msg);
                this.quickReplies = stepData.replies || [];
            }
        },

        showDiagnosisStep() {
            const questions = {
                'heating_oil': {
                    msg: "Let me help figure out what you need. How would you describe your situation?",
                    replies: [
                        { label: 'Tank is low / almost empty', value: 'Tank is running low or almost empty' },
                        { label: 'Scheduled fill-up', value: 'Routine scheduled fill-up needed' },
                        { label: 'Tank is empty — no heat!', value: 'Tank is empty, no heat' },
                        { label: 'Other', value: '' }
                    ]
                },
                'hvac_repair': {
                    msg: "Let me ask a few questions to help diagnose the issue. What's happening with your system?",
                    replies: [
                        { label: 'Not turning on at all', value: 'System is not turning on' },
                        { label: 'Running but not heating', value: 'System runs but does not heat' },
                        { label: 'Making strange noises', value: 'System is making unusual noises' },
                        { label: 'Short cycling (turns on/off)', value: 'System is short cycling' },
                        { label: 'Other issue', value: '' }
                    ]
                },
                'ac_service': {
                    msg: "Tell me what's going on with your AC so we can get the right technician out.",
                    replies: [
                        { label: 'Not cooling', value: 'AC running but not cooling' },
                        { label: 'Blowing warm air', value: 'AC blowing warm air' },
                        { label: 'Not turning on', value: 'AC not turning on at all' },
                        { label: 'Leaking water', value: 'AC unit leaking water' },
                        { label: 'Other issue', value: '' }
                    ]
                },
                'hvac_install': {
                    msg: "What kind of installation are you looking for?",
                    replies: [
                        { label: 'New furnace', value: 'Need new furnace installation' },
                        { label: 'New AC system', value: 'Need new AC installation' },
                        { label: 'Heat pump', value: 'Interested in heat pump installation' },
                        { label: 'Full HVAC system', value: 'Need complete HVAC system' },
                        { label: 'Not sure — need advice', value: 'Need consultation on best option' }
                    ]
                },
                'furnace_maintenance': {
                    msg: "Smart choice keeping up with maintenance! What do you need?",
                    replies: [
                        { label: 'Annual tune-up', value: 'Annual furnace tune-up needed' },
                        { label: 'Filter replacement', value: 'Need filter replacement' },
                        { label: 'Safety inspection', value: 'Want safety inspection' },
                        { label: 'Full maintenance plan', value: 'Interested in maintenance plan' }
                    ]
                },
                'emergency': {
                    msg: "I understand this is urgent. Let me fast-track this for you. Can you describe what's happening?",
                    replies: [
                        { label: 'No heat at all', value: 'Complete loss of heat — emergency' },
                        { label: 'Furnace won\'t start', value: 'Furnace will not start — emergency' },
                        { label: 'Strange smell', value: 'Strange smell from heating system' },
                        { label: 'Water/oil leak', value: 'Active water or oil leak from system' }
                    ]
                }
            };

            const q = questions[this.leadData.service_type] || questions['hvac_repair'];
            this.addBotMessage(q.msg);
            this.quickReplies = q.replies;

            if (this.leadData.service_type === 'emergency') {
                this.leadData.urgency = 'emergency';
            }
        },

        showConfirmation() {
            const serviceLabels = {
                'heating_oil': 'Heating Oil Delivery',
                'hvac_repair': 'HVAC / Furnace Repair',
                'ac_service': 'AC Repair',
                'hvac_install': 'HVAC Installation',
                'furnace_maintenance': 'Maintenance',
                'emergency': 'Emergency Service'
            };
            const timeLabels = {
                'asap': 'As soon as possible',
                'tomorrow': 'Tomorrow',
                'few_days': 'Within a few days',
                'flexible': 'Flexible'
            };

            let diagnosis = '';
            if (this.leadData.symptoms) {
                diagnosis = `\nIssue: ${this.leadData.symptoms}`;
            }

            const summary =
                `Here's what I have:\n\n` +
                `Name: ${this.leadData.name}\n` +
                `Phone: ${this.leadData.phone}\n` +
                `Location: ${this.leadData.zip_code}\n` +
                `Service: ${serviceLabels[this.leadData.service_type] || this.leadData.service_type}` +
                `${diagnosis}\n` +
                `Timing: ${timeLabels[this.leadData.preferred_time] || this.leadData.preferred_time}\n\n` +
                `A qualified contractor will reach out to you shortly to confirm the appointment. You'll also get a text confirmation!`;

            this.addBotMessage(summary);
            this.quickReplies = [];

            // Submit the lead via API
            this.submitLead();
        },

        async submitLead() {
            try {
                const res = await fetch('/api/leads/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: this.leadData.name,
                        phone: this.leadData.phone,
                        carrier: this.leadData.carrier,
                        zip_code: this.leadData.zip_code,
                        service_type: this.leadData.service_type,
                        urgency: this.leadData.urgency,
                        description: this.leadData.symptoms +
                            (this.leadData.preferred_time ? ` | Preferred time: ${this.leadData.preferred_time}` : '')
                    })
                });
                if (res.ok) {
                    console.log('Lead submitted successfully');
                }
            } catch (e) {
                console.error('Failed to submit lead:', e);
            }
        },

        selectReply(reply) {
            this.messages.push({ role: 'user', content: reply.label });
            this.processGuidedInput(reply.value || reply.label);
        },

        processGuidedInput(value) {
            this.quickReplies = [];

            switch (this.step) {
                case 0: // Service type selected
                    this.leadData.service_type = value;
                    if (value === 'emergency') {
                        this.leadData.urgency = 'emergency';
                    }
                    this.step = 1;
                    this.showGuidedStep();
                    break;

                case 1: // Diagnosis/symptoms
                    this.leadData.symptoms = value;
                    // Give a brief assessment
                    const assessments = {
                        'System is not turning on': "That could be a thermostat, ignitor, or power issue. A technician will diagnose it on-site.",
                        'System runs but does not heat': "This often points to a faulty ignitor, gas valve, or heat exchanger issue. A tech can pinpoint it.",
                        'System is making unusual noises': "Unusual sounds can indicate a blower motor, bearing, or loose component issue. Good to get it checked.",
                        'System is short cycling': "Short cycling is often caused by a dirty filter, thermostat issue, or overheating safety switch.",
                        'AC running but not cooling': "This could be low refrigerant, a compressor issue, or a dirty coil. A technician can check it.",
                        'AC blowing warm air': "Usually a refrigerant or compressor issue. A tech will check the charge and components.",
                        'Tank is running low or almost empty': "We'll get a delivery scheduled for you right away.",
                        'Tank is empty, no heat': "Let's get an emergency delivery out to you as quickly as possible.",
                    };
                    const assessment = assessments[value];
                    if (assessment) {
                        this.addBotMessage(assessment);
                    }
                    this.step = 2;
                    setTimeout(() => this.showGuidedStep(), assessment ? 1500 : 0);
                    break;

                case 2: // Zip code
                    this.leadData.zip_code = value.trim();
                    // Basic zip validation
                    const validZips = [
                        '17601','17602','17603','17604','17605','17606',
                        '17543','17545','17554','17557','17560','17572','17576','17584',
                        '17401','17402','17403','17404','17405','17406','17407',
                        '17101','17102','17103','17104','17105','17106','17107',
                        '17108','17109','17110','17111','17112',
                        '17042','17046',
                        '19601','19602','19603','19604','19605','19606',
                        '19607','19608','19609','19610','19611'
                    ];
                    if (!validZips.includes(this.leadData.zip_code)) {
                        this.addBotMessage("I'm sorry, we don't currently serve that area. You can call us at (717) 397-9800 and we may be able to help.");
                        return;
                    }
                    this.step = 3;
                    this.showGuidedStep();
                    break;

                case 3: // Name & phone
                    // Parse "Name, Phone" format
                    const parts = value.split(',').map(s => s.trim());
                    if (parts.length >= 2) {
                        this.leadData.name = parts[0];
                        this.leadData.phone = parts[1];
                    } else {
                        this.leadData.name = value;
                        this.addBotMessage("And what's the best phone number to reach you?");
                        this.step = 3.5; // sub-step for phone
                        return;
                    }
                    this.step = 4;
                    this.showGuidedStep();
                    break;

                case 3.5: // Phone (sub-step)
                    this.leadData.phone = value;
                    this.step = 4;
                    this.showGuidedStep();
                    break;

                case 4: // Carrier
                    this.leadData.carrier = value;
                    if (this.leadData.urgency === 'emergency') {
                        this.leadData.preferred_time = 'asap';
                        this.addBotMessage("Since this is urgent, we'll get someone out to you as quickly as possible.");
                        this.step = 6;
                        setTimeout(() => this.showGuidedStep(), 1500);
                    } else {
                        this.step = 5;
                        this.showGuidedStep();
                    }
                    break;

                case 5: // Preferred time
                    this.leadData.preferred_time = value;
                    this.step = 6;
                    this.showGuidedStep();
                    break;
            }
        },

        send() {
            const msg = this.input.trim();
            if (!msg) return;

            this.messages.push({ role: 'user', content: msg });
            this.input = '';

            if (this.mode === 'ai' && this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(msg);
                this.typing = true;
            } else {
                // Guided mode — process text input
                this.processGuidedInput(msg);
            }

            this.$nextTick(() => this.scrollToBottom());
        },

        addBotMessage(text) {
            this.messages.push({ role: 'assistant', content: text });
            this.$nextTick(() => this.scrollToBottom());
        },

        scrollToBottom() {
            const container = this.$refs.messages;
            if (container) {
                container.scrollTop = container.scrollHeight;
            }
        }
    };
}
