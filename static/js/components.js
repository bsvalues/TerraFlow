/**
 * TerraFlow UI Component System
 * A unified component architecture for consistent UI/UX
 */

class UIComponent {
  constructor(element) {
    this.element = element;
    this.initialized = false;
  }
  
  init() {
    if (this.initialized) return;
    this.setupEventListeners();
    this.initialized = true;
    return this;
  }
  
  setupEventListeners() {
    // To be implemented by child classes
  }
  
  destroy() {
    // Clean up any event listeners
    this.initialized = false;
  }
}

/**
 * Data Card component
 * Displays data with loading, error and empty states
 */
class DataCard extends UIComponent {
  constructor(element) {
    super(element);
    this.loadingTemplate = this.element.querySelector('.loading-template') || this.createLoadingTemplate();
    this.errorTemplate = this.element.querySelector('.error-template') || this.createErrorTemplate();
    this.emptyTemplate = this.element.querySelector('.empty-template') || this.createEmptyTemplate();
    this.contentTemplate = this.element.querySelector('.content-template');
    this.dataContainer = this.element.querySelector('.data-container');
    this.retryButton = null;
  }
  
  setupEventListeners() {
    this.element.addEventListener('dataCard:loading', () => this.showLoading());
    this.element.addEventListener('dataCard:error', (e) => this.showError(e.detail));
    this.element.addEventListener('dataCard:empty', (e) => this.showEmpty(e.detail));
    this.element.addEventListener('dataCard:content', (e) => this.showContent(e.detail));
  }
  
  createLoadingTemplate() {
    const template = document.createElement('div');
    template.className = 'loading-template d-none';
    template.innerHTML = `
      <div class="text-center p-4">
        <div class="spinner-border text-primary mb-3" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
        <p class="loading-message mb-0">Loading data...</p>
      </div>
    `;
    this.element.appendChild(template);
    return template;
  }
  
  createErrorTemplate() {
    const template = document.createElement('div');
    template.className = 'error-template d-none';
    template.innerHTML = `
      <div class="text-center p-4">
        <div class="text-danger mb-3">
          <i class="fas fa-exclamation-circle fa-3x"></i>
        </div>
        <h5 class="error-title">Error Loading Data</h5>
        <p class="error-message mb-3">There was a problem loading the data.</p>
        <button type="button" class="btn btn-outline-primary retry-button">Retry</button>
      </div>
    `;
    this.element.appendChild(template);
    this.retryButton = template.querySelector('.retry-button');
    return template;
  }
  
  createEmptyTemplate() {
    const template = document.createElement('div');
    template.className = 'empty-template d-none';
    template.innerHTML = `
      <div class="text-center p-4">
        <div class="text-neutral mb-3">
          <i class="fas fa-search fa-3x"></i>
        </div>
        <h5 class="empty-title">No Data Found</h5>
        <p class="empty-message mb-0">No results match your criteria.</p>
      </div>
    `;
    this.element.appendChild(template);
    return template;
  }
  
  showLoading(message = 'Loading data...') {
    this._hideAll();
    const loadingMessage = this.loadingTemplate.querySelector('.loading-message');
    if (loadingMessage) loadingMessage.textContent = message;
    this.loadingTemplate.classList.remove('d-none');
    
    // Announce for screen readers
    this._announceForScreenReader(`Loading. ${message}`);
  }
  
  showError(detail = {}) {
    this._hideAll();
    const { message = 'There was a problem loading the data.', title = 'Error Loading Data', onRetry = null } = detail;
    
    const errorTitle = this.errorTemplate.querySelector('.error-title');
    const errorMessage = this.errorTemplate.querySelector('.error-message');
    
    if (errorTitle) errorTitle.textContent = title;
    if (errorMessage) errorMessage.textContent = message;
    
    // Set up retry handler if provided
    if (this.retryButton) {
      // Remove existing listeners
      const newRetryButton = this.retryButton.cloneNode(true);
      this.retryButton.parentNode.replaceChild(newRetryButton, this.retryButton);
      this.retryButton = newRetryButton;
      
      if (onRetry && typeof onRetry === 'function') {
        this.retryButton.addEventListener('click', onRetry);
      } else {
        this.retryButton.classList.add('d-none');
      }
    }
    
    this.errorTemplate.classList.remove('d-none');
    
    // Announce for screen readers
    this._announceForScreenReader(`Error. ${message}`);
  }
  
