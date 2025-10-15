(() => {
  const config = window.FILEVIEW_CONFIG;
  if (!config) {
    return;
  }

  const rawLineBoxes = Array.isArray(config.lineBoxes) ? config.lineBoxes : [];
  const fileId = config.fileId;
  const pageNumber = config.pageNumber;
  const pdfUrl = config.pdfUrl;
  const workerSrc = config.pdfWorkerSrc;

  const pdfStageWrapper = document.querySelector('.pdf-stage-wrapper');
  const pdfStage = document.getElementById('pdf-stage');
  const pdfCanvas = document.getElementById('pdf-canvas');
  const highlightOverlay = document.getElementById('highlight-overlay');

  const zoomInButton = document.getElementById('zoom-in');
  const zoomOutButton = document.getElementById('zoom-out');
  const resetButton = document.getElementById('reset-view');

  const transcriptionEditor = document.getElementById('transcription-editor');
  const saveButton = document.getElementById('save-transcription');
  const transcriptionLinesContainer = document.getElementById('transcription-lines');

  const pdfjsLib = window['pdfjs-dist/build/pdf'] || window.pdfjsLib;
  if (!pdfjsLib || !pdfStageWrapper || !pdfStage || !pdfCanvas || !highlightOverlay) {
    console.warn('File view initialisation aborted: missing required elements.');
    return;
  }

  if (workerSrc) {
    pdfjsLib.GlobalWorkerOptions.workerSrc = workerSrc;
  }

  const overlayRects = [];
  const lines = transcriptionEditor.value.length
    ? transcriptionEditor.value.split('\n')
    : [''];
  const lineBoxes = Array.isArray(rawLineBoxes)
    ? rawLineBoxes.slice(0, lines.length)
    : [];
  while (lineBoxes.length < lines.length) {
    lineBoxes.push(null);
  }

  let activeLineIndex = null;
  let activeLineEl = null;
  let activeEditor = null;
  let isDirty = false;

  const pdfState = {
    pdfDoc: null,
    page: null,
    baseViewport: null,
    baseScale: 1,
    currentScale: 1,
    minScale: 0.5,
    maxScale: 4,
    zoomFactor: 1.2,
    rendering: false,
  };

  function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

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

  function focusLine(index) {
    const nextLine = transcriptionLinesContainer.querySelector(
      `[data-line-index="${index}"]`
    );
    if (!nextLine) {
      activeLineEl = null;
      activeLineIndex = null;
      return;
    }
    nextLine.classList.add('active');
    const overlay = overlayRects[index];
    if (overlay) {
      overlay.classList.add('active');
    }
    nextLine.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    activeLineEl = nextLine;
    activeLineIndex = index;
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
    overlayRects.forEach((rect) => {
      if (rect) {
        rect.classList.remove('active');
      }
    });
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
    overlayRects.forEach((rect) => rect && rect.classList.remove('active'));
    activeLineEl = null;
    activeLineIndex = null;
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
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ transcription: lines.join('\n') }),
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

  function updateZoomControlState() {
    const minScale = pdfState.baseScale * pdfState.minScale;
    const maxScale = pdfState.baseScale * pdfState.maxScale;
    const epsilon = 0.001;
    if (zoomOutButton) {
      zoomOutButton.disabled = pdfState.currentScale <= minScale + epsilon;
    }
    if (zoomInButton) {
      zoomInButton.disabled = pdfState.currentScale >= maxScale - epsilon;
    }
    if (resetButton) {
      resetButton.disabled = Math.abs(pdfState.currentScale - pdfState.baseScale) < epsilon;
    }
  }

  async function renderPdf() {
    if (!pdfState.page || pdfState.rendering) {
      return;
    }
    pdfState.rendering = true;

    const viewport = pdfState.page.getViewport({ scale: pdfState.currentScale });
    const previousWidth = pdfStage.offsetWidth || 1;
    const previousHeight = pdfStage.offsetHeight || 1;
    const centerXRatio =
      (pdfStageWrapper.scrollLeft + pdfStageWrapper.clientWidth / 2) / previousWidth;
    const centerYRatio =
      (pdfStageWrapper.scrollTop + pdfStageWrapper.clientHeight / 2) / previousHeight;

    const context = pdfCanvas.getContext('2d', { alpha: false });
    pdfCanvas.width = viewport.width;
    pdfCanvas.height = viewport.height;
    pdfStage.style.width = `${viewport.width}px`;
    pdfStage.style.height = `${viewport.height}px`;
    pdfCanvas.style.width = '100%';
    pdfCanvas.style.height = '100%';
    highlightOverlay.style.width = '100%';
    highlightOverlay.style.height = '100%';
    pdfStage.classList.add('is-loaded');

    try {
      await pdfState.page.render({ canvasContext: context, viewport }).promise;
    } finally {
      pdfState.rendering = false;
    }

    const newWidth = viewport.width;
    const newHeight = viewport.height;
    if (Number.isFinite(centerXRatio)) {
      pdfStageWrapper.scrollLeft = newWidth * centerXRatio - pdfStageWrapper.clientWidth / 2;
    }
    if (Number.isFinite(centerYRatio)) {
      pdfStageWrapper.scrollTop = newHeight * centerYRatio - pdfStageWrapper.clientHeight / 2;
    }

    updateZoomControlState();
  }

  function computeFitScale() {
    if (!pdfState.baseViewport) {
      return 1;
    }
    const containerWidth = pdfStageWrapper.clientWidth || pdfState.baseViewport.width;
    return containerWidth / pdfState.baseViewport.width;
  }

  async function setScale(nextScale) {
    const minScale = pdfState.baseScale * pdfState.minScale;
    const maxScale = pdfState.baseScale * pdfState.maxScale;
    pdfState.currentScale = clamp(nextScale, minScale, maxScale);
    await renderPdf();
  }

  async function loadPdf() {
    try {
      const task = pdfjsLib.getDocument(pdfUrl);
      pdfState.pdfDoc = await task.promise;
      pdfState.page = await pdfState.pdfDoc.getPage(pageNumber);
      pdfState.baseViewport = pdfState.page.getViewport({ scale: 1 });
      pdfState.baseScale = computeFitScale();
      pdfState.minScale = 0.5;
      pdfState.maxScale = 4;
      pdfState.currentScale = pdfState.baseScale;
      await renderPdf();
    } catch (error) {
      console.error('Unable to load PDF document', error);
    }
  }

  function debounce(fn, delay) {
    let handle;
    return (...args) => {
      clearTimeout(handle);
      handle = setTimeout(() => fn(...args), delay);
    };
  }

  const handleResize = debounce(async () => {
    if (!pdfState.page) {
      return;
    }
    const zoomRatio = pdfState.currentScale / pdfState.baseScale;
    pdfState.baseScale = computeFitScale();
    const nextScale = pdfState.baseScale * zoomRatio;
    await setScale(nextScale);
  }, 150);

  if (zoomInButton) {
    zoomInButton.addEventListener('click', () => {
      setScale(pdfState.currentScale * pdfState.zoomFactor);
    });
  }

  if (zoomOutButton) {
    zoomOutButton.addEventListener('click', () => {
      setScale(pdfState.currentScale / pdfState.zoomFactor);
    });
  }

  if (resetButton) {
    resetButton.addEventListener('click', () => {
      setScale(pdfState.baseScale);
    });
  }

  pdfStageWrapper.addEventListener(
    'wheel',
    (event) => {
      if (!event.ctrlKey) {
        return;
      }
      event.preventDefault();
      const factor = event.deltaY < 0 ? pdfState.zoomFactor : 1 / pdfState.zoomFactor;
      setScale(pdfState.currentScale * factor);
    },
    { passive: false }
  );

  window.addEventListener('resize', handleResize);

  renderLines();
  buildOverlay();
  updateHiddenTranscription();
  updateZoomControlState();
  loadPdf();
})();
