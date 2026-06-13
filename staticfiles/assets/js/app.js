/*
 * ClothShare - Enhanced Community Clothing Donation Platform
 * Main JavaScript File
 * Handles UI interactions, form validation, and data management
 * Updated for Django backend integration
 */

// DOM Elements
const searchInput = document.getElementById('searchInput');
const searchBtn = document.getElementById('searchBtn');
const categoryFilter = document.getElementById('categoryFilter');
const sizeFilter = document.getElementById('sizeFilter');
const conditionFilter = document.getElementById('conditionFilter');
const modeFilter = document.getElementById('modeFilter');
const resetFilters = document.getElementById('resetFilters');
const loadMore = document.getElementById('loadMore');
const donationForm = document.getElementById('donationForm');
const requestForm = document.getElementById('requestForm');
const profileItemsGrid = document.getElementById('profileItemsGrid');
const requestsList = document.getElementById('requestsList');
const navToggle = document.getElementById('navToggle');
const navMenu = document.getElementById('navMenu');
const itemModal = document.getElementById('itemModal');
const modalBody = document.getElementById('modalBody');
const modalClose = document.querySelector('.modal__close');
const successToast = document.getElementById('successToast');
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('itemImages');
const uploadPreview = document.getElementById('uploadPreview');

// App state
let currentItems = [];
let displayedItems = 6;
let isFiltered = false;
let currentPage = 1;
let isLoading = false;
let hasMore = true;
let scrollPosition = 0;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

/**
 * Initialize the application
 */
function initializeApp() {
    console.log('🚀 Initializing ClothShare application...');
    
    // Get items from Django template data (if available)
    // In a real implementation, you'd fetch this via AJAX
    // For now, we'll work with the server-rendered content
    
    // Update impact statistics with animation
    animateImpactStats();
    
    // Set up event listeners
    setupEventListeners();
    
    // Set up tab functionality
    setupTabs();
    
    // Set up header scroll effect
    setupHeaderScroll();
    
    // Initialize any dynamic content
    initializeDynamicContent();
    
    // Initialize lazy loading for images
    initializeLazyLoading();
    
    // Initialize intersection observer for animations
    initializeIntersectionObserver();
    
    // Check for user preferences
    loadUserPreferences();
    
    console.log('✅ Application initialized successfully');
}

/**
 * Initialize dynamic content that might be added by Django
 */
function initializeDynamicContent() {
    // Add event listeners to dynamically loaded items
    document.querySelectorAll('.item-card').forEach(card => {
        const itemId = card.dataset.id;
        if (itemId) {
            const viewBtn = card.querySelector('.btn--outline, .item-card__btn');
            if (viewBtn) {
                viewBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    // Use the actual URL from the link
                    const link = card.querySelector('a[href*="/item/"]');
                    if (link) {
                        window.location.href = link.href;
                    }
                });
            }
        }
    });
    
    // Add hover effects to category cards
    document.querySelectorAll('.category-card').forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-8px) scale(1.02)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });
    
    // Add click effects to action cards
    document.querySelectorAll('.action-card').forEach(card => {
        card.addEventListener('click', function(e) {
            if (!e.target.closest('a')) {
                const link = this.querySelector('a');
                if (link) {
                    link.click();
                }
            }
        });
    });
}

/**
 * Initialize lazy loading for images
 */
function initializeLazyLoading() {
    if ('IntersectionObserver' in window) {
        const lazyImageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const lazyImage = entry.target;
                    lazyImage.src = lazyImage.dataset.src;
                    lazyImage.classList.remove('lazy');
                    lazyImageObserver.unobserve(lazyImage);
                }
            });
        });

        document.querySelectorAll('img.lazy').forEach(lazyImage => {
            lazyImageObserver.observe(lazyImage);
        });
    }
}

/**
 * Initialize intersection observer for scroll animations
 */
function initializeIntersectionObserver() {
    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in-up', 'visible');
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        });

        // Observe elements that should animate on scroll
        document.querySelectorAll('.feature, .category-card, .action-card, .item-card').forEach(el => {
            observer.observe(el);
        });
    }
}

/**
 * Set up all event listeners
 */
