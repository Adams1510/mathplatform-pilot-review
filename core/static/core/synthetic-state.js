"use strict";

(() => {
  const form = document.getElementById("synthetic-state-form");
  if (!form || !window.indexedDB) return;

  const status = document.getElementById("save-status");
  const retry = document.getElementById("retry-save");
  const conflict = document.getElementById("conflict-panel");
  const operation = form.elements.operation_id;
  const baseRevision = form.elements.base_revision;
  const contentVersion = form.elements.content_version;
  const draftKey = form.dataset.draftKey;
  const allowedValues = new Set(["alpha", "beta", "gamma"]);
  const databaseRequest = indexedDB.open("math-platform-synthetic-pending-v1", 1);
  const databasePromise = new Promise((resolve, reject) => {
    databaseRequest.onupgradeneeded = () => {
      if (!databaseRequest.result.objectStoreNames.contains("drafts")) {
        databaseRequest.result.createObjectStore("drafts", { keyPath: "key" });
      }
    };
    databaseRequest.onsuccess = () => resolve(databaseRequest.result);
    databaseRequest.onerror = () => reject(databaseRequest.error);
  });

  function useStore(mode, action) {
    return databasePromise.then((database) => new Promise((resolve, reject) => {
      const transaction = database.transaction("drafts", mode);
      const request = action(transaction.objectStore("drafts"));
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    }));
  }

  const readDraft = () => useStore("readonly", (store) => store.get(draftKey));
  const writeDraft = (draft) => useStore("readwrite", (store) => store.put(draft));
  const clearDraft = () => useStore("readwrite", (store) => store.delete(draftKey));
  const selectedValue = () => new FormData(form).get("value");
  const selectValue = (value) => {
    if (!allowedValues.has(value)) return;
    const control = Array.from(form.elements.value).find((item) => item.value === value);
    if (control) control.checked = true;
  };

  function newDraft(value) {
    return {
      key: draftKey,
      value,
      operationId: crypto.randomUUID(),
      baseRevision: Number(baseRevision.value),
      contentVersion: contentVersion.value,
    };
  }

  async function saveDraft(draft) {
    operation.value = draft.operationId;
    baseRevision.value = draft.baseRevision;
    status.textContent = "Saving. A pending copy remains on this device.";
    retry.hidden = true;
    try {
      const response = await fetch(form.action, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Accept": "application/json",
          "Content-Type": "application/json",
          "X-CSRFToken": form.elements.csrfmiddlewaretoken.value,
        },
        body: JSON.stringify({
          value: draft.value,
          operation_id: draft.operationId,
          base_revision: draft.baseRevision,
          content_version: draft.contentVersion,
        }),
      });
      const result = await response.json();
      if (response.ok) {
        baseRevision.value = result.revision;
        const currentDraft = await readDraft();
        if (currentDraft && currentDraft.operationId !== draft.operationId) {
          currentDraft.baseRevision = result.revision;
          await writeDraft(currentDraft);
          await saveDraft(currentDraft);
          return;
        }
        await clearDraft();
        conflict.hidden = true;
        status.textContent = `Saved online at revision ${result.revision}.`;
        return;
      }
      if (response.status === 409 && result.status === "revision_conflict") {
        conflict.dataset.currentRevision = result.current_revision;
        conflict.dataset.currentValue = result.current_value;
        conflict.hidden = false;
        status.textContent = "Save conflict. Your pending device copy has been kept.";
        return;
      }
      status.textContent = "Save failed. Your pending device copy has been kept.";
      retry.hidden = false;
    } catch (_error) {
      status.textContent = "Connection failed. Stored on this device — not saved online.";
      retry.hidden = false;
    }
  }

  async function queueAndSave(value) {
    if (!allowedValues.has(value)) return;
    const draft = newDraft(value);
    await writeDraft(draft);
    status.textContent = "Stored on this device — not saved online.";
    await saveDraft(draft);
  }

  form.addEventListener("change", (event) => {
    if (event.target.name === "value") queueAndSave(event.target.value);
  });
  form.addEventListener("submit", async (event) => {
    const value = selectedValue();
    if (!value) return;
    event.preventDefault();
    const pendingDraft = await readDraft();
    if (pendingDraft) {
      saveDraft(pendingDraft);
    } else {
      queueAndSave(value);
    }
  });
  retry.addEventListener("click", async () => {
    const draft = await readDraft();
    if (draft) saveDraft(draft);
  });
  document.getElementById("use-server-response").addEventListener("click", async () => {
    selectValue(conflict.dataset.currentValue);
    baseRevision.value = conflict.dataset.currentRevision;
    await clearDraft();
    conflict.hidden = true;
    status.textContent = "Using the response already saved online.";
  });
  document.getElementById("save-device-response").addEventListener("click", async () => {
    const draft = await readDraft();
    if (!draft) return;
    draft.baseRevision = Number(conflict.dataset.currentRevision);
    draft.operationId = crypto.randomUUID();
    await writeDraft(draft);
    conflict.hidden = true;
    saveDraft(draft);
  });
  document.getElementById("clear-local-draft").addEventListener("click", async () => {
    await clearDraft();
    retry.hidden = true;
    conflict.hidden = true;
    status.textContent = "Pending device copy cleared. Confirmed server state is unchanged.";
  });

  readDraft().then((draft) => {
    if (
      !draft
      || draft.contentVersion !== contentVersion.value
      || !allowedValues.has(draft.value)
    ) return;
    selectValue(draft.value);
    operation.value = draft.operationId;
    baseRevision.value = draft.baseRevision;
    status.textContent = "Recovered from this device — not saved online.";
    retry.hidden = false;
  });
})();
