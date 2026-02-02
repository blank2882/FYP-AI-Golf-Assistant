document.addEventListener('DOMContentLoaded', function() {
  const videoInput = document.getElementById('videoInput');
  const chooseFileBtn = document.getElementById('chooseFileBtn');
  const recordBtn = document.getElementById('recordBtn');

  chooseFileBtn.addEventListener('click', function() {
    videoInput.click();
  });

  recordBtn.addEventListener('click', function() {
    alert('Video recording feature coming soon! Please use "Choose File" to upload a video for now.');
  });
});