function setupEventListeners() {
    console.log('🔧 Setting up event listeners...');
    
    // Search and filter events
    if (searchInput) {
        searchInput.addEventListener('input', debounce(handleSearch, 300));
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                handleSearch();
            }
        });
    }
    if (searchBtn) {
        searchBtn.addEventListener('click', handleSearch);
    }
    if (categoryFilter) {
        categoryFilter.addEventListener('change', handleFilter);
    }
    if (sizeFilter) {
        sizeFilter.addEventListener('change', handleFilter);
    }
    if (conditionFilter) {
        conditionFilter.addEventListener('change', handleFilter);
    }
    if (modeFilter) {
        modeFilter.addEventListener('change', handleFilter);
    }
    if (resetFilters) {
        resetFilters.addEventListener('click', resetAllFilters);
    }
    if (loadMore) {
        loadMore.addEventListener('click', loadMoreItems);
    }
    
    // Form submissions
    if (donationForm) {
        donationForm.addEventListener('submit', handleDonationSubmit);
        // Add real-time validation
        addRealTimeValidation(donationForm);
    }
    if (requestForm) {
        requestForm.addEventListener('submit', handleRequestSubmit);
        addRealTimeValidation(requestForm);
    }
    
    // Navigation
    if (navToggle) {
        navToggle.addEventListener('click', toggleMobileMenu);
    }
    
    // Modal
    if (modalClose) {
        modalClose.addEventListener('click', closeModal);
    }
    if (itemModal) {
        window.addEventListener('click', (e) => {
            if (e.target === itemModal) {
                closeModal();
            }
        });
        
        // Close modal on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && itemModal.style.display === 'block') {
                closeModal();
            }
        });
    }
    
    // File upload
    if (uploadArea && fileInput) {
        uploadArea.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', handleFileUpload);
        setupDragAndDrop();
    }
    
    // Smooth scrolling for navigation links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
                
                // Update active nav link
                document.querySelectorAll('.nav__link').forEach(link => {
                    link.classList.remove('active');
                });
                this.classList.add('active');
                
                // Close mobile menu if open
                if (navMenu) {
                    navMenu.classList.remove('active');
                }
            }
        });
    });
    
    // Update active nav link on scroll
    window.addEventListener('scroll', throttle(updateActiveNavLink, 100));
    
    // Handle window resize
    window.addEventListener('resize', throttle(handleResize, 250));
    
    // Handle page visibility changes
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    // Add loading state to buttons on click
    document.addEventListener('click', function(e) {
        if (e.target.matches('.btn[type="submit"], .btn--primary, .btn--secondary')) {
            addLoadingState(e.target);
        }
    });
    
    console.log('✅ Event listeners setup complete');
}

/**
 * Add real-time validation to form fields
 */
function addRealTimeValidation(form) {
    const inputs = form.querySelectorAll('input, textarea, select');
    
    inputs.forEach(input => {
        input.addEventListener('blur', function() {
            validateField(this);
        });
        
        input.addEventListener('input', function() {
            clearFieldError(this);
        });
    });
}

/**
 * Validate a single form field
 */
function validateField(field) {
    const value = field.value.trim();
    const errorElement = document.getElementById(field.id + 'Error');
    
    if (!errorElement) return;
    
    // Clear previous error
    errorElement.classList.remove('show');
    
    // Required field validation
    if (field.hasAttribute('required') && !value) {
        showFieldError(field, 'This field is required');
        return false;
    }
    
    // Email validation
    if (field.type === 'email' && value) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(value)) {
            showFieldError(field, 'Please enter a valid email address');
            return false;
        }
    }
    
    // Minimum length validation
    if (field.dataset.minLength && value.length < parseInt(field.dataset.minLength)) {
        showFieldError(field, `Must be at least ${field.dataset.minLength} characters`);
        return false;
    }
    
    // Maximum length validation
    if (field.dataset.maxLength && value.length > parseInt(field.dataset.maxLength)) {
        showFieldError(field, `Must be less than ${field.dataset.maxLength} characters`);
        return false;
    }
    
    return true;
}

/**
 * Show field error message
 */
function showFieldError(field, message) {
    const errorElement = document.getElementById(field.id + 'Error');
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.classList.add('show');
        field.classList.add('error');
    }
}

/**
 * Clear field error
 */
function clearFieldError(field) {
    const errorElement = document.getElementById(field.id + 'Error');
    if (errorElement) {
        errorElement.classList.remove('show');
        field.classList.remove('error');
    }
}

/**
 * Set up tab functionality for profile section
 */
function setupTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active class from all buttons and contents
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            // Add active class to clicked button
            btn.classList.add('active');
            
            // Show corresponding content
            const tabId = btn.getAttribute('data-tab');
            const tabContent = document.getElementById(tabId);
            if (tabContent) {
                tabContent.classList.add('active');
            }
            
            // Save active tab to localStorage
            localStorage.setItem('activeTab', tabId);
        });
    });
    
    // Restore active tab from localStorage
    const savedTab = localStorage.getItem('activeTab');
    if (savedTab) {
        const savedBtn = document.querySelector(`[data-tab="${savedTab}"]`);
        if (savedBtn) {
            savedBtn.click();
        }
    }
}

/**
 * Set up header scroll effect
 */
function setupHeaderScroll() {
    const header = document.querySelector('.header');
    let lastScrollY = window.scrollY;
    
    if (header) {
        window.addEventListener('scroll', () => {
            const currentScrollY = window.scrollY;
            
            if (currentScrollY > 100) {
                header.classList.add('scrolled');
                
                // Hide header on scroll down, show on scroll up
                if (currentScrollY > lastScrollY && currentScrollY > 200) {
                    header.classList.add('hidden');
                } else {
                    header.classList.remove('hidden');
                }
            } else {
                header.classList.remove('scrolled', 'hidden');
            }
            
            lastScrollY = currentScrollY;
        });
    }
}

/**
 * Set up drag and drop for file upload
 */
function setupDragAndDrop() {
    if (!uploadArea) return;
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, unhighlight, false);
    });
    
    function highlight() {
        uploadArea.classList.add('dragover');
        uploadArea.querySelector('.upload-area__text').textContent = 'Drop files here...';
    }
    
    function unhighlight() {
        uploadArea.classList.remove('dragover');
        uploadArea.querySelector('.upload-area__text').textContent = 'Drag & drop files or click to browse';
    }
    
    uploadArea.addEventListener('drop', handleDrop, false);
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        fileInput.files = files;
        handleFileUpload({ target: { files } });
    }
}

/**
 * Update active navigation link based on scroll position
 */
function updateActiveNavLink() {
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('.nav__link');
    
    let current = '';
    const scrollPosition = window.scrollY + 100;
    
    sections.forEach(section => {
        const sectionTop = section.offsetTop;
        const sectionHeight = section.clientHeight;
        
        if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
            current = section.getAttribute('id');
        }
    });
    
    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === `#${current}`) {
            link.classList.add('active');
        }
    });
}

/**
 * Animate impact statistics counting up
 */
function animateImpactStats() {
    const impactStats = document.querySelectorAll('.impact-number');
    
    impactStats.forEach(stat => {
        const finalValue = parseInt(stat.textContent) || 0;
        const duration = 2000;
        const step = Math.ceil(finalValue / (duration / 16)); // 60fps
        
        let current = 0;
        const timer = setInterval(() => {
            current += step;
            if (current >= finalValue) {
                current = finalValue;
                clearInterval(timer);
            }
            stat.textContent = current.toLocaleString();
        }, 16);
    });
}

/**
 * Handle search input with debouncing
 */
function handleSearch() {
    const searchTerm = searchInput ? searchInput.value.toLowerCase().trim() : '';
    
    if (searchTerm.length >= 2) {
        // Add search feedback
        if (searchBtn) {
            searchBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        }
        
        // Simulate search delay
        setTimeout(() => {
            applyFilters();
            if (searchBtn) {
                searchBtn.innerHTML = '<i class="fas fa-search"></i>';
            }
        }, 500);
    } else if (searchTerm.length === 0) {
        applyFilters();
    }
}

/**
 * Handle filter changes
 */
function handleFilter() {
    applyFilters();
    
    // Update URL with filter parameters (without page reload)
    updateURLWithFilters();
}

/**
 * Update URL with current filter parameters
 */
function updateURLWithFilters() {
    if (!history.pushState) return;
    
    const params = new URLSearchParams();
    
    if (searchInput && searchInput.value) {
        params.set('search', searchInput.value);
    }
    if (categoryFilter && categoryFilter.value) {
        params.set('category', categoryFilter.value);
    }
    if (sizeFilter && sizeFilter.value) {
        params.set('size', sizeFilter.value);
    }
    if (conditionFilter && conditionFilter.value) {
        params.set('condition', conditionFilter.value);
    }
    if (modeFilter && modeFilter.value) {
        params.set('mode', modeFilter.value);
    }
    
    const newUrl = params.toString() ? `${window.location.pathname}?${params}` : window.location.pathname;
    history.replaceState(null, '', newUrl);
}

