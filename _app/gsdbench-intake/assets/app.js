(function () {
  "use strict";

  const STORAGE_KEY = "gsdbench-intake-draft-v1";
  const form = document.getElementById("intakeForm");
  const issueTitleEl = document.getElementById("issueTitle");
  const issueBodyEl = document.getElementById("issueBody");
  const validationSummaryEl = document.getElementById("validationSummary");
  const validityBadgeEl = document.getElementById("validityBadge");
  const saveStatusEl = document.getElementById("saveStatus");
  const copyStatusEl = document.getElementById("copyStatus");
  const numericalChecksEl = document.getElementById("numericalChecks");
  const rubricRowsEl = document.getElementById("rubricRows");
  const numericalTemplate = document.getElementById("numericalCheckTemplate");
  const rubricTemplate = document.getElementById("rubricTemplate");
  const actionButtons = [
    "copyTitle",
    "copyBody",
    "copyBoth",
    "downloadMarkdown",
    "copyJson"
  ].map((id) => document.getElementById(id));

  let saveTimer = null;
  let caseIdManuallyEdited = false;
  let isPopulating = false;

  document.addEventListener("DOMContentLoaded", init);

  function init() {
    restoreDraft();
    if (rubricRowsEl.children.length === 0) {
      addRubricRow({
        axis: "numerical/statistical correctness",
        criterion_type: "reward",
        points: 4
      });
    }

    form.addEventListener("input", handleFormInput);
    form.addEventListener("change", handleFormInput);
    document.getElementById("caseId").addEventListener("input", () => {
      caseIdManuallyEdited = true;
    });
    document.getElementById("shortTitle").addEventListener("input", handleTitleInput);
    document.getElementById("addNumericalCheck").addEventListener("click", () => addNumericalCheckRow());
    document.getElementById("addRubric").addEventListener("click", () => addRubricRow());
    document.getElementById("loadExample").addEventListener("click", loadSyntheticExample);
    document.getElementById("clearDraft").addEventListener("click", clearDraft);
    document.querySelectorAll(".fatal-template").forEach((button) => {
      button.addEventListener("click", () => {
        addRubricRow({
          axis: "communication/safety",
          criterion_type: "fatal_gate",
          points: -10,
          criterion: button.dataset.template,
          grading_hint: "Treat as a fatal gate if the issue materially affects benchmark validity or public sharing."
        });
      });
    });

    document.getElementById("copyTitle").addEventListener("click", () => copyText(issueTitleEl.value, "Issue title copied."));
    document.getElementById("copyBody").addEventListener("click", () => copyText(issueBodyEl.value, "Issue body copied."));
    document.getElementById("copyBoth").addEventListener("click", () => {
      copyText(`${issueTitleEl.value}\n\n${issueBodyEl.value}`, "Issue title and body copied.");
    });
    document.getElementById("copyJson").addEventListener("click", () => {
      const data = collectFormData();
      copyText(JSON.stringify(buildIssueJson(data), null, 2), "Machine-readable JSON copied.");
    });
    document.getElementById("downloadMarkdown").addEventListener("click", downloadIssueMarkdown);

    renderPreview();
  }

  function handleFormInput(event) {
    if (event.target.matches("[data-field]")) {
      updateRubricIds();
      syncRubricPointDefaults(event.target);
    }
    saveDraft();
    renderPreview();
  }

  function handleTitleInput() {
    const title = document.getElementById("shortTitle").value;
    const caseIdEl = document.getElementById("caseId");
    if (!caseIdManuallyEdited || !caseIdEl.value.trim()) {
      caseIdEl.value = generateCaseId(title);
    }
  }

  function textValue(id) {
    const el = document.getElementById(id);
    return el ? el.value.trim() : "";
  }

  function checkedValues(name) {
    return Array.from(document.querySelectorAll(`input[name="${name}"]:checked`)).map((el) => el.value);
  }

  function setCheckedValues(name, values) {
    const set = new Set(values || []);
    document.querySelectorAll(`input[name="${name}"]`).forEach((el) => {
      el.checked = set.has(el.value);
    });
  }

  function collectFormData() {
    const confidentiality = checkedValues("confidentiality");
    return {
      schema_version: "gsdbench.case.v0.1",
      case_id: textValue("caseId"),
      short_title: textValue("shortTitle"),
      submission_type: "case_proposal",
      created_from: "GSDBench Intake static app",
      contributor: {
        name_or_initials: textValue("contributorName"),
        github_username: textValue("githubUsername"),
        role: textValue("contributorRole"),
        organization_type: textValue("organizationType")
      },
      governance: {
        source_type: textValue("sourceType"),
        no_phi_or_confidential_info_confirmed: confidentiality.includes("no_phi"),
        permission_or_deidentification_confirmed: confidentiality.includes("permission"),
        maintainer_revision_understood: confidentiality.includes("revisions")
      },
      benchmark_metadata: {
        project: "GSDBench",
        suggested_split: textValue("suggestedSplit"),
        difficulty: textValue("difficulty"),
        priority: textValue("casePriority"),
        tags: checkedValues("tags")
      },
      task: {
        agent_prompt: document.getElementById("agentPrompt").value.trim(),
        prior_context: document.getElementById("priorContext").value.trim(),
        expected_deliverables: checkedValues("expectedDeliverables"),
        allowed_tools: checkedValues("allowedTools")
      },
      trial_design: {
        disease_setting: textValue("diseaseSetting"),
        phase: textValue("phase"),
        endpoint_structure: textValue("endpointStructure"),
        endpoint_names: textValue("endpointNames"),
        population_hypothesis_structure: document.getElementById("populationHypothesis").value.trim(),
        randomization_ratio: textValue("randomizationRatio"),
        alpha_multiplicity_strategy: document.getElementById("alphaMultiplicity").value.trim(),
        analyses_information_fractions: document.getElementById("analysesInformation").value.trim(),
        spending_futility: document.getElementById("spendingFutility").value.trim(),
        survival_assumptions: document.getElementById("survivalAssumptions").value.trim(),
        enrollment_dropout: document.getElementById("enrollmentDropout").value.trim(),
        operational_constraints: document.getElementById("operationalConstraints").value.trim(),
        nph_assumptions: document.getElementById("nphAssumptions").value.trim(),
        other_design_assumptions: document.getElementById("otherDesignAssumptions").value.trim()
      },
      reference_truth: {
        truth_types: checkedValues("truthTypes"),
        reference_script_summary: document.getElementById("referenceScriptSummary").value.trim(),
        reference_code_snippet: document.getElementById("referenceCodeSnippet").value.trim(),
        numerical_checks: collectNumericalChecks(),
        textual_ground_truth: document.getElementById("textualGroundTruth").value.trim(),
        simulation_requirements: document.getElementById("simulationRequirements").value.trim(),
        known_gotchas: checkedValues("knownGotchas")
      },
      rubric: collectRubric(),
      review: {
        suggested_reviewer_expertise: checkedValues("reviewerExpertise"),
        why_case_matters: document.getElementById("whyCaseMatters").value.trim(),
        expected_model_failure_modes: document.getElementById("expectedFailureModes").value.trim(),
        maintainer_notes: document.getElementById("maintainerNotes").value.trim()
      }
    };
  }

  function collectNumericalChecks() {
    return Array.from(numericalChecksEl.querySelectorAll(".numerical-card")).map((card) => ({
      metric_name: card.querySelector('[data-field="metric_name"]').value.trim(),
      expected_value: card.querySelector('[data-field="expected_value"]').value.trim(),
      tolerance_type: card.querySelector('[data-field="tolerance_type"]').value.trim(),
      tolerance_value: card.querySelector('[data-field="tolerance_value"]').value.trim(),
      units: card.querySelector('[data-field="units"]').value.trim(),
      notes: card.querySelector('[data-field="notes"]').value.trim()
    }));
  }

  function collectRubric() {
    return Array.from(rubricRowsEl.querySelectorAll(".rubric-card")).map((card, index) => ({
      id: `R${index + 1}`,
      axis: card.querySelector('[data-field="axis"]').value,
      criterion_type: card.querySelector('[data-field="criterion_type"]').value,
      points: Number(card.querySelector('[data-field="points"]').value),
      criterion: card.querySelector('[data-field="criterion"]').value.trim(),
      grading_hint: card.querySelector('[data-field="grading_hint"]').value.trim(),
      machine_checkable: card.querySelector('[data-field="machine_checkable"]').checked,
      reviewer_notes: card.querySelector('[data-field="reviewer_notes"]').value.trim()
    }));
  }

  function validateData(data) {
    const errors = [];
    const fieldErrors = {};
    const add = (field, message) => {
      errors.push(message);
      if (field) {
        fieldErrors[field] = message;
      }
    };

    if (!data.contributor.github_username) add("githubUsername", "GitHub username is required.");
    if (!data.governance.source_type) add("sourceType", "Source type is required.");
    if (!data.governance.no_phi_or_confidential_info_confirmed || !data.governance.permission_or_deidentification_confirmed || !data.governance.maintainer_revision_understood) {
      add("confidentiality", "All confidentiality confirmations are required.");
    }
    if (!data.short_title) add("shortTitle", "Short case title is required.");
    if (!data.case_id) {
      add("caseId", "Case ID is required.");
    } else if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(data.case_id)) {
      add("caseId", "Case ID must use lowercase letters, numbers, and hyphens only.");
    }
    if (data.benchmark_metadata.tags.length === 0) add("tags", "Select at least one benchmark tag.");
    if (!data.task.agent_prompt) add("agentPrompt", "Agent prompt is required.");
    if (data.task.expected_deliverables.length === 0) add("deliverables", "Select at least one expected deliverable.");
    if (!data.trial_design.endpoint_structure) add("endpointStructure", "Endpoint structure is required.");
    if (!data.trial_design.endpoint_names) add("endpointNames", "Endpoint names are required.");
    if (data.reference_truth.truth_types.length === 0) add("truthTypes", "Select at least one reference truth type.");

    const incompleteChecks = data.reference_truth.numerical_checks
      .map((check, index) => ({ check, index }))
      .filter(({ check }) => !check.metric_name || !check.expected_value || !check.tolerance_type || !check.tolerance_value);
    if (incompleteChecks.length > 0) {
      add("numericalChecks", `Complete required fields for numerical check ${incompleteChecks[0].index + 1}.`);
    }

    if (data.rubric.length < 4) add("rubric", "At least 4 rubric criteria are required.");
    if (!data.rubric.some((row) => row.axis === "numerical/statistical correctness")) {
      add("rubric", "At least one rubric criterion must cover numerical/statistical correctness.");
    }
    if (!data.rubric.some((row) => row.criterion_type === "penalty" || row.criterion_type === "fatal_gate")) {
      add("rubric", "At least one rubric criterion must be a penalty or fatal gate.");
    }
    if (data.rubric.reduce((sum, row) => sum + (row.points > 0 ? row.points : 0), 0) <= 0) {
      add("rubric", "Total positive rubric points must be greater than 0.");
    }

    data.rubric.forEach((row) => {
      if (!row.axis || !row.criterion_type || !row.criterion) {
        add("rubric", `${row.id} is missing required rubric fields.`);
      }
      if (!Number.isInteger(row.points) || row.points < -10 || row.points > 10 || row.points === 0) {
        add("rubric", `${row.id} points must be a nonzero integer from -10 to 10.`);
      }
      if (row.criterion_type === "reward" && row.points <= 0) {
        add("rubric", `${row.id} reward criteria must have positive points.`);
      }
      if (row.criterion_type === "penalty" && row.points >= 0) {
        add("rubric", `${row.id} penalty criteria must have negative points.`);
      }
      if (row.criterion_type === "fatal_gate" && row.points >= 0) {
        add("rubric", `${row.id} fatal gates must have negative points.`);
      }
    });

    return { valid: errors.length === 0, errors, fieldErrors };
  }

  function generateCaseId(title) {
    const now = new Date();
    const yyyy = now.getFullYear();
    const mm = String(now.getMonth() + 1).padStart(2, "0");
    const dd = String(now.getDate()).padStart(2, "0");
    const slug = slugify(title || "case");
    return `gsdb-${yyyy}${mm}${dd}-${slug}`;
  }

  function slugify(value) {
    return String(value)
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .replace(/-{2,}/g, "-")
      .slice(0, 56) || "case";
  }

  function generateIssueTitle(data) {
    return `[GSDBench Case Proposal] ${data.case_id || "gsdb-case-id"}: ${data.short_title || "Untitled case"}`;
  }

  function buildIssueJson(data) {
    return {
      schema_version: data.schema_version,
      case_id: data.case_id,
      short_title: data.short_title,
      submission_type: data.submission_type,
      created_from: data.created_from,
      contributor: {
        name_or_initials: data.contributor.name_or_initials,
        github_username: data.contributor.github_username,
        role: data.contributor.role,
        organization_type: data.contributor.organization_type
      },
      governance: {
        source_type: data.governance.source_type,
        no_phi_or_confidential_info_confirmed: data.governance.no_phi_or_confidential_info_confirmed,
        permission_or_deidentification_confirmed: data.governance.permission_or_deidentification_confirmed,
        maintainer_revision_understood: data.governance.maintainer_revision_understood
      },
      benchmark_metadata: data.benchmark_metadata,
      task: data.task,
      trial_design: data.trial_design,
      reference_truth: data.reference_truth,
      rubric: data.rubric,
      review: data.review
    };
  }

  function generateIssueBody(data) {
    const json = JSON.stringify(buildIssueJson(data), null, 2);
    const fatalGates = data.rubric.filter((row) => row.criterion_type === "fatal_gate");
    return [
      "<!-- GSDBENCH_CASE_JSON_BEGIN -->",
      "```json",
      json,
      "```",
      "<!-- GSDBENCH_CASE_JSON_END -->",
      "",
      "## Summary",
      bullet("Case ID", data.case_id),
      bullet("Short title", data.short_title),
      bullet("Suggested split", data.benchmark_metadata.suggested_split),
      bullet("Difficulty", data.benchmark_metadata.difficulty),
      bullet("Priority", data.benchmark_metadata.priority),
      bullet("Tags", joinList(data.benchmark_metadata.tags)),
      "",
      "## Benchmark Prompt",
      mdBlock(data.task.agent_prompt),
      data.task.prior_context ? `\n**Prior context**\n\n${mdBlock(data.task.prior_context)}` : "",
      "",
      bullet("Expected deliverables", joinList(data.task.expected_deliverables)),
      bullet("Allowed or expected tools/packages", joinList(data.task.allowed_tools)),
      "",
      "## Trial Design Context",
      bullet("Disease/setting", data.trial_design.disease_setting),
      bullet("Phase", data.trial_design.phase),
      bullet("Endpoint structure", data.trial_design.endpoint_structure),
      bullet("Endpoint names", data.trial_design.endpoint_names),
      bullet("Population/hypothesis structure", data.trial_design.population_hypothesis_structure),
      bullet("Randomization ratio", data.trial_design.randomization_ratio),
      bullet("Alpha/multiplicity strategy", data.trial_design.alpha_multiplicity_strategy),
      bullet("Number of analyses / information fractions", data.trial_design.analyses_information_fractions),
      bullet("Spending functions / futility rules", data.trial_design.spending_futility),
      bullet("Survival assumptions", data.trial_design.survival_assumptions),
      bullet("Enrollment/dropout assumptions", data.trial_design.enrollment_dropout),
      bullet("Operational constraints", data.trial_design.operational_constraints),
      bullet("NPH assumptions", data.trial_design.nph_assumptions),
      bullet("Other design assumptions", data.trial_design.other_design_assumptions),
      "",
      "## Reference Ground Truth",
      bullet("Reference truth type", joinList(data.reference_truth.truth_types)),
      bullet("Reference script summary or link/path", data.reference_truth.reference_script_summary),
      codeSnippet("Reference R code snippet", data.reference_truth.reference_code_snippet, "r"),
      bullet("Textual ground truth / expected reasoning", data.reference_truth.textual_ground_truth),
      bullet("Simulation requirements", data.reference_truth.simulation_requirements),
      "",
      "## Numerical Checks",
      numericalChecksTable(data.reference_truth.numerical_checks),
      "",
      "## Rubric Criteria",
      rubricTable(data.rubric),
      "",
      "## Fatal Error Gates",
      fatalGates.length ? fatalGates.map((row) => `- **${escapeInline(row.id)}** (${escapeInline(String(row.points))}): ${escapeInline(row.criterion)}`).join("\n") : "_No fatal gates specified._",
      "",
      "## Known Gotchas",
      listItems(data.reference_truth.known_gotchas),
      "",
      "## Suggested Review",
      bullet("Suggested reviewer expertise", joinList(data.review.suggested_reviewer_expertise)),
      bullet("Why this case matters", data.review.why_case_matters),
      bullet("Expected failure modes for current AI agents", data.review.expected_model_failure_modes),
      bullet("Additional notes to maintainers", data.review.maintainer_notes),
      "",
      "## Contributor Governance Checklist",
      `- [${data.governance.no_phi_or_confidential_info_confirmed ? "x" : " "}] No PHI, patient-level data, confidential protocol text, trade secrets, or proprietary company information.`,
      `- [${data.governance.permission_or_deidentification_confirmed ? "x" : " "}] Permission to share publicly, or sufficiently generalized/de-identified.`,
      `- [${data.governance.maintainer_revision_understood ? "x" : " "}] Maintainers may request revisions before accepting this case.`,
      bullet("Source type", data.governance.source_type),
      bullet("Contributor name or initials", data.contributor.name_or_initials),
      bullet("Contributor GitHub username", data.contributor.github_username),
      bullet("Contributor role", data.contributor.role),
      bullet("Organization type", data.contributor.organization_type)
    ].filter((part) => part !== "").join("\n");
  }

  function renderPreview() {
    const data = collectFormData();
    const validation = validateData(data);
    issueTitleEl.value = generateIssueTitle(data);
    issueBodyEl.value = generateIssueBody(data);
    renderValidation(validation);
    renderInlineErrors(validation.fieldErrors);
    actionButtons.forEach((button) => {
      button.disabled = !validation.valid;
    });
    validityBadgeEl.textContent = validation.valid ? "Valid" : "Draft";
    validityBadgeEl.classList.toggle("valid", validation.valid);
  }

  function renderValidation(validation) {
    validationSummaryEl.className = `validation-summary ${validation.valid ? "valid" : "invalid"}`;
    if (validation.valid) {
      validationSummaryEl.innerHTML = "<p>Valid issue draft. Copy and paste into a new GitHub issue.</p>";
      return;
    }
    const visibleErrors = validation.errors.slice(0, 8);
    validationSummaryEl.innerHTML = [
      `<p>${validation.errors.length} item${validation.errors.length === 1 ? "" : "s"} need attention before copying is enabled.</p>`,
      "<ul>",
      visibleErrors.map((message) => `<li>${escapeHtml(message)}</li>`).join(""),
      validation.errors.length > visibleErrors.length ? `<li>${validation.errors.length - visibleErrors.length} more item(s).</li>` : "",
      "</ul>"
    ].join("");
  }

  function renderInlineErrors(fieldErrors) {
    const errorIds = {
      githubUsername: "githubUsername-error",
      sourceType: "sourceType-error",
      confidentiality: "confidentiality-error",
      shortTitle: "shortTitle-error",
      caseId: "caseId-error",
      tags: "tags-error",
      agentPrompt: "agentPrompt-error",
      deliverables: "deliverables-error",
      endpointStructure: "endpointStructure-error",
      endpointNames: "endpointNames-error",
      truthTypes: "truthTypes-error",
      numericalChecks: "numericalChecks-error",
      rubric: "rubric-error"
    };
    Object.entries(errorIds).forEach(([field, id]) => {
      const el = document.getElementById(id);
      if (el) {
        el.textContent = fieldErrors[field] || "";
      }
    });
    document.querySelectorAll(".has-error").forEach((el) => el.classList.remove("has-error"));
    Object.keys(fieldErrors).forEach((field) => {
      const control = document.getElementById(field);
      if (control) {
        control.closest(".field")?.classList.add("has-error");
      }
    });
  }

  function saveDraft() {
    clearTimeout(saveTimer);
    saveStatusEl.textContent = "Saving...";
    saveTimer = setTimeout(() => {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(collectFormData()));
        saveStatusEl.textContent = "Draft saved";
      } catch (error) {
        saveStatusEl.textContent = "Draft not saved";
      }
    }, 250);
  }

  function restoreDraft() {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      saveStatusEl.textContent = "Draft ready";
      return;
    }
    try {
      const data = JSON.parse(raw);
      populateForm(data);
      saveStatusEl.textContent = "Draft restored";
    } catch (error) {
      saveStatusEl.textContent = "Could not restore draft";
    }
  }

  function populateForm(data) {
    isPopulating = true;
    setValue("contributorName", data.contributor?.name_or_initials || "");
    setValue("githubUsername", data.contributor?.github_username || "");
    setValue("contributorRole", data.contributor?.role || "Industry statistician");
    setValue("organizationType", data.contributor?.organization_type || "");
    setValue("sourceType", data.governance?.source_type || "");
    setCheckedValues("confidentiality", [
      data.governance?.no_phi_or_confidential_info_confirmed ? "no_phi" : "",
      data.governance?.permission_or_deidentification_confirmed ? "permission" : "",
      data.governance?.maintainer_revision_understood ? "revisions" : ""
    ].filter(Boolean));

    setValue("shortTitle", data.short_title || "");
    setValue("caseId", data.case_id || "");
    caseIdManuallyEdited = Boolean(data.case_id);
    setValue("suggestedSplit", data.benchmark_metadata?.suggested_split || "Public/dev");
    setValue("difficulty", data.benchmark_metadata?.difficulty || "Basic");
    setValue("casePriority", data.benchmark_metadata?.priority || "Routine design");
    setCheckedValues("tags", data.benchmark_metadata?.tags || []);

    setValue("agentPrompt", data.task?.agent_prompt || "");
    setValue("priorContext", data.task?.prior_context || "");
    setCheckedValues("expectedDeliverables", data.task?.expected_deliverables || []);
    setCheckedValues("allowedTools", data.task?.allowed_tools || []);

    const trial = data.trial_design || {};
    setValue("diseaseSetting", trial.disease_setting || "");
    setValue("phase", trial.phase || "Phase 3");
    setValue("endpointStructure", trial.endpoint_structure || "");
    setValue("endpointNames", trial.endpoint_names || "");
    setValue("populationHypothesis", trial.population_hypothesis_structure || "");
    setValue("randomizationRatio", trial.randomization_ratio || "");
    setValue("alphaMultiplicity", trial.alpha_multiplicity_strategy || "");
    setValue("analysesInformation", trial.analyses_information_fractions || "");
    setValue("spendingFutility", trial.spending_futility || "");
    setValue("survivalAssumptions", trial.survival_assumptions || "");
    setValue("enrollmentDropout", trial.enrollment_dropout || "");
    setValue("operationalConstraints", trial.operational_constraints || "");
    setValue("nphAssumptions", trial.nph_assumptions || "");
    setValue("otherDesignAssumptions", trial.other_design_assumptions || "");

    const truth = data.reference_truth || {};
    setCheckedValues("truthTypes", truth.truth_types || []);
    setValue("referenceScriptSummary", truth.reference_script_summary || "");
    setValue("referenceCodeSnippet", truth.reference_code_snippet || "");
    setValue("textualGroundTruth", truth.textual_ground_truth || "");
    setValue("simulationRequirements", truth.simulation_requirements || "");
    setCheckedValues("knownGotchas", truth.known_gotchas || []);
    numericalChecksEl.innerHTML = "";
    (truth.numerical_checks || []).forEach((row) => addNumericalCheckRow(row));

    rubricRowsEl.innerHTML = "";
    (data.rubric || []).forEach((row) => addRubricRow(row));

    const review = data.review || {};
    setCheckedValues("reviewerExpertise", review.suggested_reviewer_expertise || []);
    setValue("whyCaseMatters", review.why_case_matters || "");
    setValue("expectedFailureModes", review.expected_model_failure_modes || "");
    setValue("maintainerNotes", review.maintainer_notes || "");
    isPopulating = false;
  }

  function setValue(id, value) {
    const el = document.getElementById(id);
    if (el) {
      el.value = value;
    }
  }

  function clearDraft() {
    if (!window.confirm("Clear the saved local draft and reset the form?")) {
      return;
    }
    localStorage.removeItem(STORAGE_KEY);
    form.reset();
    numericalChecksEl.innerHTML = "";
    rubricRowsEl.innerHTML = "";
    caseIdManuallyEdited = false;
    addRubricRow({
      axis: "numerical/statistical correctness",
      criterion_type: "reward",
      points: 4
    });
    saveStatusEl.textContent = "Draft cleared";
    renderPreview();
  }

  function addNumericalCheckRow(values = {}) {
    const node = numericalTemplate.content.firstElementChild.cloneNode(true);
    node.querySelector('[data-field="metric_name"]').value = values.metric_name || "";
    node.querySelector('[data-field="expected_value"]').value = values.expected_value || "";
    node.querySelector('[data-field="tolerance_type"]').value = values.tolerance_type || "absolute";
    node.querySelector('[data-field="tolerance_value"]').value = values.tolerance_value || "";
    node.querySelector('[data-field="units"]').value = values.units || "";
    node.querySelector('[data-field="notes"]').value = values.notes || "";
    node.querySelector(".remove-row").addEventListener("click", () => {
      node.remove();
      saveDraft();
      renderPreview();
    });
    numericalChecksEl.appendChild(node);
    if (!isPopulating) {
      saveDraft();
      renderPreview();
    }
  }

  function addRubricRow(values = {}) {
    const node = rubricTemplate.content.firstElementChild.cloneNode(true);
    node.querySelector('[data-field="axis"]').value = values.axis || "design judgment";
    node.querySelector('[data-field="criterion_type"]').value = values.criterion_type || "reward";
    node.querySelector('[data-field="points"]').value = values.points ?? (values.criterion_type === "fatal_gate" ? -10 : 2);
    node.querySelector('[data-field="criterion"]').value = values.criterion || "";
    node.querySelector('[data-field="grading_hint"]').value = values.grading_hint || "";
    node.querySelector('[data-field="machine_checkable"]').checked = Boolean(values.machine_checkable);
    node.querySelector('[data-field="reviewer_notes"]').value = values.reviewer_notes || "";
    node.querySelector(".remove-row").addEventListener("click", () => {
      node.remove();
      updateRubricIds();
      saveDraft();
      renderPreview();
    });
    rubricRowsEl.appendChild(node);
    updateRubricIds();
    if (!isPopulating) {
      saveDraft();
      renderPreview();
    }
  }

  function updateRubricIds() {
    rubricRowsEl.querySelectorAll(".rubric-card").forEach((card, index) => {
      const id = `R${index + 1}`;
      card.querySelector('[data-field="id"]').value = id;
      card.querySelector(".rubric-id-label").textContent = id;
    });
  }

  function syncRubricPointDefaults(target) {
    if (target.dataset.field !== "criterion_type") {
      return;
    }
    const card = target.closest(".rubric-card");
    const points = card.querySelector('[data-field="points"]');
    if (target.value === "fatal_gate") {
      points.value = -10;
    } else if (target.value === "penalty" && Number(points.value) >= 0) {
      points.value = -2;
    } else if (target.value === "reward" && Number(points.value) <= 0) {
      points.value = 2;
    }
  }

  function loadSyntheticExample() {
    const example = syntheticExample();
    form.reset();
    numericalChecksEl.innerHTML = "";
    rubricRowsEl.innerHTML = "";
    populateForm(example);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(example));
    saveStatusEl.textContent = "Synthetic example loaded";
    renderPreview();
  }

  function syntheticExample() {
    return {
      schema_version: "gsdbench.case.v0.1",
      case_id: "gsdb-20260430-pfs-os-alpha-split",
      short_title: "Synthetic PFS and OS alpha-split GSD",
      submission_type: "case_proposal",
      created_from: "GSDBench Intake static app",
      contributor: {
        name_or_initials: "AB",
        github_username: "synthetic-contributor",
        role: "Industry statistician",
        organization_type: "Pharma"
      },
      governance: {
        source_type: "Synthetic",
        no_phi_or_confidential_info_confirmed: true,
        permission_or_deidentification_confirmed: true,
        maintainer_revision_understood: true
      },
      benchmark_metadata: {
        project: "GSDBench",
        suggested_split: "Public/dev",
        difficulty: "Advanced",
        priority: "Known model failure mode",
        tags: [
          "event-driven design with pre-specified events",
          "gsDesign known events",
          "alpha splitting",
          "simulation verification",
          "protocol-ready reporting"
        ]
      },
      task: {
        agent_prompt: "Design a synthetic Phase 3 oncology trial with co-primary PFS and OS endpoints. Use a one-sided familywise alpha of 0.025 split as 0.015 for PFS and 0.010 for OS. The PFS design has one interim analysis at 70% information and a final analysis at 100% information using an O'Brien-Fleming style efficacy spending function. OS is tested only if PFS is significant, with one interim look at 60% information and a final look. Provide executable R code, boundary tables, event targets, and protocol-ready interpretation. Assume proportional hazards for design and include a simulation plan to verify type I error and power.",
        prior_context: "This is a clearly synthetic benchmark case for evaluating group sequential design reasoning. Do not use any proprietary trial assumptions.",
        expected_deliverables: [
          "Design summary",
          "Executable R code",
          "Boundary table",
          "Event/sample size/timing outputs",
          "Multiplicity strategy",
          "Simulation verification",
          "Protocol-ready language"
        ],
        allowed_tools: ["gsDesign", "rpact"]
      },
      trial_design: {
        disease_setting: "Synthetic late-stage oncology setting",
        phase: "Phase 3",
        endpoint_structure: "Co-primary endpoints",
        endpoint_names: "PFS, OS",
        population_hypothesis_structure: "Overall population. PFS and OS tested with fixed-sequence fallback: OS interpretation requires PFS success unless a valid multiplicity strategy is explicitly justified.",
        randomization_ratio: "1:1",
        alpha_multiplicity_strategy: "One-sided familywise alpha 0.025 split as 0.015 for PFS and 0.010 for OS with clear control of multiplicity.",
        analyses_information_fractions: "PFS: IA at 70%, FA at 100%. OS: IA at 60%, FA at 100%. Use pre-specified event counts.",
        spending_futility: "O'Brien-Fleming style efficacy spending. Non-binding futility may be described but should not inflate type I error.",
        survival_assumptions: "Synthetic exponential design assumptions. Target HR 0.72 for PFS and 0.78 for OS under H1. Median control PFS 8 months, median control OS 18 months.",
        enrollment_dropout: "Uniform enrollment over 24 months, administrative follow-up sufficient to observe final event targets, dropout 3% per year.",
        operational_constraints: "At least 3 months between database locks. Interim analyses should not occur before enrollment is operationally mature.",
        nph_assumptions: "Design under PH; discuss how delayed effect or waning effect would be evaluated in sensitivity simulations.",
        other_design_assumptions: "All assumptions are synthetic and may be adjusted by maintainers when locking the reference script."
      },
      reference_truth: {
        truth_types: ["Expected numerical outputs", "Expert textual standard", "Simulation verification"],
        reference_script_summary: "Maintainers can lock a gsDesign or rpact reference implementation from the numerical targets below.",
        reference_code_snippet: "library(gsDesign)\n# Synthetic sketch only; maintainers should lock final reference code.\n# Use k = 2 analyses with OF-like spending per endpoint.",
        numerical_checks: [
          {
            metric_name: "PFS one-sided alpha spent",
            expected_value: "0.015",
            tolerance_type: "absolute",
            tolerance_value: "0.0005",
            units: "probability",
            notes: "Total PFS alpha should match allocated alpha."
          },
          {
            metric_name: "OS one-sided alpha spent",
            expected_value: "0.010",
            tolerance_type: "absolute",
            tolerance_value: "0.0005",
            units: "probability",
            notes: "Total OS alpha should match allocated alpha."
          },
          {
            metric_name: "PFS information fractions",
            expected_value: "0.70, 1.00",
            tolerance_type: "percentage_points",
            tolerance_value: "1",
            units: "information fraction",
            notes: "Agent should not confuse analysis count with calendar looks."
          }
        ],
        textual_ground_truth: "A strong answer states the alpha split, uses a valid group sequential design package rather than manual ad hoc boundary calculations, reports efficacy boundaries on an interpretable scale, and explains how multiplicity is controlled.",
        simulation_requirements: "Verify type I error under H0.\nVerify power under H1.\nVerify IA/FA event counts and timing.\nUse independent simulation where applicable.",
        known_gotchas: [
          "Manual HR-boundary calculation when package output should be used",
          "Mis-handling non-binding futility in simulation",
          "Uncontrolled multiplicity/type I error"
        ]
      },
      rubric: [
        {
          id: "R1",
          axis: "numerical/statistical correctness",
          criterion_type: "reward",
          points: 4,
          criterion: "Correctly implements one-sided alpha allocation and group sequential efficacy spending for both endpoints.",
          grading_hint: "Award full credit only if PFS and OS alpha allocations are both respected.",
          machine_checkable: true,
          reviewer_notes: ""
        },
        {
          id: "R2",
          axis: "executable reproducibility",
          criterion_type: "reward",
          points: 3,
          criterion: "Provides executable R code using a suitable package such as gsDesign or rpact.",
          grading_hint: "Code should run after installing declared packages and should not rely on nonexistent object fields.",
          machine_checkable: false,
          reviewer_notes: ""
        },
        {
          id: "R3",
          axis: "verification/simulation",
          criterion_type: "reward",
          points: 2,
          criterion: "Includes a credible simulation verification plan for type I error, power, and analysis timing.",
          grading_hint: "Simulation can be pseudocode if the design code and checks are otherwise precise.",
          machine_checkable: false,
          reviewer_notes: ""
        },
        {
          id: "R4",
          axis: "communication/safety",
          criterion_type: "penalty",
          points: -3,
          criterion: "Penalize unclear reporting that prevents a reviewer from reconstructing event targets, boundaries, or alpha control.",
          grading_hint: "Apply when narrative and code disagree or key outputs are omitted.",
          machine_checkable: false,
          reviewer_notes: ""
        },
        {
          id: "R5",
          axis: "numerical/statistical correctness",
          criterion_type: "fatal_gate",
          points: -10,
          criterion: "Fails to control one-sided type I error or ignores multiplicity.",
          grading_hint: "Fatal if the proposed design spends the full 0.025 on both endpoints without a valid multiplicity strategy.",
          machine_checkable: false,
          reviewer_notes: ""
        }
      ],
      review: {
        suggested_reviewer_expertise: ["Survival/GSD", "Multiplicity", "Simulation", "Regulatory/statistical review"],
        why_case_matters: "This synthetic case tests whether an AI agent can combine group sequential design, alpha allocation, survival endpoint interpretation, and reproducible R output.",
        expected_model_failure_modes: "Likely failures include treating PFS and OS as independent full-alpha tests, manually computing hazard-ratio boundaries incorrectly, and providing code that does not execute.",
        maintainer_notes: "Synthetic example only; maintainers should lock final reference numerical outputs before acceptance."
      }
    };
  }

  function bullet(label, value) {
    const rendered = value ? escapeInlinePreserveBreaks(String(value)) : "_Not specified_";
    return `- **${escapeInline(label)}:** ${rendered}`;
  }

  function joinList(values) {
    return values && values.length ? values.join(", ") : "";
  }

  function listItems(values) {
    return values && values.length ? values.map((value) => `- ${escapeInline(value)}`).join("\n") : "_None specified._";
  }

  function numericalChecksTable(checks) {
    if (!checks.length) {
      return "_No numerical checks specified._";
    }
    return [
      "| Metric | Expected value | Tolerance type | Tolerance | Units | Notes |",
      "| --- | --- | --- | --- | --- | --- |",
      ...checks.map((check) => [
        check.metric_name,
        check.expected_value,
        check.tolerance_type,
        check.tolerance_value,
        check.units,
        check.notes
      ].map(tableCell).join(" | ")).map((row) => `| ${row} |`)
    ].join("\n");
  }

  function rubricTable(rows) {
    if (!rows.length) {
      return "_No rubric criteria specified._";
    }
    return [
      "| ID | Axis | Type | Points | Machine-checkable | Criterion | Grading hint |",
      "| --- | --- | --- | ---: | --- | --- | --- |",
      ...rows.map((row) => [
        row.id,
        row.axis,
        row.criterion_type,
        String(row.points),
        row.machine_checkable ? "yes" : "no",
        row.criterion,
        row.grading_hint
      ].map(tableCell).join(" | ")).map((row) => `| ${row} |`)
    ].join("\n");
  }

  function codeSnippet(label, value, language) {
    if (!value) {
      return `- **${escapeInline(label)}:** _Not specified_`;
    }
    const fence = longestFence(value);
    return `- **${escapeInline(label)}:**\n\n${fence}${language}\n${value}\n${fence}`;
  }

  function longestFence(value) {
    const runs = String(value).match(/`+/g) || [];
    const longest = runs.reduce((max, run) => Math.max(max, run.length), 0);
    return "`".repeat(Math.max(3, longest + 1));
  }

  function tableCell(value) {
    return escapeInline(value || "").replace(/\r?\n/g, "<br>");
  }

  function mdBlock(value) {
    return escapeFence(String(value || "").trim()) || "_Not specified_";
  }

  function escapeInline(value) {
    return escapeFence(String(value || "")).replace(/\|/g, "\\|").replace(/\r?\n/g, " ");
  }

  function escapeInlinePreserveBreaks(value) {
    return escapeFence(String(value || "")).replace(/\|/g, "\\|").replace(/\r?\n/g, "<br>");
  }

  function escapeFence(value) {
    return String(value || "").replace(/```/g, "\\`\\`\\`");
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  async function copyText(text, successMessage) {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
      } else {
        fallbackCopy(text);
      }
      copyStatusEl.textContent = successMessage;
    } catch (error) {
      fallbackCopy(text);
      copyStatusEl.textContent = "Copy fallback used. Press Ctrl/Cmd+C if your browser asks.";
    }
  }

  function fallbackCopy(text) {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    document.body.removeChild(textarea);
  }

  function downloadIssueMarkdown() {
    const data = collectFormData();
    const filename = `${data.case_id || "gsdb-case"}.issue.md`;
    const blob = new Blob([issueBodyEl.value], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    copyStatusEl.textContent = `Downloaded ${filename}.`;
  }
})();
