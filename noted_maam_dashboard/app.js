// Mock Meeting Data Timeline
const meetingTimeline = [
  {
    timestamp: "00:03",
    speaker: "rahul",
    name: "Rahul Sharma",
    text: "Hi team, dashboard interface changes verify karne hai hume production launch se pehle.",
    hindiIndices: [4, 5, 6, 7, 8, 9] // indices of hindi words
  },
  {
    timestamp: "00:10",
    speaker: "rahul",
    name: "Rahul Sharma",
    text: "Amit, can you verify the database endpoints by Friday afternoon?",
    task: {
      task_name: "Verify database endpoints",
      owner: "Amit Patel",
      deadline: "Friday (Jul 17)",
      priority: "Medium",
      confidence: "98%",
      citation: "verify the database endpoints by Friday afternoon"
    }
  },
  {
    timestamp: "00:16",
    speaker: "amit",
    name: "Amit Patel",
    text: "Haan, main verification completely clear kar dunga by Friday. Don't worry.",
    hindiIndices: [0, 2, 3, 5, 6, 7]
  },
  {
    timestamp: "00:24",
    speaker: "rahul",
    name: "Rahul Sharma",
    text: "Perfect. Sarah, dashboard change code push kar dena latest by next Wednesday so telemetry matches.",
    hindiIndices: [4, 5, 6, 7, 8, 9],
    task: {
      task_name: "Push dashboard codebase changes",
      owner: "Sarah Jenkins",
      deadline: "Wednesday (Jul 15)",
      priority: "High",
      confidence: "94%",
      citation: "dashboard change code push kar dena latest by next Wednesday"
    }
  },
  {
    timestamp: "00:33",
    speaker: "sarah",
    name: "Sarah Jenkins",
    text: "Deploy Wednesday drop karna target timing ke hisab se block ho sakta hai without security compliance signoff.",
    hindiIndices: [4, 5, 6, 7, 8]
  },
  {
    timestamp: "00:41",
    speaker: "rahul",
    name: "Rahul Sharma",
    text: "No, dashboard Friday drop must happen for client onboarding. Schedule represents our primary goal.",
    conflictTrigger: true // triggers contradiction box
  },
  {
    timestamp: "00:49",
    speaker: "sarah",
    name: "Sarah Jenkins",
    text: "Wait. Let's postpone the beta deploy to next Friday to finalize telemetry telemetry mapping properly.",
    citation: "postpone the beta deploy to next Friday"
  },
  {
    timestamp: "00:56",
    speaker: "amit",
    name: "Amit Patel",
    text: "Theek hai, main dev environment update test verify kar leta hoon tab tak."
  }
];

// Document Summaries
const summaryData = {
  exec: `
    <ul class="exec-summary-list">
      <li><span class="exec-bullet">•</span> Verified database endpoints deadline set for Friday afternoon.</li>
      <li><span class="exec-bullet">•</span> Dashboard UI changes undergo active review for client onboarding requirements.</li>
      <li><span class="exec-bullet">•</span> Deployment schedule contradiction identified between Wednesday and next Friday.</li>
    </ul>
  `,
  topic: `
    <div class="topic-group">
      <div class="topic-title">Engineering & Database</div>
      <p class="placeholder-text" style="font-style: normal; color: var(--text-main); font-size: 0.9rem;">
        Amit Patel assigned to run endpoint verification. Database schema validation pending staging confirmation.
      </p>
    </div>
    <div class="topic-group">
      <div class="topic-title">Deployments & Schedule</div>
      <p class="placeholder-text" style="font-style: normal; color: var(--text-main); font-size: 0.9rem;">
        Conflict: Rahul requested Wednesday code freeze for Friday deploy. Sarah requested postpone deployment to next Friday due to telemetry alignment.
      </p>
    </div>
  `,
  mom: `
    <div style="font-size: 0.85rem; line-height: 1.5; color: var(--text-main);">
      <p><strong>Date:</strong> 2026-07-10</p>
      <p><strong>Attendees:</strong> Rahul Sharma, Sarah Jenkins, Amit Patel</p>
      <hr style="border: 0; border-top: 1px solid var(--border-light); margin: 10px 0;">
      <p><strong>Minutes:</strong></p>
      <p>1. Amit will complete endpoint analysis by Friday.</p>
      <p>2. Scheduling misalignment detected and escalated for client review.</p>
    </div>
  `
};