/**
 * Apply all filters and search to items (client-side fallback)
 */
function applyFilters() {
    const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';
    const category = categoryFilter ? categoryFilter.value : '';
    const size = sizeFilter ? sizeFilter.value : '';
    const condition = conditionFilter ? conditionFilter.value : '';
    const mode = modeFilter ? modeFilter.value : '';
    
    const itemCards = document.querySelectorAll('.item-card');
    let visibleCount = 0;
    
    itemCards.forEach(card => {
        const title = card.querySelector('.item-card__title')?.textContent.toLowerCase() || '';
        const description = card.querySelector('.item-card__description')?.textContent.toLowerCase() || '';
        const categoryText = card.querySelector('.item-card__category')?.textContent.toLowerCase() || '';
        const conditionText = card.querySelector('.item-card__condition')?.textContent.toLowerCase() || '';
        const sizeText = card.querySelector('.item-card__size')?.textContent.toLowerCase() || '';
        const modeText = card.querySelector('.item-mode')?.textContent.toLowerCase() || '';
        
        const matchesSearch = !searchTerm || 
            title.includes(searchTerm) ||
            description.includes(searchTerm);
        
        const matchesCategory = !category || categoryText.includes(category);
        const matchesSize = !size || sizeText.includes(size);
        const matchesCondition = !condition || conditionText.includes(condition);
        const matchesMode = !mode || modeText.includes(mode);
        
        if (matchesSearch && matchesCategory && matchesSize && matchesCondition && matchesMode) {
            card.style.display = 'block';
            visibleCount++;
            
            // Add fade-in animation
            card.style.animation = 'fadeInUp 0.6s ease';
        } else {
            card.style.display = 'none';
        }
    });
    
    isFiltered = searchTerm || category || size || condition || mode;
    
    // Show no results message if no items match
    const noResults = document.getElementById('noResults');
    if (!noResults && visibleCount === 0 && itemCards.length > 0) {
        const grid = itemCards[0].parentElement;
        const noResultsEl = document.createElement('div');
        noResultsEl.id = 'noResults';
        noResultsEl.className = 'empty-state';
        noResultsEl.innerHTML = `
            <i class="fas fa-search"></i>
            <h3>No items found</h3>
            <p>Try adjusting your search or filters</p>
            <button class="btn btn--primary" onclick="resetAllFilters()">Reset Filters</button>
        `;
        grid.appendChild(noResultsEl);
    } else if (noResults) {
        noResults.style.display = visibleCount === 0 ? 'block' : 'none';
    }
    
    // Update results count
    updateResultsCount(visibleCount);
}

/**
 * Update results count display
 */
function updateResultsCount(count) {
    let resultsCount = document.getElementById('resultsCount');
    if (!resultsCount) {
        resultsCount = document.createElement('div');
        resultsCount.id = 'resultsCount';
        resultsCount.className = 'results-count';
        const filtersContainer = document.querySelector('.filters') || document.querySelector('.items-grid').parentElement;
        filtersContainer.insertBefore(resultsCount, document.querySelector('.items-grid'));
    }
    
    resultsCount.textContent = `${count} item${count !== 1 ? 's' : ''} found`;
    resultsCount.style.display = count > 0 ? 'block' : 'none';
}

/**
 * Reset all filters
 */
function resetAllFilters() {
    if (searchInput) searchInput.value = '';
    if (categoryFilter) categoryFilter.value = '';
    if (sizeFilter) sizeFilter.value = '';
    if (conditionFilter) conditionFilter.value = '';
    if (modeFilter) modeFilter.value = '';
    
    // Show all items with animation
    document.querySelectorAll('.item-card').forEach((card, index) => {
        card.style.display = 'block';
        card.style.animationDelay = `${index * 0.1}s`;
        card.classList.add('fade-in-up');
    });
    
    isFiltered = false;
    
    // Clear URL parameters
    history.replaceState(null, '', window.location.pathname);
    
    // Hide results count
    const resultsCount = document.getElementById('resultsCount');
    if (resultsCount) {
        resultsCount.style.display = 'none';
    }
    
    // Hide no results message
    const noResults = document.getElementById('noResults');
    if (noResults) {
        noResults.style.display = 'none';
    }
    
    showToast('Filters reset successfully');
}

