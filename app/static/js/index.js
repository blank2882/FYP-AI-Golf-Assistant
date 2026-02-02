document.addEventListener('DOMContentLoaded', function() {
  const videoInput = document.getElementById('videoInput');
  const chooseFileBtn = document.getElementById('chooseFileBtn');
  const recordBtn = document.getElementById('recordBtn');
  const previewCanvas = document.getElementById('videoPreviewCanvas');
  const previewCtx = previewCanvas ? previewCanvas.getContext('2d') : null;
  const previewVideo = document.getElementById('videoPreview');
  const previewHint = document.getElementById('previewHint');
  let animationFrameId = null;

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

  drawPlaceholder('No video selected');

  chooseFileBtn.addEventListener('click', function() {
    videoInput.click();
  });

  recordBtn.addEventListener('click', function() {
    alert('Video recording feature coming soon! Please use "Choose File" to upload a video for now.');
  });

  videoInput.addEventListener('change', function() {
    const file = videoInput.files && videoInput.files[0];
    if (!file || !previewVideo) {
      if (previewHint) previewHint.textContent = 'No video selected.';
      drawPlaceholder('No video selected');
      return;
    }

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