// State Variables
let currentTimelineIndex = 0;
let isPlaying = false;
let playInterval = null;
let secondsElapsed = 0;

// Elements
const btnToggleStream = document.getElementById("btn-toggle-stream");
const streamTimer = document.getElementById("stream-timer");
const transcriptFeed = document.getElementById("transcript-feed");
const transcriptEmpty = document.getElementById("transcript-empty");
const conflictPanel = document.getElementById("conflict-panel");
const taskList = document.getElementById("task-list");
const taskBadge = document.getElementById("task-badge");
const conflictBadge = document.getElementById("conflict-badge");
const summaryContent = document.getElementById("summary-content");
const globalSearch = document.getElementById("global-search");

// Audio Player Simulation
function formatTime(secs) {
  const mins = Math.floor(secs / 60).toString().padStart(2, '0');
  const remainingSecs = (secs % 60).toString().padStart(2, '0');
  return `${mins}:${remainingSecs}`;
}

function handleStreamStep() {
  if (currentTimelineIndex >= meetingTimeline.length) {
    clearInterval(playInterval);
    isPlaying = false;
    btnToggleStream.classList.remove("playing");
    btnToggleStream.querySelector("span").innerText = "Simulation Ended";
    btnToggleStream.disabled = true;
    return;
  }

  // Time ticking
  secondsElapsed += 7;
  streamTimer.innerText = formatTime(secondsElapsed);

  const dataPoint = meetingTimeline[currentTimelineIndex];
  renderTranscriptSegment(dataPoint);

  // Trigger tasks if present
  if (dataPoint.task) {
    renderTaskItem(dataPoint.task);
  }

  // Trigger conflict if marked
  if (dataPoint.conflictTrigger) {
    triggerConflictBox();
  }

  // Update summaries progressively at mid/end-points
  if (currentTimelineIndex === 3) {
    updateSummaries(3);
  } else if (currentTimelineIndex === meetingTimeline.length - 1) {
    updateSummaries(8);
  }

  currentTimelineIndex++;
  transcriptFeed.scrollTop = transcriptFeed.scrollHeight;
}

function renderTranscriptSegment(item) {
  if (transcriptEmpty) {
    transcriptEmpty.remove();
  }

  const bubble = document.createElement("div");
  bubble.className = `transcript-bubble ${item.speaker}`;
  
  // Format Hindi indices if defined
  let textContentHtml = item.text;
  if (item.hindiIndices) {
    const words = item.text.split(" ");
    item.hindiIndices.forEach(idx => {
      if (words[idx]) {
        words[idx] = `<span class="hi-segment">${words[idx]}</span>`;
      }
    });
    textContentHtml = words.join(" ");
  }

  bubble.innerHTML = `
    <div class="bubble-meta">
      <span class="speaker-badge ${item.speaker}">${item.name}</span>
      <span class="timestamp">${item.timestamp}</span>
    </div>
    <div class="bubble-text">${textContentHtml}</div>
  `;

  transcriptFeed.appendChild(bubble);
}

function renderTaskItem(task) {
  // Clear placeholder if first task
  const placeholder = taskList.querySelector(".placeholder-text");
  if (placeholder) {
    placeholder.remove();
  }

  const taskItem = document.createElement("div");
  taskItem.className = "task-item";
  taskItem.id = `task-${Date.now()}`;
  
  taskItem.innerHTML = `
    <div class="task-top">
      <div class="checkbox-wrap" onclick="toggleTask('${taskItem.id}')">
        <div class="checkbox-custom"></div>
      </div>
      <div class="task-details">
        <div class="task-title">${task.task_name}</div>
        <div class="task-meta">
          <span class="meta-tag owner">${task.owner}</span>
          <span class="meta-tag">Due: ${task.deadline}</span>
          <span class="meta-tag priority-high">${task.priority} Priority</span>
          <span class="meta-tag confidence">Confidence: ${task.confidence}</span>
        </div>
      </div>
    </div>
    <div class="task-citation">
      Context: "... ${task.citation} ..."
    </div>
  `;

  taskList.appendChild(taskItem);
  updateActiveTaskCount();
}

