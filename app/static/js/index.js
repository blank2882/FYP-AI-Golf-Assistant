document.addEventListener('DOMContentLoaded', function() {
  const videoInput = document.getElementById('videoInput');
  const chooseFileBtn = document.getElementById('chooseFileBtn');
  const recordBtn = document.getElementById('recordBtn');
  const analyzeBtn = document.getElementById('analyzeBtn');
  const uploadForm = document.getElementById('uploadForm');
  const previewCanvas = document.getElementById('videoPreviewCanvas');
  const previewCtx = previewCanvas ? previewCanvas.getContext('2d') : null;
  const previewVideo = document.getElementById('videoPreview');
  const previewHint = document.getElementById('previewHint');
  const liveBox = document.getElementById('liveBox');
  const liveVideo = document.getElementById('liveVideo');
  const liveStatus = document.getElementById('liveStatus');
  const liveOverlay = document.getElementById('liveOverlay');
  const overlayCtx = liveOverlay ? liveOverlay.getContext('2d') : null;
  const fullBodyStatus = document.getElementById('fullBodyStatus');
  const swingDuration = document.getElementById('swingDuration');
  const recordedActions = document.getElementById('recordedActions');
  const useSwingBtn = document.getElementById('useSwingBtn');
  const retakeBtn = document.getElementById('retakeBtn');
  const loadingOverlay = document.getElementById('loadingOverlay');

  let animationFrameId = null;
  let liveStream = null;
  let mediaRecorder = null;
  let recordedChunks = [];
  let isArmed = false;
  let isRecording = false;
  let addressCount = 0;
  let finishCount = 0;
  let stopTimeoutId = null;
  let pose = null;
  let processingFrame = false;
  let fullBodyDetected = false;
  let recordStartTime = null;

  function drawPlaceholder(text) {
    if (!previewCtx || !previewCanvas) return;
    const w = previewCanvas.width;
    const h = previewCanvas.height;
    previewCtx.fillStyle = '#f5f5f5';
    previewCtx.fillRect(0, 0, w, h);
    previewCtx.fillStyle = '#777';
    previewCtx.font = '16px Segoe UI, sans-serif';
    previewCtx.textAlign = 'center';
    previewCtx.textBaseline = 'middle';
    previewCtx.fillText(text, w / 2, h / 2);
  }

  function setSwingDurationText(value) {
    if (!swingDuration) return;
    swingDuration.textContent = value ? `Swing duration: ${value}` : 'Swing duration: --';
  }

  function resizeOverlay() {
    if (!liveOverlay || !liveVideo) return;
    const width = liveVideo.videoWidth || 640;
    const height = liveVideo.videoHeight || 360;
    liveOverlay.width = width;
    liveOverlay.height = height;
  }

  function clearOverlay() {
    if (!overlayCtx || !liveOverlay) return;
    overlayCtx.clearRect(0, 0, liveOverlay.width, liveOverlay.height);
  }

  function isLandmarkVisible(lm, margin) {
    if (!lm) return false;
    if (typeof lm.visibility === 'number' && lm.visibility < 0.5) return false;
    return lm.x > margin && lm.x < 1 - margin && lm.y > margin && lm.y < 1 - margin;
  }

  function updateFullBodyStatus(landmarks) {
    if (!fullBodyStatus) return false;
    if (!landmarks) {
      fullBodyStatus.textContent = 'Full body: --';
      fullBodyStatus.classList.remove('ok');
      return false;
    }
    const margin = 0.04;
    const required = [11, 12, 23, 24, 27, 28];
    const ok = required.every((idx) => isLandmarkVisible(landmarks[idx], margin));
    fullBodyStatus.textContent = ok ? 'Full body detected' : 'Full body: adjust camera';
    fullBodyStatus.classList.toggle('ok', ok);
    return ok;
  }

  const POSE_CONNECTIONS = [
    [11, 12], [11, 23], [12, 24], [23, 24],
    [11, 13], [13, 15], [12, 14], [14, 16],
    [23, 25], [25, 27], [24, 26], [26, 28]
  ];

  function drawPose(landmarks) {
    if (!overlayCtx || !liveOverlay || !landmarks) return;
    const w = liveOverlay.width;
    const h = liveOverlay.height;
    overlayCtx.clearRect(0, 0, w, h);
    overlayCtx.lineWidth = 2;
    overlayCtx.strokeStyle = 'rgba(0, 255, 140, 0.9)';
    overlayCtx.fillStyle = 'rgba(0, 255, 140, 0.9)';

    POSE_CONNECTIONS.forEach(([a, b]) => {
      const la = landmarks[a];
      const lb = landmarks[b];
      if (!la || !lb) return;
      overlayCtx.beginPath();
      overlayCtx.moveTo(la.x * w, la.y * h);
      overlayCtx.lineTo(lb.x * w, lb.y * h);
      overlayCtx.stroke();
    });

    landmarks.forEach((lm) => {
      if (!lm) return;
      overlayCtx.beginPath();
      overlayCtx.arc(lm.x * w, lm.y * h, 3, 0, Math.PI * 2);
      overlayCtx.fill();
    });
  }

  function drawFrame() {
    if (!previewCtx || !previewCanvas || !previewVideo) return;
    if (previewVideo.readyState >= 2) {
      previewCtx.drawImage(previewVideo, 0, 0, previewCanvas.width, previewCanvas.height);
    }
    if (!previewVideo.paused && !previewVideo.ended) {
      animationFrameId = requestAnimationFrame(drawFrame);
    }
  }

  function stopAnimation() {
    if (animationFrameId) {
      cancelAnimationFrame(animationFrameId);
      animationFrameId = null;
    }
  }

  function updatePreviewFromFile(file) {
    if (!file || !previewVideo) return;
    const url = URL.createObjectURL(file);
    previewVideo.src = url;
    previewVideo.load();

    previewVideo.onloadeddata = function() {
      stopAnimation();
      if (previewCanvas) {
        previewCanvas.width = previewVideo.videoWidth || 640;
        previewCanvas.height = previewVideo.videoHeight || 360;
      }
      drawFrame();
      if (previewHint) previewHint.textContent = 'Click the preview to play/pause.';
    };

    previewVideo.onplay = function() {
      stopAnimation();
      drawFrame();
    };

    previewVideo.onpause = function() {
      stopAnimation();
      drawFrame();
    };

    previewVideo.onended = function() {
      stopAnimation();
      drawFrame();
    };
  }

  function resetDetectionCounters() {
    addressCount = 0;
    finishCount = 0;
  }

  function stopLiveStream() {
    if (liveStream) {
      liveStream.getTracks().forEach((t) => t.stop());
      liveStream = null;
    }
    if (liveVideo) {
      liveVideo.srcObject = null;
    }
    clearOverlay();
  }

  function stopRecording() {
    if (stopTimeoutId) {
      clearTimeout(stopTimeoutId);
      stopTimeoutId = null;
    }
    if (mediaRecorder && isRecording) {
      mediaRecorder.stop();
    }
    isRecording = false;
  }

  function finalizeRecording() {
    const blob = new Blob(recordedChunks, { type: mediaRecorder?.mimeType || 'video/webm' });
    recordedChunks = [];
    const file = new File([blob], `recorded_${Date.now()}.webm`, { type: blob.type });
    const dt = new DataTransfer();
    dt.items.add(file);
    videoInput.files = dt.files;
    videoInput.dispatchEvent(new Event('change'));
    updatePreviewFromFile(file);
    if (previewHint) previewHint.textContent = 'Recorded video ready. Click the preview to play/pause.';
    if (recordedActions) recordedActions.hidden = false;
    if (analyzeBtn) analyzeBtn.hidden = true;
  }

  function startRecording() {
    if (!liveStream || isRecording) return;
    if (liveStatus) liveStatus.textContent = 'Recording...';
    recordedChunks = [];
    recordStartTime = performance.now();
    setSwingDurationText('--');
    mediaRecorder = new MediaRecorder(liveStream, { mimeType: 'video/webm;codecs=vp8' });
    mediaRecorder.ondataavailable = function(event) {
      if (event.data && event.data.size > 0) {
        recordedChunks.push(event.data);
      }
    };
    mediaRecorder.onstop = function() {
      if (recordStartTime) {
        const elapsed = (performance.now() - recordStartTime) / 1000;
        setSwingDurationText(`${elapsed.toFixed(1)}s`);
      }
      finalizeRecording();
      if (liveStatus) liveStatus.textContent = 'Recording stopped. Preview updated.';
      recordBtn.textContent = 'Record Video';
      isArmed = false;
      stopLiveStream();
      if (liveBox) liveBox.hidden = true;
    };
    mediaRecorder.start();
    isRecording = true;
  }

  function scheduleStopAfterFinish() {
    if (stopTimeoutId) return;
    if (liveStatus) liveStatus.textContent = 'Finish detected. Stopping in 1 second...';
    stopTimeoutId = setTimeout(() => {
      stopRecording();
    }, 1000);
  }

  function getDistance(a, b) {
    const dx = (a.x - b.x);
    const dy = (a.y - b.y);
    return Math.hypot(dx, dy);
  }

  function isAddressPose(landmarks) {
    const ls = landmarks[11];
    const rs = landmarks[12];
    const lw = landmarks[15];
    const rw = landmarks[16];
    const lh = landmarks[23];
    const rh = landmarks[24];
    if (!ls || !rs || !lw || !rw || !lh || !rh) return false;

    const shoulderWidth = getDistance(ls, rs) || 1e-6;
    const wristHipDist = (getDistance(lw, lh) + getDistance(rw, rh)) / 2;
    const wristsBelowShoulders = lw.y > ls.y && rw.y > rs.y;
    const handsNearHips = wristHipDist < shoulderWidth * 0.45;
    return wristsBelowShoulders && handsNearHips;
  }

  function isFinishPose(landmarks) {
    const ls = landmarks[11];
    const rs = landmarks[12];
    const lw = landmarks[15];
    const rw = landmarks[16];
    const nose = landmarks[0];
    if (!ls || !rs || !lw || !rw) return false;

    const wristsAboveShoulders = lw.y < ls.y - 0.05 && rw.y < rs.y - 0.05;
    const wristsAboveHead = nose ? (lw.y < nose.y && rw.y < nose.y) : true;
    return wristsAboveShoulders && wristsAboveHead;
  }

  async function setupPose() {
    if (pose) return pose;
    if (!window.Pose) {
      throw new Error('MediaPipe Pose failed to load.');
    }
    pose = new window.Pose({
      locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`
    });
    pose.setOptions({
      modelComplexity: 1,
      smoothLandmarks: true,
      minDetectionConfidence: 0.5,
      minTrackingConfidence: 0.5
    });
    pose.onResults((results) => {
      const landmarks = results.poseLandmarks;
      if (!isArmed || !landmarks) return;
      fullBodyDetected = updateFullBodyStatus(landmarks);
      drawPose(landmarks);

      if (!isRecording) {
        if (fullBodyDetected && isAddressPose(landmarks)) {
          addressCount += 1;
        } else {
          addressCount = 0;
        }
        if (addressCount >= 8) {
          startRecording();
          resetDetectionCounters();
        }
      } else {
        if (isFinishPose(landmarks)) {
          finishCount += 1;
        } else {
          finishCount = 0;
        }
        if (finishCount >= 8) {
          scheduleStopAfterFinish();
        }
      }
    });
    return pose;
  }

  async function processLiveFrame() {
    if (!isArmed || !pose || !liveVideo) return;
    if (liveVideo.readyState < 2) {
      requestAnimationFrame(processLiveFrame);
      return;
    }
    if (processingFrame) {
      requestAnimationFrame(processLiveFrame);
      return;
    }
    processingFrame = true;
    try {
      await pose.send({ image: liveVideo });
    } catch (err) {
      console.error(err);
    }
    processingFrame = false;
    requestAnimationFrame(processLiveFrame);
  }

  async function startLivePreview() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      alert('Camera access is not supported in this browser.');
      return;
    }
    if (!liveVideo) return;

    // Clear uploaded video preview when starting live recording
    if (previewVideo) previewVideo.src = '';
    drawPlaceholder('Recording in progress...');
    if (previewHint) previewHint.textContent = '';

    liveStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    liveVideo.srcObject = liveStream;
    await liveVideo.play();
    resizeOverlay();
    liveVideo.onloadedmetadata = resizeOverlay;
    if (liveBox) liveBox.hidden = false;
    if (liveStatus) liveStatus.textContent = 'Stand in address position to start recording.';
    setSwingDurationText('--');
    if (fullBodyStatus) {
      fullBodyStatus.textContent = 'Full body: --';
      fullBodyStatus.classList.remove('ok');
    }
    if (recordedActions) recordedActions.hidden = true;
    if (analyzeBtn) analyzeBtn.hidden = false;

    await setupPose();
    processLiveFrame();
  }

  drawPlaceholder('No video selected');

  chooseFileBtn.addEventListener('click', function() {
    videoInput.click();
  });

  videoInput.addEventListener('change', function() {
    const file = videoInput.files && videoInput.files[0];
    if (!file || !previewVideo) {
      if (previewHint) previewHint.textContent = 'No video selected.';
      drawPlaceholder('No video selected');
      return;
    }
    // Hide live video when uploading a file
    if (liveBox) liveBox.hidden = true;
    stopLiveStream();
    isArmed = false;
    if (recordBtn) recordBtn.textContent = 'Record Video';
    if (recordedActions) recordedActions.hidden = true;
    if (analyzeBtn) analyzeBtn.hidden = false;
    updatePreviewFromFile(file);
  });

  if (useSwingBtn && uploadForm) {
    useSwingBtn.addEventListener('click', function() {
      if (!videoInput.files || videoInput.files.length === 0) return;
      if (loadingOverlay) loadingOverlay.hidden = false;
      uploadForm.submit();
    });
  }

  if (retakeBtn) {
    retakeBtn.addEventListener('click', async function() {
      stopLiveStream();
      if (recordedActions) recordedActions.hidden = true;
      if (previewHint) previewHint.textContent = 'No video selected.';
      if (previewVideo) previewVideo.src = '';
      drawPlaceholder('No video selected');
      videoInput.value = '';
      try {
        isArmed = true;
        recordBtn.textContent = 'Recording Armed';
        resetDetectionCounters();
        await startLivePreview();
      } catch (err) {
        console.error(err);
        alert('Unable to start live video. Please check camera permissions.');
        isArmed = false;
        recordBtn.textContent = 'Record Video';
      }
    });
  }

  if (uploadForm) {
    uploadForm.addEventListener('submit', function() {
      if (loadingOverlay) loadingOverlay.hidden = false;
    });
  }

  if (previewCanvas && previewVideo) {
    previewCanvas.addEventListener('click', function() {
      if (!previewVideo.src) return;
      if (previewVideo.paused) {
        previewVideo.play();
      } else {
        previewVideo.pause();
      }
    });
  }
});
