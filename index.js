// Handle file upload and navigation to analysis page
document.addEventListener('DOMContentLoaded', function() {
  const videoInput = document.getElementById('videoInput');
  const chooseFileBtn = document.getElementById('chooseFileBtn');
  const recordBtn = document.getElementById('recordBtn');
  
  // Choose file button - opens file picker
  chooseFileBtn.addEventListener('click', function() {
    videoInput.click();
  });
  
  // Handle file selection
  videoInput.addEventListener('change', function(event) {
    const file = event.target.files[0];
    
    if (file && file.type.startsWith('video/')) {
      // Create a URL for the video file
      const reader = new FileReader();
      
      reader.onload = function(e) {
        // Store video data in session storage
        sessionStorage.setItem('uploadedVideo', e.target.result);
        sessionStorage.setItem('videoName', file.name);
        
        // Redirect to analysis page
        window.location.href = 'analysis.html';
      };
      
      reader.readAsDataURL(file);
    } else {
      alert('Please select a valid video file.');
    }
  });
  
  // Record video button (placeholder - requires webcam API)
  recordBtn.addEventListener('click', function() {
    alert('Video recording feature coming soon! Please use "Choose File" to upload a video for now.');
    // In a full implementation, this would open the camera and record video
  });
});
