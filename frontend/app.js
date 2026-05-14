(function () {
  "use strict";

  const safeStorageKey = "inclassDemoUiFieldsV2";
  const passwordStorageKey = "inclassDemoUiPasswordsV2";
  const passwordKeys = new Set([
    "instructorPassword",
    "studentPassword",
    "badInstructorPassword",
    "badStudentPassword",
  ]);
  const setupFields = [
    "baseUrl",
    "instructorEmail",
    "instructorPassword",
    "studentEmail",
    "studentPassword",
    "courseId",
    "activityNo",
    "studentId",
    "resetStudentEmail",
    "badInstructorEmail",
    "badInstructorPassword",
    "badStudentEmail",
    "badStudentPassword",
  ];
  const requiredDemoFields = [
    "baseUrl",
    "instructorEmail",
    "instructorPassword",
    "studentEmail",
    "studentPassword",
    "courseId",
    "activityNo",
    "studentId",
  ];
  const history = [];
  let latestCsv = "";

  const flowSteps = [
    ["Check API health", "Confirm the FastAPI backend is reachable.", "/", "health", "success"],
    ["Instructor login", "Verify instructor credentials.", "/instructor/login", "instructorLogin", "success"],
    ["Student login", "Verify student credentials.", "/student/login", "studentLogin", "success"],
    ["Instructor list my courses", "Show instructor-scoped course access.", "/instructor/list-my-courses", "listMyCourses", "success"],
    ["Instructor list activities", "Show activities for the selected course.", "/instructor/list-activities", "listActivities", "success"],
    ["Create activity", "Create an instructor-controlled activity.", "/instructor/create-activity", "createActivity", "success"],
    ["Start activity", "Make the activity available to students.", "/instructor/start-activity", "startActivity", "success"],
    ["Student get active activity", "Load the student-facing activity text.", "/student/get-activity", "getActivity", "success"],
    ["Student submit tutoring answer", "Send an answer into the AI tutoring flow.", "/student/submit-tutoring-answer", "submitAnswer", "success"],
    ["Export scores", "Export score evidence as JSON/CSV.", "/instructor/export-scores", "exportScores", "success"],
    ["Manual grade", "Record an instructor grade.", "/instructor/manual-grade", "manualGrade", "success"],
    ["Reset activity", "Clear runtime score state and end the activity.", "/instructor/reset-activity", "resetActivity", "success"],
    ["Student tries logScore after reset", "Expected rejection because the activity is no longer active.", "/student/log-score", "logScore", "postResetFailure"],
  ];

  function el(id) { return document.getElementById(id); }
  function value(id) { const n = el(id); return n ? n.value.trim() : ""; }
  function setValue(id, next) {
    const n = el(id);
    if (n) n.value = next == null ? "" : String(next);
    updateReadyCard();
  }
  function numberValue(id) { const r = value(id); return r === "" ? "" : Number(r); }

  function baseUrl() {
    const fallback = window.location.origin || "http://127.0.0.1:8000";
    return (value("baseUrl") || fallback).replace(/\/+$/, "");
  }

  function objectives(id) {
    return value(id)
      .split(/\r?\n/)
      .map((l) => l.trim())
      .filter(Boolean);
  }

  function setBadge(target, text, kind) {
    if (!target) return;
    target.className = "badge badge-" + kind;
    target.textContent = text;
  }

  function maskSensitive(data) {
    if (data == null || typeof data !== "object") return data;
    if (Array.isArray(data)) return data.map(maskSensitive);
    const copy = {};
    for (const [key, val] of Object.entries(data)) {
      copy[key] = key.toLowerCase().includes("password") ? "***" : maskSensitive(val);
    }
    return copy;
  }

  function format(data) {
    if (typeof data === "string") return data;
    return JSON.stringify(maskSensitive(data), null, 2);
  }

  function summary(method, path, params, body) {
    return maskSensitive({ method, path, params: params || {}, body });
  }

  function visibleOutputForAction(action) {
    if (action === "health") return "setupOut";
    if (action.startsWith("bad")) return "negativeOut";
    if ([
      "studentLogin", "setStudentPassword", "changeStudentPassword",
      "getActivity", "startTutoring", "submitAnswer", "logScore",
    ].includes(action)) {
      return "studentOut";
    }
    return "instructorOut";
  }

  function renderTo(id, data) {
    const n = el(id);
    if (n) n.textContent = format(data);
  }

  async function apiCall(path, params, options) {
    const opts = options || {};
    const method = opts.method || "POST";
    const qs = new URLSearchParams();
    Object.entries(params || {}).forEach(([key, val]) => {
      if (val !== "" && val !== undefined && val !== null) qs.append(key, val);
    });

    const fetchOptions = { method, headers: {} };
    if (opts.body !== undefined) {
      fetchOptions.headers["Content-Type"] = "application/json";
      fetchOptions.body = JSON.stringify(opts.body);
    }

    const req = summary(method, path, params, opts.body);
    try {
      const response = await fetch(baseUrl() + path + (qs.toString() ? "?" + qs.toString() : ""), fetchOptions);
      const text = await response.text();
      let data;
      try { data = text ? JSON.parse(text) : {}; }
      catch (_) { data = { ok: false, error: "Non-JSON response", status: response.status, body: text }; }
      if (!response.ok && data && data.detail) {
        data = { ok: false, error: "HTTP " + response.status, detail: data.detail };
      }
      updateEvidence(req, data, response.ok);
      return { data, requestSummary: req, httpOk: response.ok };
    } catch (err) {
      const data = { ok: false, error: "Backend unreachable", detail: String(err.message || err) };
      updateEvidence(req, data, false);
      return { data, requestSummary: req, httpOk: false };
    }
  }

  function updateEvidence(req, data, httpOk) {
    const safe = maskSensitive(data);
    renderTo("lastSummary", req);
    renderTo("rawLastSummary", req);
    renderTo("lastResponse", safe);
    renderTo("rawLastResponse", safe);

    const ok = safe && safe.ok === true;
    setBadge(el("lastBadge"), ok ? "PASS" : httpOk ? "Backend response" : "Request failed", ok ? "success" : "warning");
    setBadge(el("globalStatus"), ok ? "Last request passed" : "Evidence updated", ok ? "success" : "warning");

    history.unshift({ at: new Date().toISOString(), request: req, response: safe });
    if (history.length > 40) history.pop();
    renderHistory();
  }

  function instructorParams(extra) {
    return Object.assign({ email: value("instructorEmail"), password: value("instructorPassword") }, extra || {});
  }

  function studentParams(extra) {
    return Object.assign({ email: value("studentEmail"), password: value("studentPassword") }, extra || {});
  }

  function courseActivity() {
    return { course_id: value("courseId"), activity_no: numberValue("activityNo") };
  }

  const actions = {
    health: async () => {
      const result = await apiCall("/", {}, { method: "GET" });
      updateReadyCard();
      return result;
    },

    // ── Instructor auth ──────────────────────────────────────────
    instructorLogin: () => apiCall("/instructor/login", instructorParams()),
    setInstructorPassword: () => apiCall("/instructor/set-password", instructorParams()),
    changeInstructorPassword: () => apiCall("/instructor/change-password", instructorParams({
      old_password: value("instructorOldPassword"),
      new_password: value("instructorNewPassword"),
    })),

    // ── Google federated auth (called from GIS callback, not buttons) ──
    googleLogin: (idToken, role) => apiCall("/auth/google-login", {}, {
      method: "POST",
      body: { id_token: idToken, role },
    }),

    // ── Instructor course / activity ─────────────────────────────
    listMyCourses: async () => {
      const result = await apiCall("/instructor/list-my-courses", instructorParams());
      renderCourses(result.data);
      return result;
    },
    listActivities: async () => {
      const result = await apiCall("/instructor/list-activities", instructorParams({ course_id: value("courseId") }));
      renderActivities(result.data);
      return result;
    },
    createActivity: async () => {
      const params = instructorParams({
        course_id: value("courseId"),
        activity_text: value("activityText"),
      });
      if (value("optionalActivityNo")) params.activity_no_optional = numberValue("optionalActivityNo");
      const result = await apiCall("/instructor/create-activity", params, { body: objectives("learningObjectives") });
      if (result.data && result.data.ok) renderActivities(result.data);
      return result;
    },
    updateActivity: () => {
      const patch = {};
      if (value("updateActivityText")) patch.activity_text = value("updateActivityText");
      const nextObjectives = objectives("updateLearningObjectives");
      if (nextObjectives.length) patch.learning_objectives = nextObjectives;
      return apiCall("/instructor/update-activity", instructorParams(courseActivity()), { body: patch });
    },
    startActivity: () => apiCall("/instructor/start-activity", instructorParams(courseActivity())),
    endActivity: () => apiCall("/instructor/end-activity", instructorParams(courseActivity())),
    resetActivity: () => apiCall("/instructor/reset-activity", instructorParams(courseActivity())),

    // ── Instructor grading ───────────────────────────────────────
    exportScores: async () => {
      const result = await apiCall("/instructor/export-scores", instructorParams(courseActivity()));
      latestCsv = (result.data && result.data.csv) || "";
      renderScores(result.data);
      el("downloadCsv").classList.toggle("hidden", !latestCsv);
      return result;
    },
    manualGrade: () => apiCall("/instructor/manual-grade", instructorParams({
      course_id: value("courseId"),
      student_id: numberValue("studentId"),
      activity_no: numberValue("activityNo"),
      score: numberValue("manualScore"),
      reason: value("manualReason"),
    })),
    resetStudentPassword: () => apiCall("/instructor/reset-student-password", instructorParams({
      course_id: value("courseId"),
      student_email: value("resetStudentEmail"),
      new_password: value("resetNewPassword"),
    })),

    // ── Student auth ─────────────────────────────────────────────
    studentLogin: () => apiCall("/student/login", studentParams()),
    setStudentPassword: () => apiCall("/student/set-password", studentParams()),
    changeStudentPassword: () => apiCall("/student/change-password", studentParams({
      old_password: value("studentOldPassword"),
      new_password: value("studentNewPassword"),
    })),

    // ── Student activity / tutoring ──────────────────────────────
    getActivity: async () => {
      const result = await apiCall("/student/get-activity", studentParams(courseActivity()));
      renderActivity(result.data);
      return result;
    },
    startTutoring: () => tutoring(""),
    submitAnswer: () => tutoring(value("studentAnswer")),
    logScore: async () => {
      const result = await apiCall("/student/log-score", studentParams(Object.assign(courseActivity(), {
        score: numberValue("studentScore"),
        meta: value("scoreMeta"),
      })));
      renderStudentState(result.data);
      return result;
    },

    // ── Negative tests ───────────────────────────────────────────
    badInstructorListActivities: () => expectedFailure("/instructor/list-activities", {
      email: value("badInstructorEmail"), password: value("badInstructorPassword"),
      course_id: value("courseId"),
    }),
    badInstructorResetActivity: () => expectedFailure("/instructor/reset-activity", Object.assign({
      email: value("badInstructorEmail"), password: value("badInstructorPassword"),
    }, courseActivity())),
    badInstructorManualGrade: () => expectedFailure("/instructor/manual-grade", {
      email: value("badInstructorEmail"), password: value("badInstructorPassword"),
      course_id: value("courseId"),
      student_id: numberValue("studentId"),
      activity_no: numberValue("activityNo"),
      score: numberValue("manualScore"),
      reason: value("manualReason"),
    }),
    badStudentGetActivity: () => expectedFailure("/student/get-activity", Object.assign({
      email: value("badStudentEmail"), password: value("badStudentPassword"),
    }, courseActivity())),
  };

  async function expectedFailure(path, params) {
    const result = await apiCall(path, params);
    const [label, kind] = classify(result.data, "expectedFailure");
    setBadge(el("lastBadge"), label, kind);
    return result;
  }

  async function tutoring(answer) {
    const params = studentParams(courseActivity());
    if (answer) params.answer = answer;
    addChat("student", answer || "Ask tutor / start tutoring");
    const result = await apiCall("/student/submit-tutoring-answer", params);
    const response = result.data || {};
    const guidance = response.assistant_response || response.guidance || response.message || response.response || response.feedback;
    addChat("assistant", guidance || format(response));
    renderStudentState(response);
    return result;
  }

  function addChat(kind, text) {
    // Hide the welcome state once real messages appear.
    const welcome = el("tutorWelcome");
    if (welcome && !welcome.classList.contains("hidden")) {
      welcome.classList.add("hidden");
    }
    const node = document.createElement("div");
    node.className = "message " + kind;
    node.textContent = text;
    el("chatPanel").appendChild(node);
    el("chatPanel").scrollTop = el("chatPanel").scrollHeight;
  }

  function renderActivity(data) {
    const activity = data && (data.activity || data);
    const text = activity && (activity.activity_text || activity.text || activity.content);
    el("activityDisplay").textContent = text || "No student-facing activity text found in response.";

    // Update the chat header badge with course + activity info.
    const courseBadge = el("chatCourseBadge");
    if (courseBadge) {
      const course = value("courseId") || "Course";
      const actNo = value("activityNo") || "?";
      courseBadge.textContent = course + " — Activity " + actNo;
    }

    const leaked = !!(activity && activity.learning_objectives);
    const warning = el("objectiveWarning");
    warning.className = leaked ? "integrity-pill error" : "integrity-pill success";
    warning.textContent = leaked
      ? "Problem: learning objectives exposed to student."
      : "Hidden instructional fields are not exposed.";
  }

  function renderStudentState(data) {
    const bits = [];
    ["score", "state", "status", "current_state"].forEach((key) => {
      if (data && data[key] !== undefined) bits.push(key + ": " + data[key]);
    });
    const text = bits.length ? bits.join(" | ") : "No score/state returned";
    el("studentStateDisplay").textContent = text;

    // Mirror score in the chat header pill.
    const pill = el("chatScorePill");
    if (pill) {
      if (bits.length) {
        pill.style.display = "";
        pill.textContent = text;
      } else {
        pill.style.display = "none";
      }
    }
  }

  function rowsFrom(data, keys) {
    if (!data || typeof data !== "object") return [];
    for (const key of keys) {
      if (Array.isArray(data[key])) return data[key];
    }
    if (Array.isArray(data)) return data;
    return [];
  }

  function renderTable(targetId, rows, columns, emptyText, onRowClick) {
    const target = el(targetId);
    if (!target) return;
    if (!rows.length) {
      target.className = "data-zone empty";
      target.textContent = emptyText;
      return;
    }
    target.className = "data-zone";
    const table = document.createElement("table");
    table.className = "data-table";
    const head = document.createElement("thead");
    head.innerHTML = "<tr>" + columns.map((c) => "<th>" + c.label + "</th>").join("") + "</tr>";
    table.appendChild(head);
    const body = document.createElement("tbody");
    rows.forEach((row) => {
      const tr = document.createElement("tr");
      if (onRowClick) tr.className = "click-row";
      columns.forEach((col) => {
        const td = document.createElement("td");
        const val = row[col.key];
        td.textContent = Array.isArray(val) ? val.join(", ") : val == null ? "" : String(val);
        tr.appendChild(td);
      });
      if (onRowClick) tr.addEventListener("click", () => onRowClick(row));
      body.appendChild(tr);
    });
    table.appendChild(body);
    target.replaceChildren(table);
  }

  function renderCourses(data) {
    const rows = rowsFrom(data, ["courses", "data", "items"]);
    renderTable("coursesDisplay", rows, [
      { key: "course_id", label: "Course ID" },
      { key: "course_name", label: "Name" },
      { key: "id", label: "Internal ID" },
    ], "No courses returned.", (row) => {
      setValue("courseId", row.course_id || row.id || "");
      setBadge(el("globalStatus"), "Course selected", "success");
    });
  }

  function renderActivities(data) {
    const rows = rowsFrom(data, ["activities", "data", "items"]);
    const single = data && data.activity ? [data.activity] : [];
    renderTable("activitiesDisplay", rows.length ? rows : single, [
      { key: "activity_no", label: "No" },
      { key: "status", label: "Status" },
      { key: "activity_text", label: "Activity text" },
      { key: "learning_objectives", label: "Objectives" },
    ], "No activities returned.", (row) => {
      if (row.activity_no !== undefined) setValue("activityNo", row.activity_no);
    });
  }

  function renderScores(data) {
    if (!latestCsv) { renderTable("scoresDisplay", [], [], "No CSV returned."); return; }
    renderTable("scoresDisplay", csvRows(latestCsv), [
      { key: "student_id", label: "Student ID" },
      { key: "student_email", label: "Email" },
      { key: "activity_no", label: "Activity" },
      { key: "score", label: "Score" },
      { key: "meta", label: "Meta" },
    ], "No score rows found.");
  }

  function csvRows(csvText) {
    const lines = csvText.trim().split(/\r?\n/);
    if (lines.length < 2) return [];
    const headers = lines[0].split(",");
    return lines.slice(1).map((line) => {
      const values = line.split(",");
      const row = {};
      headers.forEach((h, i) => { row[h] = values[i] || ""; });
      return row;
    });
  }

  function classify(data, expected) {
    if (expected === "expectedFailure") {
      return data && data.ok === false ? ["EXPECTED FAIL", "warning"] : ["UNEXPECTED", "error"];
    }
    if (expected === "postResetFailure") {
      const error = String((data && data.error) || "").toLowerCase();
      const pass = data && data.ok === false && (
        error.includes("not active") ||
        error.includes("activity is not active") ||
        error.includes("ended")
      );
      return pass ? ["PASS", "success"] : ["FAIL", "error"];
    }
    return data && data.ok === true ? ["PASS", "success"] : ["FAIL", "error"];
  }

  // ── Demo flow ─────────────────────────────────────────────────
  function initFlow() {
    const list = el("demoFlow");
    flowSteps.forEach(([title, explanation, endpoint, action, expected], index) => {
      const item = document.createElement("li");
      item.className = "flow-card";
      item.innerHTML =
        '<div class="flow-title">' +
        '<div class="flow-number">' + (index + 1) + '</div>' +
        '<div><strong>' + title + '</strong><p class="quiet">' + explanation + '</p>' +
        '<div class="endpoint">' + endpoint + '</div></div>' +
        '<span class="badge badge-neutral" id="flowBadge' + index + '">Not run</span>' +
        '</div>' +
        '<button data-flow="' + index + '">Run step</button>' +
        '<pre class="output" id="flowSummary' + index + '"></pre>' +
        '<pre class="output" id="flowResponse' + index + '"></pre>';
      list.appendChild(item);
      item.querySelector("button").addEventListener("click", async () => {
        const result = await actions[action]();
        renderTo("flowSummary" + index, result.requestSummary);
        renderTo("flowResponse" + index, result.data);
        const [label, kind] = classify(result.data, expected);
        setBadge(el("flowBadge" + index), label, kind);
      });
    });
  }

  // ── Inner tabs (Activities / Grading / Account within instructor) ──
  function initInnerTabs() {
    document.querySelectorAll("[data-tab-target]").forEach((button) => {
      button.addEventListener("click", () => {
        const panelId = button.dataset.tabTarget;
        const panel = el(panelId);
        if (!panel) return;

        // Deactivate sibling tabs.
        const tabBar = button.closest(".inner-tabs");
        if (tabBar) tabBar.querySelectorAll(".inner-tab").forEach((t) => t.classList.remove("active"));
        button.classList.add("active");

        // Deactivate sibling panels within the same section.
        const section = button.closest(".view");
        if (section) section.querySelectorAll(".inner-panel").forEach((p) => p.classList.remove("active-panel"));
        panel.classList.add("active-panel");
      });
    });
  }

  // ── Google Identity Services ───────────────────────────────────
  let pendingGoogleRole = null;

  function setGoogleStatus(role, message, kind) {
    const statusEl = el(role === "instructor" ? "googleStatusInstructor" : "googleStatusStudent");
    if (!statusEl) return;
    statusEl.textContent = message;
    statusEl.className = "google-status" + (kind ? " " + kind : "");
    statusEl.classList.remove("hidden");
  }

  function initGoogleIdentityServices(clientId) {
    if (!window.google || !window.google.accounts || !window.google.accounts.id) return;

    window.google.accounts.id.initialize({
      client_id: clientId,
      callback: async function (response) {
        const role = pendingGoogleRole || "student";
        if (!response || !response.credential) {
          setGoogleStatus(role, "No credential returned by Google.", "fail");
          return;
        }
        setGoogleStatus(role, "Verifying with backend…", "");
        const result = await actions.googleLogin(response.credential, role);
        const ok = result.data && result.data.ok;
        setGoogleStatus(role,
          ok ? "Signed in with Google." : "Backend rejected: " + (result.data && result.data.error),
          ok ? "ok" : "fail");
        renderTo(role === "instructor" ? "instructorOut" : "studentOut", result.data);
      },
      auto_select: false,
      cancel_on_tap_outside: true,
    });
  }

  function initGoogleButtons() {
    document.querySelectorAll("[data-google-role]").forEach((button) => {
      button.addEventListener("click", () => {
        const role = button.dataset.googleRole;
        pendingGoogleRole = role;

        if (!window.google || !window.google.accounts || !window.google.accounts.id) {
          setGoogleStatus(role, "Google Identity Services not yet loaded — check your connection.", "fail");
          return;
        }

        setGoogleStatus(role, "Opening Google sign-in…", "");
        window.google.accounts.id.prompt((notification) => {
          if (notification.isNotDisplayed()) {
            setGoogleStatus(role,
              "Sign-in dialog blocked (" + notification.getNotDisplayedReason() + "). " +
              "Add this origin to Authorized JavaScript Origins in Google Cloud Console.",
              "fail");
          } else if (notification.isSkippedMoment()) {
            setGoogleStatus(role, "Dismissed — click again to retry.", "fail");
          }
        });
      });
    });
  }

  async function loadGoogleClientId() {
    try {
      const resp = await fetch(baseUrl() + "/auth/google-client-id");
      if (!resp.ok) return;
      const data = await resp.json();
      if (!data.client_id) return;

      const clientId = data.client_id;
      const tryInit = () => {
        if (window.google && window.google.accounts && window.google.accounts.id) {
          initGoogleIdentityServices(clientId);
        } else {
          setTimeout(tryInit, 300);
        }
      };
      tryInit();
    } catch (_) {
      // GIS unavailable (offline) — silent fail, buttons just won't render.
    }
  }

  // ── Main navigation ────────────────────────────────────────────
  function initNavigation() {
    document.querySelectorAll("[data-view-target]").forEach((button) => {
      button.addEventListener("click", () => {
        document.querySelectorAll("[data-view-target]").forEach((n) => n.classList.remove("active"));
        document.querySelectorAll(".view").forEach((v) => v.classList.remove("active-view"));
        button.classList.add("active");
        const view = el(button.dataset.viewTarget);
        if (view) view.classList.add("active-view");
      });
    });
  }

  async function runAction(name) {
    const result = await actions[name]();
    renderTo(visibleOutputForAction(name), result.data);
    return result;
  }

  // ── Button wiring ──────────────────────────────────────────────
  function initButtons() {
    document.querySelectorAll("[data-action]").forEach((button) => {
      button.addEventListener("click", () => runAction(button.dataset.action));
    });

    el("saveDemoFields").addEventListener("click", saveFields);
    el("clearDemoFields").addEventListener("click", clearFields);
    el("clearHistory").addEventListener("click", () => {
      history.length = 0;
      renderHistory();
    });
    el("exportHistory").addEventListener("click", () =>
      downloadText("request-history.json", JSON.stringify(history, null, 2), "application/json")
    );
    el("downloadCsv").addEventListener("click", () =>
      downloadText("scores.csv", latestCsv, "text/csv")
    );

    setupFields.forEach((id) => {
      const n = el(id);
      if (n) n.addEventListener("input", updateReadyCard);
    });
  }

  // ── Field persistence ──────────────────────────────────────────
  function saveFields() {
    const safe = {}, passwords = {};
    setupFields.forEach((id) => {
      if (passwordKeys.has(id)) passwords[id] = value(id);
      else safe[id] = value(id);
    });
    localStorage.setItem(safeStorageKey, JSON.stringify(safe));
    if (el("rememberPasswords").checked) localStorage.setItem(passwordStorageKey, JSON.stringify(passwords));
    else localStorage.removeItem(passwordStorageKey);
    setBadge(el("globalStatus"), "Fields saved", "success");
    updateReadyCard();
  }

  function loadFields() {
    setValue("baseUrl", window.location.origin || "http://127.0.0.1:8000");
    const safe = JSON.parse(localStorage.getItem(safeStorageKey) || "{}");
    const passwords = JSON.parse(localStorage.getItem(passwordStorageKey) || "{}");
    Object.entries(Object.assign({}, safe, passwords)).forEach(([id, next]) => setValue(id, next));
    el("rememberPasswords").checked = Object.keys(passwords).length > 0;
    if (!value("activityNo")) setValue("activityNo", "1");
    updateReadyCard();
  }

  function clearFields() {
    localStorage.removeItem(safeStorageKey);
    localStorage.removeItem(passwordStorageKey);
    setupFields.forEach((id) => setValue(id, id === "baseUrl" ? (window.location.origin || "http://127.0.0.1:8000") : ""));
    setValue("activityNo", "1");
    el("rememberPasswords").checked = false;
    setBadge(el("globalStatus"), "Saved fields cleared", "warning");
    updateReadyCard();
  }

  function updateReadyCard() {
    const missing = requiredDemoFields.filter((id) => !value(id));
    const card = el("readyCard");
    if (!card) return;
    if (missing.length === 0) {
      card.className = "alert alert-success";
      card.innerHTML = "<strong>Ready for demo</strong><span>All required credentials and activity identifiers are filled.</span>";
    } else {
      card.className = "alert alert-warning";
      card.innerHTML = "<strong>Required fields missing</strong><span>Missing: " + missing.join(", ") + "</span>";
    }
  }

  // ── History ────────────────────────────────────────────────────
  function renderHistory() {
    const target = el("historyList");
    if (!target) return;
    if (!history.length) {
      target.className = "history-list empty";
      target.textContent = "No requests yet.";
      return;
    }
    target.className = "history-list";
    target.replaceChildren(...history.map((item) => {
      const div = document.createElement("div");
      div.className = "history-item";
      div.innerHTML =
        "<strong>" + item.request.method + " " + item.request.path + "</strong>" +
        "<span class=\"quiet\">" + item.at + "</span>" +
        "<pre class=\"output\">" + escapeHtml(format({ request: item.request, response: item.response })) + "</pre>";
      return div;
    }));
  }

  function escapeHtml(text) {
    return String(text).replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]));
  }

  function downloadText(filename, text, type) {
    const blob = new Blob([text || ""], { type });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  document.addEventListener("DOMContentLoaded", () => {
    loadFields();
    initNavigation();
    initInnerTabs();
    initButtons();
    initGoogleButtons();
    initFlow();
    renderHistory();
    loadGoogleClientId();
  });
}());
