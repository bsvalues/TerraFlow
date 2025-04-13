/**
 * GeoAssessmentPro Main JavaScript
 * Benton County Assessor's Office
 * Copyright 2025
 */

// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    const popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Setup Flash message auto-dismissal
    const flashMessages = document.querySelectorAll('.alert-dismissible');
    flashMessages.forEach(function(alert) {
        // Auto dismiss after 5 seconds
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
    
    // Toggle password visibility for password fields
    const togglePasswordButtons = document.querySelectorAll('.toggle-password');
    togglePasswordButtons.forEach(button => {
        button.addEventListener('click', function() {
            const passwordInput = this.parentElement.querySelector('input');
            const icon = this.querySelector('i');
            
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                icon.classList.remove('bi-eye');
                icon.classList.add('bi-eye-slash');
            } else {
                passwordInput.type = 'password';
                icon.classList.remove('bi-eye-slash');
                icon.classList.add('bi-eye');
            }
        });
    });
    
    // Handle confirmation dialogs
    const confirmButtons = document.querySelectorAll('[data-confirm]');
    confirmButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm(this.getAttribute('data-confirm'))) {
                e.preventDefault();
                return false;
            }
        });
    });
    
    // Add active class to current nav item based on URL
    const currentLocation = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentLocation) {
            link.classList.add('active');
        }
    });
    
    // Form validation enhancement
    const forms = document.querySelectorAll('form.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        }, false);
    });
    
    // Copy to clipboard functionality
    const copyButtons = document.querySelectorAll('.copy-to-clipboard');
    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const textToCopy = this.getAttribute('data-clipboard-text');
            const tempInput = document.createElement('input');
            document.body.appendChild(tempInput);
            tempInput.value = textToCopy;
            tempInput.select();
            document.execCommand('copy');
            document.body.removeChild(tempInput);
            
            // Show success feedback
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="bi bi-check"></i> Copied!';
            setTimeout(() => {
                this.innerHTML = originalText;
            }, 2000);
        });
    });
    
    // Initialize date pickers if any
    if (typeof flatpickr !== 'undefined') {
        flatpickr('.datepicker', {
            dateFormat: 'Y-m-d',
            allowInput: true
        });
    }
    
    // Handle custom file inputs
    const customFileInputs = document.querySelectorAll('.custom-file-input');
    customFileInputs.forEach(input => {
        input.addEventListener('change', function(e) {
            const fileName = this.files[0].name;
            const nextSibling = this.nextElementSibling;
            nextSibling.innerText = fileName;
        });
    });
    
    // Collapsible card functionality
    const cardToggles = document.querySelectorAll('.card-header-toggle');
    cardToggles.forEach(toggle => {
        toggle.addEventListener('click', function() {
            const targetId = this.getAttribute('data-bs-target');
            const targetCollapse = document.querySelector(targetId);
            const isCollapsed = targetCollapse.classList.contains('show');
            const icon = this.querySelector('i');
            
            if (isCollapsed) {
                icon.classList.remove('bi-chevron-up');
                icon.classList.add('bi-chevron-down');
            } else {
                icon.classList.remove('bi-chevron-down');
                icon.classList.add('bi-chevron-up');
            }
        });
    });
});