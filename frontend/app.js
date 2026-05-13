(function () {
  "use strict";

  const fields = [
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
  const passwordFields = new Set([
    "instructorPassword",
    "studentPassword",
    "badInstructorPassword",
    "badStudentPassword",
  ]);
  const safeStorageKey = "inclassDemoUiFields";
  const passwordStorageKey = "inclassDemoUiPasswords";
  let latestCsv = "";

  const flowSteps = [
    ["Instructor login", "/instructor/login", "instructorLogin", "success"],
    ["Student login", "/student/login", "studentLogin", "success"],
    ["Instructor list my courses", "/instructor/list-my-courses", "listMyCourses", "success"],
    ["Instructor list activities", "/instructor/list-activities", "listActivities", "success"],
    ["Create activity", "/instructor/create-activity", "createActivity", "success"],
    ["Start activity", "/instructor/start-activity", "startActivity", "success"],
    ["Student get active activity", "/student/get-activity", "getActivity", "success"],
    ["Student submit tutoring answer", "/student/submit-tutoring-answer", "submitAnswer", "success"],
    ["Export scores", "/instructor/export-scores", "exportScores", "success"],
    ["Manual grade", "/instructor/manual-grade", "manualGrade", "success"],
    ["Reset activity", "/instructor/reset-activity", "resetActivity", "success"],
    ["Try student logScore after reset", "/student/log-score", "logScore", "postResetFailure"],
  ];

  function el(id) {
    return document.getElementById(id);
  }

  function value(id) {
    const node = el(id);
    return node ? node.value.trim() : "";
  }

  function numberValue(id) {
    const raw = value(id);
    return raw === "" ? "" : Number(raw);
  }

  function objectives(id) {
    return value(id)
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean);
  }

  function baseUrl() {
    return (value("baseUrl") || window.location.origin).replace(/\/+$/, "");
  }

  function setBadge(target, text, kind) {
    if (!target) return;
    target.className = "badge badge-" + kind;
    target.textContent = text;
  }

  function renderJson(targetId, data) {
    const target = el(targetId);
    if (target) target.textContent = format(data);
  }

  function format(data) {
    if (typeof data === "string") return data;
    return JSON.stringify(data, null, 2);
  }

  function masked(obj) {
    if (!obj || typeof obj !== "object") return obj;
    if (Array.isArray(obj)) return obj.map(masked);
    const copy = {};
    for (const [key, val] of Object.entries(obj)) {
      copy[key] = key.toLowerCase().includes("password") ? "***" : masked(val);
    }
    return copy;
  }

  function summary(method, path, params, body) {
    return {
      method,
      path,
      params: masked(params || {}),
      body: body === undefined ? undefined : masked(body),
    };
  }

  function classify(data, expected) {
    if (expected === "postResetFailure") {
      const error = String((data && data.error) || "").toLowerCase();
      return data && data.ok === false && error.includes("activity") && error.includes("active")
        ? ["PASS", "success"]
        : ["FAIL", "error"];
    }
    if (expected === "expectedFailure") {
      return data && data.ok === false ? ["EXPECTED FAILURE", "warning"] : ["UNEXPECTED", "error"];
    }
    return data && data.ok === true ? ["PASS", "success"] : ["FAIL", "error"];
  }

  async function apiCall(path, params, options) {
    const opts = options || {};
    const method = opts.method || "POST";
    const qs = new URLSearchParams();
    for (const [key, val] of Object.entries(params || {})) {
      if (val !== "" && val !== undefined && val !== null) qs.append(key, val);
    }
    const url = baseUrl() + path + (qs.toString() ? "?" + qs.toString() : "");
    const requestSummary = summary(method, path, params, opts.body);
    const fetchOptions = { method, headers: {} };
    if (opts.body !== undefined) {
      fetchOptions.headers["Content-Type"] = "application/json";
      fetchOptions.body = JSON.stringify(opts.body);
    }

    try {
      const response = await fetch(url, fetchOptions);
      const text = await response.text();
      let data;
      try {
        data = text ? JSON.parse(text) : {};
      } catch (err) {
        data = { ok: false, error: "Non-JSON response", status: response.status, body: text };
      }
      if (!response.ok && data && data.detail) {
        data = { ok: false, error: "HTTP " + response.status, detail: data.detail };
      }
      updateLast(requestSummary, data, response.ok);
      return { data, requestSummary, httpOk: response.ok };
    } catch (err) {
      const data = { ok: false, error: "Backend unreachable", detail: String(err.message || err) };
      updateLast(requestSummary, data, false);
      return { data, requestSummary, httpOk: false };
    }
  }

  function updateLast(requestSummary, data, httpOk) {
    el("lastSummary").textContent = format(requestSummary);
    el("lastResponse").textContent = format(data);
    const ok = data && data.ok === true;
    setBadge(el("lastBadge"), ok ? "Success" : httpOk ? "Backend returned error" : "Request failed", ok ? "success" : "error");
    setBadge(el("globalStatus"), ok ? "Last request ok" : "Check response", ok ? "success" : "warning");
  }

  function instructorParams(overrides) {
    return Object.assign({
      email: value("instructorEmail"),
      password: value("instructorPassword"),
    }, overrides || {});
  }

  function studentParams(overrides) {
    return Object.assign({
      email: value("studentEmail"),
      password: value("studentPassword"),
    }, overrides || {});
  }

  function courseActivity() {
    return {
      course_id: value("courseId"),
      activity_no: numberValue("activityNo"),
    };
  }

  async function health() {
    const result = await apiCall("/", {}, { method: "GET" });
    renderJson("healthOut", result.data);
    setBadge(el("healthBadge"), result.data && result.data.ok === true ? "ok true" : "Not ok", result.data && result.data.ok === true ? "success" : "error");
    return result;
  }

  const actions = {
    health,
    instructorLogin: () => apiCall("/instructor/login", instructorParams()),
    setInstructorPassword: () => apiCall("/instructor/set-password", instructorParams()),
    changeInstructorPassword: () => apiCall("/instructor/change-password", instructorParams({
      old_password: value("instructorOldPassword"),
      new_password: value("instructorNewPassword"),
    })),
    listMyCourses: () => apiCall("/instructor/list-my-courses", instructorParams()),
    listActivities: () => apiCall("/instructor/list-activities", instructorParams({ course_id: value("courseId") })),
    createActivity: () => {
      const params = instructorParams({
        course_id: value("courseId"),
        activity_text: value("activityText"),
      });
      const optionalNo = value("optionalActivityNo");
      if (optionalNo) params.activity_no_optional = Number(optionalNo);
      return apiCall("/instructor/create-activity", params, { body: objectives("learningObjectives") });
    },
    updateActivity: () => {
      const patch = {};
      if (value("updateActivityText")) patch.activity_text = value("updateActivityText");
      const newObjectives = objectives("updateLearningObjectives");
      if (newObjectives.length) patch.learning_objectives = newObjectives;
      return apiCall("/instructor/update-activity", instructorParams(courseActivity()), { body: patch });
    },
    startActivity: () => apiCall("/instructor/start-activity", instructorParams(courseActivity())),
    endActivity: () => apiCall("/instructor/end-activity", instructorParams(courseActivity())),
    resetActivity: () => apiCall("/instructor/reset-activity", instructorParams(courseActivity())),
    exportScores: async () => {
      const result = await apiCall("/instructor/export-scores", instructorParams(courseActivity()));
      latestCsv = (result.data && (result.data.csv || result.data.csv_text || result.data.content)) || "";
      el("csvTools").classList.toggle("hidden", !latestCsv);
      el("csvOut").textContent = latestCsv;
      return result;
    },
    resetStudentPassword: () => apiCall("/instructor/reset-student-password", instructorParams({
      course_id: value("courseId"),
      student_email: value("resetStudentEmail"),
      new_password: value("resetNewPassword"),
    })),
    manualGrade: () => apiCall("/instructor/manual-grade", instructorParams({
      course_id: value("courseId"),
      student_id: numberValue("studentId"),
      activity_no: numberValue("activityNo"),
      score: numberValue("manualScore"),
      reason: value("manualReason"),
    })),
    studentLogin: () => apiCall("/student/login", studentParams()),
    setStudentPassword: () => apiCall("/student/set-password", studentParams()),
    changeStudentPassword: () => apiCall("/student/change-password", studentParams({
      old_password: value("studentOldPassword"),
      new_password: value("studentNewPassword"),
    })),
    getActivity: async () => {
      const result = await apiCall("/student/get-activity", studentParams(courseActivity()));
      renderActivity(result.data);
      return result;
    },
    startTutoring: () => tutoring(""),
    submitAnswer: () => tutoring(value("studentAnswer")),
    logScore: () => apiCall("/student/log-score", studentParams(Object.assign(courseActivity(), {
      score: numberValue("studentScore"),
      meta: value("scoreMeta"),
    }))),
    badInstructorListActivities: () => expectedFailure("/instructor/list-activities", {
      email: value("badInstructorEmail"),
      password: value("badInstructorPassword"),
      course_id: value("courseId"),
    }),
    badInstructorResetActivity: () => expectedFailure("/instructor/reset-activity", Object.assign({
      email: value("badInstructorEmail"),
      password: value("badInstructorPassword"),
    }, courseActivity())),
    badInstructorManualGrade: () => expectedFailure("/instructor/manual-grade", {
      email: value("badInstructorEmail"),
      password: value("badInstructorPassword"),
      course_id: value("courseId"),
      student_id: numberValue("studentId"),
      activity_no: numberValue("activityNo"),
      score: numberValue("manualScore"),
      reason: value("manualReason"),
    }),
    badStudentGetActivity: () => expectedFailure("/student/get-activity", Object.assign({
      email: value("badStudentEmail"),
      password: value("badStudentPassword"),
    }, courseActivity())),
  };

  async function expectedFailure(path, params) {
    const result = await apiCall(path, params);
    renderJson("negativeOut", result.data);
    const [label, kind] = classify(result.data, "expectedFailure");
    setBadge(el("lastBadge"), label, kind);
    return result;
  }

  async function tutoring(answer) {
    const params = studentParams(courseActivity());
    if (answer) params.answer = answer;
    const result = await apiCall("/student/submit-tutoring-answer", params);
    addChat(answer ? "student" : "student", answer || "Start / continue tutoring");
    const guidance = result.data && (result.data.assistant_response || result.data.guidance || result.data.message || result.data.response);
    addChat("assistant", guidance || format(result.data));
    return result;
  }

  function addChat(kind, text) {
    const msg = document.createElement("div");
    msg.className = "message " + kind;
    msg.textContent = text;
    el("chatPanel").appendChild(msg);
  }

  function renderActivity(data) {
    const display = el("activityDisplay");
    const activity = data && (data.activity || data);
    const text = activity && (activity.activity_text || activity.text || activity.content);
    display.textContent = text ? text : "No activity content found in response.";
    const leaked = !!(activity && activity.learning_objectives);
    el("objectiveWarning").className = leaked ? "notice badge badge-error" : "notice badge badge-warning";
    el("objectiveWarning").textContent = leaked
      ? "Warning: response contains learning_objectives."
      : "Learning objectives should not be exposed to student.";
  }

  async function runAction(name, outputId) {
    const result = await actions[name]();
    if (outputId) renderJson(outputId, result.data);
    return result;
  }

  function initFlow() {
    const list = el("demoFlow");
    flowSteps.forEach((step, index) => {
      const [title, endpoint, action, expected] = step;
      const item = document.createElement("li");
      item.className = "flow-card";
      item.innerHTML = '<div class="flow-title"><strong>' + title + '</strong><span class="badge badge-neutral" id="flowBadge' + index + '">Not run</span></div>' +
        '<div class="endpoint">' + endpoint + '</div>' +
        '<button data-flow="' + index + '">Run step</button>' +
        '<pre class="request-summary" id="flowSummary' + index + '"></pre>' +
        '<pre class="flow-response" id="flowResponse' + index + '"></pre>';
      list.appendChild(item);
      item.querySelector("button").addEventListener("click", async () => {
        const result = await actions[action]();
        el("flowSummary" + index).textContent = format(result.requestSummary);
        el("flowResponse" + index).textContent = format(result.data);
        const [label, kind] = classify(result.data, expected);
        setBadge(el("flowBadge" + index), label, kind);
      });
    });
  }

  function saveFields() {
    const safe = {};
    const passwords = {};
    fields.forEach((id) => {
      if (passwordFields.has(id)) passwords[id] = value(id);
      else safe[id] = value(id);
    });
    localStorage.setItem(safeStorageKey, JSON.stringify(safe));
    if (el("rememberPasswords").checked) {
      localStorage.setItem(passwordStorageKey, JSON.stringify(passwords));
    } else {
      localStorage.removeItem(passwordStorageKey);
    }
    setBadge(el("globalStatus"), "Saved", "success");
  }

  function loadFields() {
    el("baseUrl").value = window.location.origin;
    const safe = JSON.parse(localStorage.getItem(safeStorageKey) || "{}");
    const passwords = JSON.parse(localStorage.getItem(passwordStorageKey) || "{}");
    Object.entries(Object.assign({}, safe, passwords)).forEach(([id, val]) => {
      if (el(id)) el(id).value = val;
    });
    el("rememberPasswords").checked = Object.keys(passwords).length > 0;
  }

  function clearFields() {
    localStorage.removeItem(safeStorageKey);
    localStorage.removeItem(passwordStorageKey);
    fields.forEach((id) => {
      if (el(id)) el(id).value = id === "baseUrl" ? window.location.origin : "";
    });
    el("activityNo").value = "1";
    el("rememberPasswords").checked = false;
    setBadge(el("globalStatus"), "Cleared", "warning");
  }

  function initButtons() {
    document.querySelectorAll("[data-action]").forEach((button) => {
      button.addEventListener("click", async () => {
        const action = button.getAttribute("data-action");
        let output = "instructorOut";
        if (action === "health") output = "healthOut";
        if (["studentLogin", "setStudentPassword", "changeStudentPassword", "getActivity", "startTutoring", "submitAnswer", "logScore"].includes(action)) output = "studentOut";
        if (action.startsWith("bad")) output = "negativeOut";
        await runAction(action, output);
      });
    });
    el("saveDemoFields").addEventListener("click", saveFields);
    el("clearDemoFields").addEventListener("click", clearFields);
    el("downloadCsv").addEventListener("click", () => {
      const blob = new Blob([latestCsv], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "scores.csv";
      link.click();
      URL.revokeObjectURL(url);
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    loadFields();
    initButtons();
    initFlow();
  });
}());