/**
 * Load more items (for client-side demo)
 */
function loadMoreItems() {
    if (isLoading) return;
    
    isLoading = true;
    
    // Show loading state
    if (loadMore) {
        loadMore.disabled = true;
        loadMore.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
    }
    
    // Simulate API call
    setTimeout(() => {
        // This would be an actual API call in production
        const newItems = generateMockItems(6);
        
        if (newItems.length > 0) {
            // Append new items to grid
            const itemsGrid = document.querySelector('.items-grid');
            newItems.forEach(item => {
                const itemElement = createItemElement(item);
                itemsGrid.appendChild(itemElement);
            });
            
            // Re-initialize dynamic content for new items
            initializeDynamicContent();
            
            showToast(`Loaded ${newItems.length} more items`);
        } else {
            showToast('No more items to load');
            if (loadMore) {
                loadMore.style.display = 'none';
            }
            hasMore = false;
        }
        
        isLoading = false;
        
        if (loadMore) {
            loadMore.disabled = false;
            loadMore.innerHTML = '<i class="fas fa-plus"></i> Load More Items';
        }
    }, 1000);
}

/**
 * Generate mock items for demo purposes
 */
function generateMockItems(count) {
    const items = [];
    const categories = ['Tops', 'Bottoms', 'Dresses', 'Outerwear', 'Accessories'];
    const conditions = ['New', 'Like New', 'Good', 'Fair'];
    const modes = ['donate', 'exchange'];
    
    for (let i = 0; i < count; i++) {
        items.push({
            id: Date.now() + i,
            title: `Demo Item ${i + 1}`,
            category: categories[Math.floor(Math.random() * categories.length)],
            condition: conditions[Math.floor(Math.random() * conditions.length)],
            mode: modes[Math.floor(Math.random() * modes.length)],
            image: null
        });
    }
    
    return items;
}

/**
 * Create item element from data
 */
function createItemElement(item) {
    const itemEl = document.createElement('div');
    itemEl.className = 'item-card fade-in-up';
    itemEl.innerHTML = `
        <div class="item-card__image placeholder">
            <i class="fas fa-tshirt"></i>
        </div>
        <div class="item-card__content">
            <h3 class="item-card__title">${item.title}</h3>
            <p class="item-card__category">${item.category}</p>
            <p class="item-card__condition">${item.condition}</p>
            <div class="item-card__meta">
                <span class="item-mode ${item.mode}">${item.mode.charAt(0).toUpperCase() + item.mode.slice(1)}</span>
            </div>
            <button class="btn btn--outline btn--small">View Details</button>
        </div>
    `;
    
    return itemEl;
}

/**
 * Handle donation form submission
 */
function handleDonationSubmit(e) {
    e.preventDefault();
    
    if (validateDonationForm()) {
        // Add loading state to form
        const submitBtn = donationForm.querySelector('button[type="submit"]');
        addLoadingState(submitBtn);
        
        // Simulate API call
        setTimeout(() => {
            showToast('Thank you for your donation! Your item has been submitted for review.');
            
            // Reset form
            donationForm.reset();
            if (uploadPreview) {
                uploadPreview.innerHTML = '';
            }
            
            // Remove loading state
            removeLoadingState(submitBtn);
            
            // Redirect to browse page or show success message
            setTimeout(() => {
                window.location.href = '/browse/';
            }, 2000);
        }, 1500);
    }
}

/**
 * Handle request form submission
 */
function handleRequestSubmit(e) {
    e.preventDefault();
    
    if (validateRequestForm()) {
        const submitBtn = requestForm.querySelector('button[type="submit"]');
        addLoadingState(submitBtn);
        
        setTimeout(() => {
            showToast('Your request has been submitted! We\'ll notify you when matching items are available.');
            
            requestForm.reset();
            removeLoadingState(submitBtn);
        }, 1500);
    }
}

/**
 * Validate donation form
 */
