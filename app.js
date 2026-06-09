// ExpertMachina CLI Demo Simulation Logic

const demoData = {
    biotechStudy: {
        prompt: "Which version of the monitoring plan was used for Study ABC-201 and why was it amended?",
        steps: [
            { stage: 'l1', log: "L1 INTAKE: Accessing clinical trial archives... Reading ABC-201_Protocol_v3.pdf, Monitoring_Plan_v2.0.docx, Monitoring_Plan_v2.1_Final.pdf, and FDA_Decentralized_Guidance_2024.pdf" },
            { stage: 'l2', log: "L2 KNOWLEDGE MAP: Parsing entity associations: [Study ABC-201] -> [Monitoring Plan v2.1] -> [Amendment 2: remote SDV workflows] -> [FDA Guidance compliance]" },
            { stage: 'l3', log: "L3 EXPERT AGENT: Aligning plan change history with regulatory guidelines..." },
            { stage: 'l4', log: "L4 GOVERNANCE: Access credentials validated (Role: Clinical Operations Lead). Action logged to audit trail." }
        ],
        answer: "Study ABC-201 utilized Monitoring Plan v2.1 (authorized 2024-04-12). It was amended from v2.0 to include remote source data verification (rSDV) protocols in response to updated FDA guidance on decentralized trial workflows."
    },
    protocol: {
        prompt: "Why was Client X moved from Protocol A to Protocol B in 2024?",
        steps: [
            { stage: 'l1', log: "L1 INTAKE: Accessing repository archives... Reading SOP_Revision_3.2.docx, Meeting_Minutes_2024-03-18.pdf, Validation_Report_441.docx, and Change_Request_17.msg" },
            { stage: 'l2', log: "L2 KNOWLEDGE MAP: Resolving entity relations: [Client X] -> [Protocol A stability issue] -> [Change Request 17] approved by [Lead Investigator]" },
            { stage: 'l3', log: "L3 EXPERT AGENT: Correlating meeting consensus with experimental reports..." },
            { stage: 'l4', log: "L4 GOVERNANCE: Checked clearance. Query logged to secure ledger. Verification complete." }
        ],
        answer: "Client X was moved to Protocol B after stability issues documented in Change Request #17. Supporting evidence:\n- Meeting Minutes 2024-03-18\n- SOP Revision 3.2\n- Validation Report #441"
    },
    refund: {
        prompt: "What is our refund/cancellation policy for enterprise SLA?",
        steps: [
            { stage: 'l1', log: "L1 INTAKE: Accessing repository files... Found 'SLA_Agreement_v4_Final.pdf' and 'Finance_SOP_Q1.docx'" },
            { stage: 'l2', log: "L2 KNOWLEDGE MAP: Parsing node relations: [Enterprise Contract] -> [Refund Policy: 30-Day Pro-Rata] -> Approved by [Finance Director]" },
            { stage: 'l3', log: "L3 EXPERT AGENT: Synthesizing contextual answer based on 2 verified sources..." },
            { stage: 'l4', log: "L4 GOVERNANCE: Verifying access clearances: Group 'Finance-SLA' authorized. Generating audit log..." }
        ],
        answer: "Under our standard Enterprise SLA (SLA_Agreement_v4_Final.pdf, Section 8.2), customers can request a pro-rated refund within the first 30 days of contract execution if service uptime falls below 99.9% for two consecutive weeks. Any exceptions require written sign-off from the Finance Director."
    }
};

let isRunning = false;

async function typeText(element, text, speed = 15) {
    return new Promise((resolve) => {
        let i = 0;
        element.innerHTML = "";
        const interval = setInterval(() => {
            if (i < text.length) {
                element.innerHTML += text.charAt(i);
                i++;
                // Auto-scroll console
                const body = document.getElementById('console-body');
                body.scrollTop = body.scrollHeight;
            } else {
                clearInterval(interval);
                resolve();
            }
        }, speed);
    });
}

async function runDemo(key) {
    if (isRunning) return;
    isRunning = true;

    const flowContainer = document.getElementById('demo-execution-flow');
    const choicesContainer = document.getElementById('choices-container');
    
    // Disable other choice buttons
    const buttons = choicesContainer.querySelectorAll('button');
    buttons.forEach(btn => btn.disabled = true);
    
    // Clear previous execution logs
    flowContainer.innerHTML = "";
    
    // Reset pipeline step card highlights
    document.querySelectorAll('.pipeline-card').forEach(card => card.classList.remove('active'));

    const data = demoData[key];

    // 1. Output Prompt Input
    const promptLine = document.createElement('div');
    promptLine.className = 'console-prompt';
    flowContainer.appendChild(promptLine);
    await typeText(promptLine, data.prompt, 25);

    // 2. Perform step-by-step pipeline logging
    for (let i = 0; i < data.steps.length; i++) {
        await new Promise(r => setTimeout(r, 600));
        
        const step = data.steps[i];
        
        // Highlight pipeline cards
        document.querySelectorAll('.pipeline-card').forEach(card => card.classList.remove('active'));
        const card = document.getElementById(`card-${step.stage}`);
        if (card) card.classList.add('active');

        const logLine = document.createElement('div');
        logLine.className = 'console-log';
        flowContainer.appendChild(logLine);
        await typeText(logLine, `> ${step.log}`, 10);
    }

    await new Promise(r => setTimeout(r, 800));

    // 3. Highlight Expert Agent (L3) & Governance (L4) as answers are returned
    document.querySelectorAll('.pipeline-card').forEach(card => card.classList.remove('active'));
    document.getElementById('card-l3').classList.add('active');
    document.getElementById('card-l4').classList.add('active');

    // 4. Output Answer Box
    const outputBox = document.createElement('div');
    outputBox.className = 'console-output success';
    flowContainer.appendChild(outputBox);
    
    const outputHeader = document.createElement('div');
    outputHeader.style.fontWeight = 'bold';
    outputHeader.style.color = 'var(--accent-green)';
    outputHeader.style.marginBottom = '8px';
    outputHeader.innerText = "EXPERT ANSWER [SOURCE_VERIFIED]:";
    outputBox.appendChild(outputHeader);

    const textSpan = document.createElement('span');
    outputBox.appendChild(textSpan);
    
    // Show answer box
    outputBox.classList.add('show');
    
    await typeText(textSpan, data.answer, 20);

    // Add blinking cursor at the end
    const cursor = document.createElement('span');
    cursor.className = 'blinking-cursor';
    outputBox.appendChild(cursor);

    // Enable choices buttons
    buttons.forEach(btn => btn.disabled = false);
    isRunning = false;
}

// Handle waitlist pilot application form submit
function handleFormSubmit(e) {
    e.preventDefault();
    const email = document.getElementById('email').value;
    const company = document.getElementById('company-name').value;
    const employees = document.getElementById('employees').value;
    const industry = document.getElementById('industry').value;
    const challenge = document.getElementById('challenge').value;
    const status = document.getElementById('form-status');

    status.style.color = 'var(--accent-green)';
    status.innerText = "Connection initialized... Syncing qualification profile...";

    setTimeout(() => {
        status.innerText = `SUCCESS: Qualification profile stored. Company: ${company} | Employees: ${employees} | Industry: ${industry} | Main challenge: "${challenge.substring(0,60)}...". Ticket generated for ${email}. We will contact you for Q3 2026 pilot scheduling.`;
        document.getElementById('pilot-form').reset();
    }, 1500);
}
