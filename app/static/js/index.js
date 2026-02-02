document.addEventListener('DOMContentLoaded', function() {
  const videoInput = document.getElementById('videoInput');
  const chooseFileBtn = document.getElementById('chooseFileBtn');
  const recordBtn = document.getElementById('recordBtn');
  const previewCanvas = document.getElementById('videoPreviewCanvas');
  const previewCtx = previewCanvas ? previewCanvas.getContext('2d') : null;
  const previewVideo = document.getElementById('videoPreview');
  const previewHint = document.getElementById('previewHint');
  const liveBox = document.getElementById('liveBox');
  const liveVideo = document.getElementById('liveVideo');
  const liveStatus = document.getElementById('liveStatus');

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
  }

  function startRecording() {
    if (!liveStream || isRecording) return;
    if (liveStatus) liveStatus.textContent = 'Recording...';
    recordedChunks = [];
    mediaRecorder = new MediaRecorder(liveStream, { mimeType: 'video/webm;codecs=vp8' });
    mediaRecorder.ondataavailable = function(event) {
      if (event.data && event.data.size > 0) {
        recordedChunks.push(event.data);
      }
    };
    mediaRecorder.onstop = function() {
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

      if (!isRecording) {
        if (isAddressPose(landmarks)) {
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
    if (liveBox) liveBox.hidden = false;
    if (liveStatus) liveStatus.textContent = 'Stand in address position to start recording.';

    await setupPose();
    processLiveFrame();
  }

  drawPlaceholder('No video selected');

  chooseFileBtn.addEventListener('click', function() {
    videoInput.click();
  });

  recordBtn.addEventListener('click', async function() {
    if (isArmed) {
      if (liveStatus) liveStatus.textContent = 'Recording cancelled.';
      stopRecording();
      stopLiveStream();
      if (liveBox) liveBox.hidden = true;
      recordBtn.textContent = 'Record Video';
      isArmed = false;
      return;
    }

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
    updatePreviewFromFile(file);
  });

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