  showEmpty(detail = {}) {
    this._hideAll();
    const { message = 'No results match your criteria.', title = 'No Data Found' } = detail;
    
    const emptyTitle = this.emptyTemplate.querySelector('.empty-title');
    const emptyMessage = this.emptyTemplate.querySelector('.empty-message');
    
    if (emptyTitle) emptyTitle.textContent = title;
    if (emptyMessage) emptyMessage.textContent = message;
    
    this.emptyTemplate.classList.remove('d-none');
    
    // Announce for screen readers
    this._announceForScreenReader(`No data found. ${message}`);
  }
  
  showContent(detail = {}) {
    this._hideAll();
    
    if (this.dataContainer) {
      if (detail.html) {
        this.dataContainer.innerHTML = detail.html;
      } else if (detail.element) {
        // Clear existing content
        this.dataContainer.innerHTML = '';
        this.dataContainer.appendChild(detail.element);
      }
      this.dataContainer.classList.remove('d-none');
    } else if (this.contentTemplate) {
      this.contentTemplate.classList.remove('d-none');
    }
    
    // Announce for screen readers if specified
    if (detail.announcement) {
      this._announceForScreenReader(detail.announcement);
    }
  }
  
  _hideAll() {
    this.loadingTemplate?.classList.add('d-none');
    this.errorTemplate?.classList.add('d-none');
    this.emptyTemplate?.classList.add('d-none');
    this.contentTemplate?.classList.add('d-none');
    this.dataContainer?.classList.add('d-none');
  }
  
  _announceForScreenReader(message) {
    // Find or create an aria-live region
    let announcer = document.getElementById('screen-reader-announcer');
    
    if (!announcer) {
      announcer = document.createElement('div');
      announcer.id = 'screen-reader-announcer';
      announcer.className = 'visually-hidden';
      announcer.setAttribute('aria-live', 'polite');
      announcer.setAttribute('aria-atomic', 'true');
      document.body.appendChild(announcer);
    }
    
    // Update the announcer
    announcer.textContent = message;
  }
}

/**
 * Mobile Navigation component
 * Provides consistent mobile navigation experience
 */
class MobileNavigation extends UIComponent {
  constructor(element) {
    super(element);
    this.mobileDrawer = document.querySelector('.mobile-drawer') || this.createMobileDrawer();
    this.overlay = document.querySelector('.mobile-overlay') || this.createOverlay();
    this.isDrawerOpen = false;
    this.drawerWidth = 280; // Width in pixels
    this.startX = 0;
    this.currentX = 0;
    this.touchingSurface = false;
  }
  