function toggleTask(id) {
  const item = document.getElementById(id);
  if (item) {
    item.classList.toggle("completed");
    updateActiveTaskCount();
  }
}

function updateActiveTaskCount() {
  const total = taskList.querySelectorAll(".task-item:not(.completed)").length;
  taskBadge.innerText = `${total} Active Tasks`;
}

function triggerConflictBox() {
  conflictPanel.style.display = "block";
  conflictBadge.style.display = "inline-block";
}

function resolveConflict(selection) {
  conflictPanel.style.transition = "all 0.4s ease";
  conflictPanel.style.opacity = "0.4";
  conflictPanel.style.pointerEvents = "none";
  
  setTimeout(() => {
    conflictPanel.style.display = "none";
    conflictBadge.style.display = "none";
    
    // Dynamically insert resolved outcome task/note into Deliverables
    const resolutionNote = document.createElement("div");
    resolutionNote.className = "task-item";
    resolutionNote.style.borderLeftColor = "var(--accent-green)";
    resolutionNote.innerHTML = `
      <div class="task-top">
        <div class="checkbox-wrap" style="cursor: default;">
          <div class="checkbox-custom" style="background: var(--accent-green); border-color: var(--accent-green);">✓</div>
        </div>
        <div class="task-details">
          <div class="task-title" style="text-decoration: line-through; color: var(--text-muted);">
            Conflict Resolved: Target Deploy Postponed to Next Friday
          </div>
          <div class="task-meta">
            <span class="meta-tag" style="background: rgba(16, 185, 129, 0.1); color: var(--accent-green)">Resolved</span>
            <span class="meta-tag">Override Source: Sarah Jenkins</span>
          </div>
        </div>
      </div>
    `;
    taskList.insertBefore(resolutionNote, taskList.firstChild);
  }, 600);
}

function updateSummaries(step) {
  if (step === 3) {
    document.getElementById("tab-exec").innerHTML = `
      <ul class="exec-summary-list">
        <li><span class="exec-bullet">•</span> Database verification initialized by Amit Patel.</li>
        <li><span class="exec-bullet">•</span> Staging deploy review expected early Wednesday.</li>
      </ul>
    `;
  } else {
    document.getElementById("tab-exec").innerHTML = summaryData.exec;
    document.getElementById("tab-topic").innerHTML = summaryData.topic;
    document.getElementById("tab-mom").innerHTML = summaryData.mom;
  }
}

// Global Tab Click handlers
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", (e) => {
    const parent = btn.parentElement;
    parent.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    
    const tabName = btn.getAttribute("data-tab");
    document.querySelectorAll(".tab-pane").forEach(pane => pane.classList.remove("active"));
    document.getElementById(`tab-${tabName}`).classList.add("active");
  });
});

// Play/Pause Action
btnToggleStream.addEventListener("click", () => {
  if (isListening) stopLiveMic();
  if (isPlaying) {
    clearInterval(playInterval);
    isPlaying = false;
    btnToggleStream.classList.remove("playing");
    btnToggleStream.querySelector("span").innerText = "Simulate Meeting";
  } else {
    isPlaying = true;
    btnToggleStream.classList.add("playing");
    btnToggleStream.querySelector("span").innerText = "Pause Simulation";
    playInterval = setInterval(handleStreamStep, 2000); // Step every 2 seconds
  }
});

// Live Microphone Speech Recognition
const btnLiveMic = document.getElementById("btn-live-mic");
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
let isListening = false;