function validateDonationForm() {
    let isValid = true;
    
    // Reset error messages
    document.querySelectorAll('.error-message').forEach(el => {
        el.classList.remove('show');
    });
    
    // Validate item name
    const itemName = document.getElementById('itemName');
    if (itemName && !itemName.value.trim()) {
        showFieldError(itemName, 'Item name is required');
        isValid = false;
    }
    
    // Validate category
    const category = document.getElementById('itemCategory');
    if (category && !category.value) {
        showFieldError(category, 'Category is required');
        isValid = false;
    }
    
    // Validate condition
    const condition = document.getElementById('itemCondition');
    if (condition && !condition.value) {
        showFieldError(condition, 'Condition is required');
        isValid = false;
    }
    
    // Validate mode
    const mode = document.getElementById('itemMode');
    if (mode && !mode.value) {
        showFieldError(mode, 'Mode is required');
        isValid = false;
    }
    
    // Validate description
    const description = document.getElementById('itemDescription');
    if (description) {
        const descValue = description.value.trim();
        if (!descValue) {
            showFieldError(description, 'Description is required');
            isValid = false;
        } else if (descValue.length < 10) {
            showFieldError(description, 'Description should be at least 10 characters');
            isValid = false;
        }
    }
    
    // Validate images
    const fileInput = document.getElementById('itemImages');
    if (fileInput && fileInput.files.length === 0) {
        showToast('Please upload at least one image of your item');
        isValid = false;
    }
    
    return isValid;
}

/**
 * Validate request form
 */
function validateRequestForm() {
    let isValid = true;
    
    // Reset error messages
    document.querySelectorAll('.error-message').forEach(el => {
        el.classList.remove('show');
    });
    
    // Validate category
    const category = document.getElementById('requestCategory');
    if (category && !category.value) {
        showFieldError(category, 'Category is required');
        isValid = false;
    }
    
    // Validate description
    const description = document.getElementById('requestDescription');
    if (description) {
        const descValue = description.value.trim();
        if (!descValue) {
            showFieldError(description, 'Please describe what you need');
            isValid = false;
        } else if (descValue.length < 10) {
            showFieldError(description, 'Description should be at least 10 characters');
            isValid = false;
        }
    }
    
    return isValid;
}

/**
 * Handle file upload for item images
 */
function handleFileUpload(e) {
    if (!uploadPreview) return;
    
    const files = e.target.files;
    const maxFiles = 5;
    const maxSize = 5 * 1024 * 1024; // 5MB
    
    if (files.length > maxFiles) {
        showToast(`Please select no more than ${maxFiles} files`);
        fileInput.value = '';
        return;
    }
    
    // Clear existing previews if we're replacing files
    if (!fileInput.hasAttribute('multiple') || fileInput.files.length === 1) {
        uploadPreview.innerHTML = '';
    }
    
    Array.from(files).forEach(file => {
        // Check file size
        if (file.size > maxSize) {
            showToast(`File ${file.name} is too large. Maximum size is 5MB.`);
            return;
        }
        
        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            
            reader.onload = function(e) {
                const previewItem = document.createElement('div');
                previewItem.className = 'upload-preview__item';
                
                const img = document.createElement('img');
                img.src = e.target.result;
                img.alt = 'Upload preview';
                
                const removeBtn = document.createElement('button');
                removeBtn.className = 'upload-preview__remove';
                removeBtn.innerHTML = '&times;';
                removeBtn.title = 'Remove image';
                removeBtn.onclick = function() {
                    previewItem.remove();
                    updateFileInput();
                };
                
                previewItem.appendChild(img);
                previewItem.appendChild(removeBtn);
                uploadPreview.appendChild(previewItem);
            };
            
            reader.readAsDataURL(file);
        } else {
            showToast('Please select image files only (JPEG, PNG, etc.)');
        }
    });
}

/**
 * Update file input after removing previews
 */
function updateFileInput() {
    // This would need a more complex implementation to actually update the files
    // For now, we'll just show a message
    showToast('Image removed. To update the file selection, please re-upload all images.');
}

/**
 * Add loading state to button
 */
function addLoadingState(button) {
    button.disabled = true;
    button.dataset.originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
}

/**
 * Remove loading state from button
 */
function removeLoadingState(button) {
    button.disabled = false;
    if (button.dataset.originalText) {
        button.innerHTML = button.dataset.originalText;
    }
}

/**
 * Open the modal
 */
function openModal() {
    if (itemModal) {
        // Save current scroll position
        scrollPosition = window.pageYOffset;
        
        itemModal.style.display = 'block';
        document.body.style.overflow = 'hidden';
        document.body.style.position = 'fixed';
        document.body.style.width = '100%';
        document.body.style.top = `-${scrollPosition}px`;
        
        // Add animation
        itemModal.classList.add('modal--open');
    }
}