  setupEventListeners() {
    // Toggle navigation
    const toggleButtons = document.querySelectorAll('[data-action="toggle-mobile-nav"]');
    toggleButtons.forEach(button => {
      button.addEventListener('click', () => this.toggleDrawer());
    });
    
    // Close when overlay is clicked
    this.overlay.addEventListener('click', () => this.closeDrawer());
    
    // Handle swipe gestures
    document.addEventListener('touchstart', (e) => this.handleTouchStart(e), { passive: true });
    document.addEventListener('touchmove', (e) => this.handleTouchMove(e), { passive: false });
    document.addEventListener('touchend', (e) => this.handleTouchEnd(e), { passive: true });
    
    // Close on escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.isDrawerOpen) {
        this.closeDrawer();
      }
    });
  }
  
  createMobileDrawer() {
    const drawer = document.createElement('div');
    drawer.className = 'mobile-drawer';
    drawer.setAttribute('aria-hidden', 'true');
    
    // Get current page for active highlighting
    const currentPath = window.location.pathname;
    
    drawer.innerHTML = `
      <div class="drawer-header">
        <div class="drawer-brand">
          <img src="/static/img/logo/terrafusion-logo.png" alt="Logo" class="drawer-logo" />
          <span class="drawer-title">TerraFlow</span>
        </div>
        <button class="drawer-close" aria-label="Close menu" data-action="toggle-mobile-nav">
          <i class="fas fa-times"></i>
        </button>
      </div>
      <nav class="drawer-nav">
        <ul class="drawer-nav-list">
          <li class="drawer-nav-item ${currentPath === '/' ? 'active' : ''}">
            <a href="/" class="drawer-nav-link">
              <i class="fas fa-home drawer-nav-icon"></i>
              <span>Home</span>
            </a>
          </li>
          <li class="drawer-nav-item ${currentPath.includes('/map') ? 'active' : ''}">
            <a href="/map_viewer" class="drawer-nav-link">
              <i class="fas fa-map drawer-nav-icon"></i>
              <span>Map Viewer</span>
            </a>
          </li>
          <li class="drawer-nav-item ${currentPath.includes('/file') ? 'active' : ''}">
            <a href="/file_manager" class="drawer-nav-link">
              <i class="fas fa-file drawer-nav-icon"></i>
              <span>Files</span>
            </a>
          </li>
          <li class="drawer-nav-item ${currentPath.includes('/search') ? 'active' : ''}">
            <a href="/search" class="drawer-nav-link">
              <i class="fas fa-search drawer-nav-icon"></i>
              <span>Search</span>
            </a>
          </li>
          <li class="drawer-nav-item ${currentPath.includes('/power_query') ? 'active' : ''}">
            <a href="/power_query" class="drawer-nav-link">
              <i class="fas fa-bolt drawer-nav-icon"></i>
              <span>Power Query</span>
            </a>
          </li>
        </ul>
      </nav>
      <div class="drawer-footer">
        <a href="/logout" class="drawer-footer-link">
          <i class="fas fa-sign-out-alt"></i>
          <span>Logout</span>
        </a>
      </div>
    `;
    
    document.body.appendChild(drawer);
    return drawer;
  }
  
  createOverlay() {
    const overlay = document.createElement('div');
    overlay.className = 'mobile-overlay';
    document.body.appendChild(overlay);
    return overlay;
  }
  
  openDrawer() {
    this.isDrawerOpen = true;
    this.mobileDrawer.classList.add('open');
    this.overlay.classList.add('active');
    document.body.classList.add('drawer-open');
    this.mobileDrawer.setAttribute('aria-hidden', 'false');
    
    // Set focus to drawer for accessibility
    setTimeout(() => {
      const closeButton = this.mobileDrawer.querySelector('.drawer-close');
      if (closeButton) closeButton.focus();
    }, 100);
  }
  
  closeDrawer() {
    this.isDrawerOpen = false;
    this.mobileDrawer.classList.remove('open');
    this.overlay.classList.remove('active');
    document.body.classList.remove('drawer-open');
    this.mobileDrawer.setAttribute('aria-hidden', 'true');
    
    // Return focus to toggle button for accessibility
    const toggleButton = document.querySelector('[data-action="toggle-mobile-nav"]:not(.drawer-close)');
    if (toggleButton) toggleButton.focus();
  }
  
  toggleDrawer() {
    if (this.isDrawerOpen) {
      this.closeDrawer();
    } else {
      this.openDrawer();
    }
  }
  
  handleTouchStart(e) {
    this.touchingSurface = true;
    this.startX = e.touches[0].clientX;
    this.currentX = this.startX;
  }
  
  handleTouchMove(e) {
    if (!this.touchingSurface) return;
    
    this.currentX = e.touches[0].clientX;
    const deltaX = this.currentX - this.startX;
    
    // Handling drawer opening (swipe right from edge)
    if (!this.isDrawerOpen && this.startX < 20 && deltaX > 0) {
      e.preventDefault(); // Prevent scrolling
      const openPercentage = Math.min(deltaX / this.drawerWidth, 1);
      this.mobileDrawer.style.transform = `translateX(${-this.drawerWidth + (deltaX)}px)`;
      this.overlay.style.opacity = openPercentage * 0.5;
      this.overlay.classList.add('active');
    }
    
    // Handling drawer closing (swipe left)
    if (this.isDrawerOpen && deltaX < 0) {
      e.preventDefault(); // Prevent scrolling
      const openPercentage = Math.max(1 + deltaX / this.drawerWidth, 0);
      this.mobileDrawer.style.transform = `translateX(${deltaX}px)`;
      this.overlay.style.opacity = openPercentage * 0.5;
    }
  }
  
  handleTouchEnd(e) {
    if (!this.touchingSurface) return;
    this.touchingSurface = false;
    
    const deltaX = this.currentX - this.startX;
    
    // Reset styles
    this.mobileDrawer.style.transform = '';
    this.overlay.style.opacity = '';
    
    // Determine if drawer should open or close based on swipe distance
    if (!this.isDrawerOpen && deltaX > 70) {
      this.openDrawer();
    } else if (this.isDrawerOpen && deltaX < -70) {
      this.closeDrawer();
    } else if (this.isDrawerOpen) {
      // Restore open state if swipe wasn't enough to close
      this.openDrawer();
    } else {
      // Restore closed state if swipe wasn't enough to open
      this.overlay.classList.remove('active');
    }
  }
}