if (SpeechRecognition) {
  recognition = new SpeechRecognition();
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = "en-US";

  recognition.onstart = () => {
    isListening = true;
    btnLiveMic.classList.add("playing");
    btnLiveMic.style.backgroundColor = "rgba(239, 68, 68, 0.12)";
    btnLiveMic.style.borderColor = "rgba(239, 68, 68, 0.3)";
    btnLiveMic.style.color = "var(--accent-red)";
    btnLiveMic.querySelector("span").innerText = "Listening...";
    
    // Start elapsed timer
    timerInterval = setInterval(() => {
      secondsElapsed++;
      streamTimer.innerText = formatTime(secondsElapsed);
    }, 1000);
  };

  recognition.onerror = (event) => {
    console.error("Speech Recognition Error:", event.error);
    const errContainer = document.getElementById("mic-error-container");
    const errText = document.getElementById("mic-error-text");
    if (errContainer && errText) {
      if (event.error === "not-allowed") {
        errText.innerText = "Microphone access blocked. Please click the site padlock icon in your address bar, switch Microphone to 'Allow', then refresh the page.";
      } else if (event.error === "no-speech") {
        console.log("No speech detected.");
        return; // don't stop listening on quietness
      } else {
        errText.innerText = `Speech recognition issue: ${event.error}`;
      }
      errContainer.style.display = "flex";
    }
    stopLiveMic();
  };

  recognition.onend = () => {
    stopLiveMic();
  };

  recognition.onresult = (event) => {
    let interimTranscript = "";
    let finalTranscript = "";

    for (let i = event.resultIndex; i < event.results.length; ++i) {
      if (event.results[i].isFinal) {
        finalTranscript += event.results[i][0].transcript;
      } else {
        interimTranscript += event.results[i][0].transcript;
      }
    }

    if (finalTranscript) {
      const formattedTime = formatTime(secondsElapsed);
      renderTranscriptSegment({
        timestamp: formattedTime,
        speaker: "sarah", // render with Sarah's color for contrast
        name: "You (Real-time)",
        text: finalTranscript
      });
      transcriptFeed.scrollTop = transcriptFeed.scrollHeight;

      // Extract tasks and conflicts dynamically in real-time
      analyzeSpeechForTasks(finalTranscript);
      updateSummariesRealtime(finalTranscript);
    }
  };
} else {
  btnLiveMic.title = "Speech Recognition not supported in this browser.";
  btnLiveMic.disabled = true;
}

function stopLiveMic() {
  if (timerInterval) clearInterval(timerInterval);
  isListening = false;
  btnLiveMic.classList.remove("playing");
  btnLiveMic.style.backgroundColor = "rgba(107, 143, 59, 0.08)";
  btnLiveMic.style.borderColor = "rgba(107, 143, 59, 0.2)";
  btnLiveMic.style.color = "var(--accent-olive)";
  btnLiveMic.querySelector("span").innerText = "Start Live Mic";
  try {
    recognition.stop();
  } catch {}
}

btnLiveMic.addEventListener("click", async () => {
  if (isPlaying) {
    // Pause simulation if active
    clearInterval(playInterval);
    isPlaying = false;
    btnToggleStream.classList.remove("playing");
    btnToggleStream.querySelector("span").innerText = "Simulate Meeting";
  }

  if (isListening) {
    stopLiveMic();
  } else {
    try {
      // Clear warning container
      document.getElementById("mic-error-container").style.display = "none";

      // Force browser permission dialog prompt
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach(track => track.stop()); // release mic immediately

      if (transcriptEmpty) {
        transcriptEmpty.remove();
      }
      recognition.start();
    } catch (e) {
      console.error(e);
      const errContainer = document.getElementById("mic-error-container");
      const errText = document.getElementById("mic-error-text");
      if (errContainer && errText) {
        if (window.location.protocol === "chrome-extension:") {
          chrome.tabs.create({ url: "permission.html" });
          errText.innerText = "Please grant microphone access in the opened tab to activate transcription.";
        } else {
          errText.innerText = "Microphone access blocked. Please click the site padlock icon in your address bar, switch Microphone to 'Allow', then refresh the page.";
        }
        errContainer.style.display = "flex";
      }
    }
  }
});