/**
 * Close the modal
 */
function closeModal() {
    if (itemModal) {
        itemModal.style.display = 'none';
        document.body.style.overflow = 'auto';
        document.body.style.position = '';
        document.body.style.width = '';
        document.body.style.top = '';
        
        // Restore scroll position
        window.scrollTo(0, scrollPosition);
        
        itemModal.classList.remove('modal--open');
    }
}

/**
 * Show toast message
 */
function showToast(message, type = 'success') {
    // Remove existing toasts
    document.querySelectorAll('.toast').forEach(toast => {
        if (toast !== successToast) {
            toast.remove();
        }
    });
    
    let toast = successToast;
    
    if (!toast) {
        // Create toast if it doesn't exist
        toast = document.createElement('div');
        toast.className = `toast toast--${type}`;
        toast.innerHTML = `
            <div class="toast__content">
                <span class="toast__message">${message}</span>
                <button class="toast__close">&times;</button>
            </div>
        `;
        document.body.appendChild(toast);
        
        // Add close event
        toast.querySelector('.toast__close').addEventListener('click', () => {
            toast.remove();
        });
    } else {
        // Use existing toast
        const messageEl = toast.querySelector('.toast__message');
        if (messageEl) {
            messageEl.textContent = message;
        }
        toast.className = `toast toast--${type}`;
    }
    
    toast.style.display = 'flex';
    
    // Add show class for animation
    setTimeout(() => {
        toast.classList.add('toast--show');
    }, 10);
    
    // Auto hide after 5 seconds
    setTimeout(() => {
        toast.classList.remove('toast--show');
        setTimeout(() => {
            toast.style.display = 'none';
        }, 300);
    }, 5000);
}

/**
 * Toggle mobile menu
 */
function toggleMobileMenu() {
    if (navMenu) {
        navMenu.classList.toggle('active');
        navToggle.classList.toggle('active');
        
        // Prevent body scroll when menu is open
        if (navMenu.classList.contains('active')) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = 'auto';
        }
    }
}

/**
 * Handle window resize
 */
function handleResize() {
    // Close mobile menu on resize to desktop
    if (window.innerWidth > 768 && navMenu && navMenu.classList.contains('active')) {
        navMenu.classList.remove('active');
        navToggle.classList.remove('active');
        document.body.style.overflow = 'auto';
    }
}

/**
 * Handle page visibility change
 */
function handleVisibilityChange() {
    if (document.hidden) {
        // Page is hidden
        console.log('Page is hidden');
    } else {
        // Page is visible
        console.log('Page is visible');
        // You could refresh notifications or update data here
    }
}

/**
 * Load user preferences from localStorage
 */
function loadUserPreferences() {
    // Load theme preference
    const theme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', theme);
    
    // Load other preferences...
}

/**
 * Save user preferences to localStorage
 */
function saveUserPreferences(key, value) {
    localStorage.setItem(key, value);
}

// Utility Functions

/**
 * Debounce function to limit how often a function is called
 */
function debounce(func, wait, immediate) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            timeout = null;
            if (!immediate) func(...args);
        };
        const callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func(...args);
    };
}

/**
 * Throttle function to limit function execution rate
 */
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Format date for display
 */
function formatDate(dateString) {
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return new Date(dateString).toLocaleDateString(undefined, options);
}

/**
 * Format file size for display
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// AJAX functionality for dynamic content loading

/**
 * Search items via AJAX
 */
function searchItemsAjax(query) {
    if (query.length < 2) return;
    
    fetch(`/ajax/search/?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            // Handle search results
            console.log('Search results:', data);
        })
        .catch(error => {
            console.error('Search error:', error);
            showToast('Search failed. Please try again.', 'error');
        });
}

/**
 * Get unread notification count
 */
function getUnreadNotificationCount() {
    fetch('/ajax/notifications/count/')
        .then(response => response.json())
        .then(data => {
            // Update notification badge
            const badge = document.querySelector('.notification-badge');
            if (badge && data.count > 0) {
                badge.textContent = data.count;
                badge.style.display = 'block';
            }
        })
        .catch(error => {
            console.error('Notification count error:', error);
        });
}

// Export functions for global access (if needed)
window.ClothShare = {
    initializeApp,
    showToast,
    resetAllFilters,
    loadMoreItems,
    toggleMobileMenu
};

console.log('🎉 ClothShare JavaScript loaded successfully!');