/**
 * Toast Notification component
 * Provides consistent toast notifications across the application
 */
class ToastNotifications extends UIComponent {
  constructor() {
    super(document.body);
    this.container = document.getElementById('toast-container') || this.createContainer();
    this.toasts = [];
  }
  
  createContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    container.style.zIndex = '1090';
    document.body.appendChild(container);
    return container;
  }
  
  setupEventListeners() {
    document.addEventListener('toast:show', (e) => this.showToast(e.detail));
    
    // Add global method
    window.showToast = (detail) => this.showToast(detail);
  }
  
  showToast({ title, message, type = 'info', duration = 5000, actions = [] }) {
    // Create toast element
    const toastEl = document.createElement('div');
    toastEl.className = `toast align-items-center border-0 tf-toast tf-toast-${type}`;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    
    // Create actions markup if provided
    let actionsMarkup = '';
    if (actions && actions.length) {
      actionsMarkup = `
        <div class="toast-actions mt-2">
          ${actions.map(action => `
            <button type="button" class="btn btn-sm ${action.class || 'btn-outline-light'}" data-action="${action.action}">
              ${action.icon ? `<i class="fas fa-${action.icon} me-1"></i>` : ''}
              ${action.text}
            </button>
          `).join('')}
        </div>
      `;
    }
    
    // Create toast content
    toastEl.innerHTML = `
      <div class="d-flex">
        <div class="toast-body">
          <div class="d-flex align-items-center mb-1">
            <i class="fas fa-${this._getIconForType(type)} me-2"></i>
            <strong>${title}</strong>
          </div>
          <div>${message}</div>
          ${actionsMarkup}
        </div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
    `;
    
    // Add to container
    this.container.appendChild(toastEl);
    
    // Initialize toast
    const toast = new bootstrap.Toast(toastEl, {
      autohide: true,
      delay: duration
    });
    
    // Add any action event listeners
    if (actions && actions.length) {
      actions.forEach(action => {
        const actionButton = toastEl.querySelector(`[data-action="${action.action}"]`);
        if (actionButton && action.handler) {
          actionButton.addEventListener('click', (e) => {
            e.preventDefault();
            action.handler();
          });
        }
      });
    }
    
    // Show toast
    toast.show();
    
    // Remove from DOM after hiding
    toastEl.addEventListener('hidden.bs.toast', () => {
      toastEl.remove();
    });
    
    return toast;
  }
  
  _getIconForType(type) {
    switch (type) {
      case 'success': return 'check-circle';
      case 'warning': return 'exclamation-triangle';
      case 'danger': return 'exclamation-circle';
      case 'info': return 'info-circle';
      default: return 'bell';
    }
  }
}

