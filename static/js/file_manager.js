// Benton County GIS File Manager
document.addEventListener('DOMContentLoaded', () => {
    // File upload form handling
    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('file-input');
    const fileNameDisplay = document.getElementById('file-name');
    const uploadBtn = document.getElementById('upload-btn');
    const progressBar = document.getElementById('upload-progress-bar');
    const progressContainer = document.getElementById('upload-progress');
    
    // File filter and search
    const searchInput = document.getElementById('file-search');
    const fileTypeFilter = document.getElementById('file-type-filter');
    const fileCards = document.querySelectorAll('.file-card');
    
    // Initialize file upload form
    if (uploadForm) {
        // Update file name display when a file is selected
        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) {
                fileNameDisplay.textContent = fileInput.files[0].name;
                uploadBtn.disabled = false;
            } else {
                fileNameDisplay.textContent = 'No file selected';
                uploadBtn.disabled = true;
            }
        });
        
        // Handle file upload
        uploadForm.addEventListener('submit', (e) => {
            // Show progress bar
            progressContainer.classList.remove('d-none');
            progressBar.style.width = '0%';
            progressBar.textContent = '0%';
            
            // Simulate upload progress
            // In a real implementation, this would use XHR or Fetch API to track actual progress
            const simulateProgress = () => {
                let progress = 0;
                const interval = setInterval(() => {
                    progress += 5;
                    progressBar.style.width = `${progress}%`;
                    progressBar.textContent = `${progress}%`;
                    
                    if (progress >= 100) {
                        clearInterval(interval);
                    }
                }, 200);
            };
            
            simulateProgress();
            
            // Let the form submit normally
        });
    }
    
    // Initialize search and filter functionality
    if (searchInput) {
        searchInput.addEventListener('input', filterFiles);
    }
    
    if (fileTypeFilter) {
        fileTypeFilter.addEventListener('change', filterFiles);
    }
    
    // File filtering function
    function filterFiles() {
        const searchTerm = searchInput.value.toLowerCase();
        const fileType = fileTypeFilter.value;
        
        fileCards.forEach(card => {
            const fileName = card.querySelector('.file-name').textContent.toLowerCase();
            const fileTypeText = card.querySelector('.file-type').textContent.toLowerCase();
            
            // Check if file matches search term
            const matchesSearch = fileName.includes(searchTerm);
            
            // Check if file matches type filter
            const matchesType = fileType === 'all' || fileTypeText.includes(fileType);
            
            // Show or hide card based on filters
            if (matchesSearch && matchesType) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
        
        // Update count of displayed files
        updateFileCount();
    }
    
    // Update file count display
    function updateFileCount() {
        const visibleFiles = document.querySelectorAll('.file-card[style="display: block;"]').length;
        const totalFiles = fileCards.length;
        
        document.getElementById('file-count').textContent = `${visibleFiles} of ${totalFiles} files`;
    }
    
    // Initialize file count
    if (document.getElementById('file-count')) {
        updateFileCount();
    }
    
    // Confirm file deletion
    const deleteButtons = document.querySelectorAll('.delete-file-btn');
    deleteButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            if (!confirm('Are you sure you want to delete this file? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    });
    
    // Initialize tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    
    // File metadata viewer
    const metadataButtons = document.querySelectorAll('.view-metadata-btn');
    metadataButtons.forEach(button => {
        button.addEventListener('click', () => {
            const metadata = JSON.parse(button.getAttribute('data-metadata'));
            
            // Populate modal with metadata
            const metadataContainer = document.getElementById('file-metadata-content');
            metadataContainer.innerHTML = formatMetadata(metadata);
            
            // Show modal
            const metadataModal = new bootstrap.Modal(document.getElementById('metadata-modal'));
            metadataModal.show();
        });
    });
    
    // Format metadata as HTML
    function formatMetadata(metadata) {
        if (!metadata) {
            return '<p class="text-muted">No metadata available for this file.</p>';
        }
        
        let html = '<table class="table table-sm">';
        
        // Iterate through metadata properties
        for (const key in metadata) {
            if (metadata.hasOwnProperty(key)) {
                let value = metadata[key];
                
                // Format value based on type
                if (typeof value === 'object' && value !== null) {
                    value = `<pre class="mb-0"><code>${JSON.stringify(value, null, 2)}</code></pre>`;
                }
                
                html += `
                <tr>
                    <th>${key}</th>
                    <td>${value}</td>
                </tr>`;
            }
        }
        
        html += '</table>';
        return html;
    }
});
