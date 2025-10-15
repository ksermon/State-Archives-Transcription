(() => {
  const config = window.FILEVIEW_CONFIG || {};
  const rawLineBoxes = Array.isArray(config.lineBoxes) ? config.lineBoxes : [];
  const fileId = config.fileId;
  const pageNumber = config.pageNumber;

  const pdfStage = document.getElementById('pdf-stage');
  const pdfWrapper = pdfStage ? pdfStage.parentElement : null;
  const highlightOverlay = document.getElementById('highlight-overlay');
  const zoomInButton = document.getElementById('zoom-in');
  const zoomOutButton = document.getElementById('zoom-out');
  const resetButton = document.getElementById('reset-view');
  const transcriptionEditor = document.getElementById('transcription-editor');
  const saveButton = document.getElementById('save-transcription');
  const transcriptionLinesContainer = document.getElementById('transcription-lines');

  if (!pdfStage || !pdfWrapper || typeof Panzoom !== 'function') {
    console.warn('File view initialisation aborted: missing stage or Panzoom.');
    return;
  }

  const panzoomInstance = Panzoom(pdfStage, {
    contain: 'outside',
    maxScale: 5,
    minScale: 0.5,
    cursor: 'grab',
    step: 0.2
  });

  pdfWrapper.addEventListener(
    'wheel',
    (event) => {
      event.preventDefault();
      panzoomInstance.zoomWithWheel(event);
    },
    { passive: false }
  );

  zoomInButton?.addEventListener('click', () => {
    panzoomInstance.zoomIn();
  });

  zoomOutButton?.addEventListener('click', () => {
    panzoomInstance.zoomOut();
  });

  resetButton?.addEventListener('click', () => {
    panzoomInstance.reset({ animate: true });
  });

  const lines = transcriptionEditor.value.length
    ? transcriptionEditor.value.split('\n')
    : [''];

  const lineBoxes = Array.isArray(rawLineBoxes) ? rawLineBoxes.slice(0, lines.length) : [];
  while (lineBoxes.length < lines.length) {
    lineBoxes.push(null);
  }

  const overlayRects = [];
  let activeLineEl = null;
  let activeEditor = null;
  let isDirty = false;

  function updateHiddenTranscription() {
    transcriptionEditor.value = lines.join('\n');
  }

  function setLineActions(lineEl) {
    const actions = lineEl.querySelector('.line-actions');
    actions.innerHTML = '';
    const editBtn = document.createElement('button');
    editBtn.type = 'button';
    editBtn.className = 'icon-btn line-edit-btn';
    editBtn.setAttribute('aria-label', 'Edit line');
    editBtn.innerHTML = '&#9998;';
    actions.appendChild(editBtn);
    lineEl.classList.remove('editing');
  }

  function applyLineText(lineEl, text) {
    const textEl = lineEl.querySelector('.line-text');
    const cleanText = text.replace(/\r/g, '');
    if (!cleanText.length) {
      textEl.textContent = '(blank line)';
      textEl.classList.add('is-empty');
      lineEl.classList.add('is-empty');
    } else {
      textEl.textContent = cleanText;
      textEl.classList.remove('is-empty');
      lineEl.classList.remove('is-empty');
    }
  }

  function renderLines() {
    transcriptionLinesContainer.innerHTML = '';
    lines.forEach((text, index) => {
      const lineEl = document.createElement('div');
      lineEl.className = 'transcription-line';
      lineEl.dataset.lineIndex = index;

      const numberEl = document.createElement('span');
      numberEl.className = 'line-number';
      numberEl.textContent = String(index + 1);

      const mainEl = document.createElement('div');
      mainEl.className = 'line-main';

      const textEl = document.createElement('div');
      textEl.className = 'line-text';
      mainEl.appendChild(textEl);

      const actionsEl = document.createElement('div');
      actionsEl.className = 'line-actions';
      mainEl.appendChild(actionsEl);

      lineEl.appendChild(numberEl);
      lineEl.appendChild(mainEl);

      transcriptionLinesContainer.appendChild(lineEl);
      applyLineText(lineEl, text);
      setLineActions(lineEl);
    });
  }

  function buildOverlay() {
    highlightOverlay.innerHTML = '';
    overlayRects.length = 0;
    lineBoxes.forEach((box, index) => {
      if (!box) {
        overlayRects[index] = null;
        return;
      }
      const rect = document.createElement('div');
      rect.className = 'line-region';
      rect.dataset.lineIndex = index;
      rect.style.left = `${box.x * 100}%`;
      rect.style.top = `${box.y * 100}%`;
      rect.style.width = `${box.width * 100}%`;
      rect.style.height = `${box.height * 100}%`;
      highlightOverlay.appendChild(rect);
      overlayRects[index] = rect;
    });
  }

  function clearOverlayHighlights() {
    overlayRects.forEach((rect) => rect && rect.classList.remove('active'));
  }

  function focusLine(index) {
    const nextLine = transcriptionLinesContainer.querySelector(
      `[data-line-index="${index}"]`
    );
    if (!nextLine) {
      activeLineEl = null;
      return;
    }
    nextLine.classList.add('active');
    const overlay = overlayRects[index];
    if (overlay) {
      overlay.classList.add('active');
    }
    nextLine.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    activeLineEl = nextLine;
  }

  function highlightLine(index) {
    if (index === null || Number.isNaN(index)) {
      return;
    }
    if (activeEditor && activeEditor.index !== index) {
      closeEditor(activeEditor, { commit: true });
    }
    if (activeLineEl) {
      activeLineEl.classList.remove('active');
    }
    clearOverlayHighlights();
    focusLine(index);
  }

  function markDirty() {
    if (isDirty) {
      return;
    }
    isDirty = true;
    saveButton.disabled = false;
    saveButton.textContent = 'Save changes';
    saveButton.classList.add('has-changes');
  }

  function resetDirtyState() {
    isDirty = false;
    saveButton.disabled = true;
    saveButton.textContent = 'Save changes';
    saveButton.classList.remove('has-changes');
  }

  function closeEditor(editor, { commit }) {
    if (!editor) {
      return;
    }
    const { lineEl, index, textarea, original } = editor;
    const nextValue = commit ? textarea.value : original;
    const changed = commit && nextValue !== original;
    lines[index] = nextValue;
    applyLineText(lineEl, nextValue);
    setLineActions(lineEl);
    lineEl.classList.remove('editing');
    delete lineEl.dataset.editing;
    activeEditor = null;
    updateHiddenTranscription();
    if (changed) {
      markDirty();
    }
  }

  function openEditor(lineEl, index) {
    if (lineEl.dataset.editing === 'true') {
      return;
    }
    if (activeEditor) {
      closeEditor(activeEditor, { commit: true });
    }
    const textEl = lineEl.querySelector('.line-text');
    const originalText = lines[index] ?? '';
    const textarea = document.createElement('textarea');
    textarea.className = 'line-editor';
    textarea.value = originalText;
    textEl.classList.remove('is-empty');
    textEl.innerHTML = '';
    textEl.appendChild(textarea);

    const actions = lineEl.querySelector('.line-actions');
    actions.innerHTML = '';
    const saveBtn = document.createElement('button');
    saveBtn.type = 'button';
    saveBtn.className = 'icon-btn line-commit-btn';
    saveBtn.setAttribute('aria-label', 'Save line');
    saveBtn.innerHTML = '&#10003;';
    const cancelBtn = document.createElement('button');
    cancelBtn.type = 'button';
    cancelBtn.className = 'icon-btn line-cancel-btn';
    cancelBtn.setAttribute('aria-label', 'Undo edit');
    cancelBtn.innerHTML = '&#10005;';
    actions.appendChild(saveBtn);
    actions.appendChild(cancelBtn);

    lineEl.dataset.editing = 'true';
    lineEl.classList.add('editing');
    activeEditor = { lineEl, index, textarea, original: originalText };

    requestAnimationFrame(() => {
      textarea.focus();
      textarea.select();
    });

    textarea.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        closeEditor(activeEditor, { commit: true });
      }
    });

    textarea.addEventListener('blur', () => {
      setTimeout(() => {
        if (activeEditor && activeEditor.textarea === textarea) {
          closeEditor(activeEditor, { commit: true });
        }
      }, 10);
    });
  }

  function clearActiveLine() {
    if (activeLineEl) {
      activeLineEl.classList.remove('active');
    }
    clearOverlayHighlights();
    activeLineEl = null;
  }

  transcriptionLinesContainer.addEventListener('click', (event) => {
    const commitBtn = event.target.closest('.line-commit-btn');
    if (commitBtn && activeEditor) {
      event.stopPropagation();
      event.preventDefault();
      closeEditor(activeEditor, { commit: true });
      return;
    }

    const cancelBtn = event.target.closest('.line-cancel-btn');
    if (cancelBtn && activeEditor) {
      event.stopPropagation();
      event.preventDefault();
      closeEditor(activeEditor, { commit: false });
      return;
    }

    const lineEl = event.target.closest('.transcription-line');
    if (!lineEl) {
      if (activeEditor) {
        closeEditor(activeEditor, { commit: true });
      }
      clearActiveLine();
      return;
    }

    const index = parseInt(lineEl.dataset.lineIndex, 10);
    highlightLine(index);

    if (event.target.closest('.line-edit-btn')) {
      event.preventDefault();
      openEditor(lineEl, index);
    }
  });

  transcriptionLinesContainer.addEventListener('dblclick', (event) => {
    const lineEl = event.target.closest('.transcription-line');
    if (!lineEl) {
      return;
    }
    const index = parseInt(lineEl.dataset.lineIndex, 10);
    highlightLine(index);
    openEditor(lineEl, index);
  });

  transcriptionLinesContainer.addEventListener('mouseover', (event) => {
    const lineEl = event.target.closest('.transcription-line');
    if (!lineEl) {
      overlayRects.forEach((rect) => rect && rect.classList.remove('hover'));
      return;
    }
    const index = parseInt(lineEl.dataset.lineIndex, 10);
    overlayRects.forEach((rect, rectIndex) => {
      if (!rect) {
        return;
      }
      if (rectIndex === index) {
        rect.classList.add('hover');
      } else {
        rect.classList.remove('hover');
      }
    });
  });

  transcriptionLinesContainer.addEventListener('mouseleave', () => {
    overlayRects.forEach((rect) => rect && rect.classList.remove('hover'));
  });

  document.addEventListener('click', (event) => {
    if (!activeEditor) {
      return;
    }
    if (event.target.closest('.transcription-line')) {
      return;
    }
    closeEditor(activeEditor, { commit: true });
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && activeEditor) {
      event.preventDefault();
      closeEditor(activeEditor, { commit: false });
    }
  });

  saveButton.addEventListener('click', async () => {
    if (activeEditor) {
      closeEditor(activeEditor, { commit: true });
    }
    if (!isDirty) {
      return;
    }
    saveButton.disabled = true;
    saveButton.textContent = 'Saving...';
    saveButton.classList.remove('has-changes');
    try {
      const response = await fetch(`/api/files/${fileId}/pages/${pageNumber}/transcription`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ transcription: lines.join('\n') })
      });
      if (!response.ok) {
        throw new Error('Failed to save transcription');
      }
      saveButton.textContent = 'Saved';
      setTimeout(() => {
        if (!isDirty) {
          saveButton.textContent = 'Save changes';
        }
      }, 2000);
      resetDirtyState();
    } catch (error) {
      console.error(error);
      saveButton.disabled = false;
      saveButton.textContent = 'Retry save';
      saveButton.classList.add('has-changes');
    }
  });

  renderLines();
  buildOverlay();
  updateHiddenTranscription();
  resetDirtyState();
})();