function analyzeSpeechForTasks(text) {
  const lowercase = text.toLowerCase().trim();
  
  // Custom regex to match actionable expressions: "need to X", "have to Y", "remind me to Z"
  const verbs = ["verify", "push", "test", "write", "call", "fix", "update", "deploy", "build", "review", "email"];
  
  // 1. Scan for conflict words
  if (lowercase.includes("conflict") || lowercase.includes("contradiction") || (lowercase.includes("wednesday") && lowercase.includes("friday"))) {
    triggerConflictBox();
  }

  // 2. Scan for actions
  const triggerPhrases = ["need to", "must", "action item to", "task is to", "have to", "remind me to", "assign to"];
  for (const phrase of triggerPhrases) {
    if (lowercase.includes(phrase)) {
      const idx = lowercase.indexOf(phrase);
      let actionPart = text.substring(idx + phrase.length).trim();
      if (actionPart.length > 5) {
        // Strip trailing punctuation
        actionPart = actionPart.replace(/[.,\/#!$%\^&\*;:{}=\-_`~()]/g,"");
        
        // Clean capitalisation
        const taskName = actionPart.charAt(0).toUpperCase() + actionPart.slice(1);
        renderTaskItem({
          task_name: taskName,
          owner: "You (Real-time)",
          deadline: "Immediate",
          priority: "High",
          confidence: "95%",
          citation: phrase + " " + actionPart
        });
        return;
      }
    }
  }
}

function updateSummariesRealtime(text) {
  // 1. Update Executive Summary
  const execBox = document.getElementById("tab-exec");
  if (execBox.querySelector(".placeholder-text")) {
    execBox.innerHTML = '<ul class="exec-summary-list"></ul>';
  }
  const list = execBox.querySelector(".exec-summary-list");
  if (list) {
    const li = document.createElement("li");
    li.innerHTML = `<span class="exec-bullet">•</span> Voice transcript captured: "${text}"`;
    list.appendChild(li);
  }

  // 2. Update Topics
  const topicBox = document.getElementById("tab-topic");
  if (topicBox.querySelector(".placeholder-text")) {
    topicBox.innerHTML = '';
  }
  const lowercase = text.toLowerCase();
  let title = "";
  if (lowercase.includes("database") || lowercase.includes("api") || lowercase.includes("endpoints") || lowercase.includes("server")) {
    title = "Database & Backend";
  } else if (lowercase.includes("dashboard") || lowercase.includes("ui") || lowercase.includes("design") || lowercase.includes("interface")) {
    title = "UI & Dashboard Design";
  } else if (lowercase.includes("deploy") || lowercase.includes("schedule") || lowercase.includes("date") || lowercase.includes("deadline")) {
    title = "Schedule & Operations";
  }
  if (title) {
    const div = document.createElement("div");
    div.className = "topic-group";
    div.innerHTML = `
      <div class="topic-title">${title}</div>
      <p class="placeholder-text" style="font-style: normal; color: var(--text-main); font-size: 0.9rem;">
        Speaker noted: "${text}"
      </p>
    `;
    topicBox.appendChild(div);
  }

  // 3. Update MOM Minutes
  const momBox = document.getElementById("tab-mom");
  if (momBox.querySelector(".placeholder-text")) {
    momBox.innerHTML = `
      <div style="font-size: 0.85rem; line-height: 1.5; color: var(--text-main);">
        <p><strong>Date:</strong> 2026-07-12</p>
        <p><strong>Attendees:</strong> You (Real-time)</p>
        <hr style="border: 0; border-top: 1px solid var(--border-light); margin: 10px 0;">
        <p><strong>Minutes:</strong></p>
        <ul class="space-y-2" id="mom-minutes-list" style="list-style: decimal; padding-left: 15px;"></ul>
      </div>
    `;
  }
  const momList = document.getElementById("mom-minutes-list");
  if (momList) {
    const li = document.createElement("li");
    li.style.marginTop = "6px";
    li.innerText = text;
    momList.appendChild(li);
  }
}

// Conflict Resolvers
document.getElementById("resolve-stmt-b").addEventListener("click", () => resolveConflict("sarah"));
document.getElementById("resolve-stmt-a").addEventListener("click", () => resolveConflict("rahul"));

// Search query filter simulation
globalSearch.addEventListener("input", (e) => {
  const val = e.target.value.toLowerCase().trim();
  const bubbles = transcriptFeed.querySelectorAll(".transcript-bubble");
  
  bubbles.forEach(b => {
    const txt = b.querySelector(".bubble-text").innerText.toLowerCase();
    if (txt.includes(val)) {
      b.style.display = "flex";
      b.style.opacity = "1";
    } else {
      b.style.opacity = "0.2";
    }
  });

  if (val === "") {
    bubbles.forEach(b => {
      b.style.display = "flex";
      b.style.opacity = "1";
    });
  }
});