/**
 * Form Validation component
 * Provides enhanced form validation with accessible error messages
 */
class FormValidator extends UIComponent {
  constructor(element) {
    super(element);
    this.form = element;
    this.submitButton = this.form.querySelector('[type="submit"]');
    this.validated = false;
  }
  
  setupEventListeners() {
    this.form.addEventListener('submit', e => this.handleSubmit(e));
    
    // Live validation for fields
    const inputs = this.form.querySelectorAll('input, select, textarea');
    inputs.forEach(input => {
      input.addEventListener('blur', () => this.validateField(input));
      input.addEventListener('input', () => {
        if (this.validated) {
          this.validateField(input);
        }
      });
    });
  }
  
  handleSubmit(e) {
    if (!this.form.checkValidity()) {
      e.preventDefault();
      e.stopPropagation();
      
      // Find the first invalid field and focus it
      const invalidField = this.form.querySelector(':invalid');
      if (invalidField) {
        invalidField.focus();
        this.validateField(invalidField);
      }
    }
    
    this.form.classList.add('was-validated');
    this.validated = true;
  }
  
  validateField(field) {
    // Remove existing error message
    const existingMessage = field.parentElement.querySelector('.invalid-feedback');
    if (existingMessage) {
      existingMessage.remove();
    }
    
    // If field is invalid, add custom error message
    if (!field.checkValidity()) {
      const errorMessage = document.createElement('div');
      errorMessage.className = 'invalid-feedback';
      errorMessage.textContent = this.getValidationMessage(field);
      field.parentElement.appendChild(errorMessage);
      
      // Add error class to parent for styling
      field.parentElement.classList.add('has-error');
    } else {
      // Remove error class
      field.parentElement.classList.remove('has-error');
    }
  }
  
  getValidationMessage(field) {
    // Get the validation message based on validation state
    if (field.validity.valueMissing) {
      return field.getAttribute('data-required-message') || 'This field is required';
    }
    
    if (field.validity.typeMismatch) {
      if (field.type === 'email') {
        return field.getAttribute('data-email-message') || 'Please enter a valid email address';
      }
      if (field.type === 'url') {
        return field.getAttribute('data-url-message') || 'Please enter a valid URL';
      }
    }
    
    if (field.validity.patternMismatch) {
      return field.getAttribute('data-pattern-message') || 'Please match the requested format';
    }
    
    if (field.validity.tooShort) {
      return `Please use at least ${field.minLength} characters`;
    }
    
    if (field.validity.tooLong) {
      return `Please use no more than ${field.maxLength} characters`;
    }
    
    if (field.validity.rangeUnderflow) {
      return `Value must be at least ${field.min}`;
    }
    
    if (field.validity.rangeOverflow) {
      return `Value must be no more than ${field.max}`;
    }
    
    return field.validationMessage || 'This value is invalid';
  }
}

/**
 * Initialize all UI components
 */
document.addEventListener('DOMContentLoaded', function() {
  // Register component classes for reuse
  window.TerraFlowUI = {
    DataCard,
    MobileNavigation,
    ToastNotifications,
    FormValidator
  };
  
  // Initialize Toast Notifications (singleton)
  const toastNotifications = new ToastNotifications().init();
  
  // Initialize Mobile Navigation on mobile devices
  if (window.innerWidth < 768) {
    const mobileNav = new MobileNavigation(document.body).init();
  }
  
  // Initialize DataCards
  document.querySelectorAll('.data-card').forEach(element => {
    new DataCard(element).init();
  });
  
  // Initialize Form Validators
  document.querySelectorAll('form.needs-validation').forEach(form => {
    new FormValidator(form).init();
  });
});