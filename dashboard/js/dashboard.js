// Dashboard Main JavaScript
document.addEventListener('DOMContentLoaded', function() {
    
    // Initialize dashboard
    initNavigation();
    initThemeToggle();
    initSearchForm();
    initModals();
    initFileUpload();
    initTooltips();
    initMobileMenu();
    
    // Page Navigation
    function initNavigation() {
        const navItems = document.querySelectorAll('.nav-item');
        const pages = document.querySelectorAll('.page');
        
        navItems.forEach(item => {
            item.addEventListener('click', function(e) {
                e.preventDefault();
                
                // Remove active class from all items and pages
                navItems.forEach(nav => nav.classList.remove('active'));
                pages.forEach(page => page.classList.remove('active'));
                
                // Add active class to clicked item
                this.classList.add('active');
                
                // Show corresponding page
                const pageName = this.dataset.page;
                const targetPage = document.getElementById(pageName);
                if (targetPage) {
                    targetPage.classList.add('active');
                }
                
                // Update URL hash
                window.location.hash = pageName;
                
                // Close mobile menu if open
                document.getElementById('sidebar').classList.remove('active');
            });
        });
        
        // Handle initial page load from hash
        const hash = window.location.hash.slice(1);
        if (hash) {
            const navItem = document.querySelector(`[data-page="${hash}"]`);
            if (navItem) {
                navItem.click();
            }
        }
    }
    
    // Theme Toggle
    function initThemeToggle() {
        const themeToggle = document.getElementById('theme-toggle');
        const html = document.documentElement;
        
        // Load saved theme or default to light
        const savedTheme = localStorage.getItem('theme') || 'light';
        html.dataset.theme = savedTheme;
        updateThemeIcon();
        
        themeToggle.addEventListener('click', function() {
            const currentTheme = html.dataset.theme;
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            
            html.dataset.theme = newTheme;
            localStorage.setItem('theme', newTheme);
            updateThemeIcon();
            
            // Show toast notification
            showToast(`Switched to ${newTheme} mode`);
        });
        
        function updateThemeIcon() {
            const icon = themeToggle.querySelector('i');
            if (html.dataset.theme === 'dark') {
                icon.classList.remove('fa-moon');
                icon.classList.add('fa-sun');
            } else {
                icon.classList.remove('fa-sun');
                icon.classList.add('fa-moon');
            }
        }
    }
    
    // Mobile Menu Toggle
    function initMobileMenu() {
        const menuToggle = document.getElementById('menu-toggle');
        const sidebar = document.getElementById('sidebar');
        
        menuToggle.addEventListener('click', function() {
            sidebar.classList.toggle('active');
        });
        
        // Close sidebar when clicking outside
        document.addEventListener('click', function(e) {
            if (!sidebar.contains(e.target) && !menuToggle.contains(e.target)) {
                sidebar.classList.remove('active');
            }
        });
    }
    
    // Search Form
    function initSearchForm() {
        const searchForm = document.getElementById('jobSearchForm');
        const progressContainer = document.getElementById('searchProgress');
        const progressPercent = document.getElementById('progressPercent');
        
        if (searchForm) {
            searchForm.addEventListener('submit', function(e) {
                e.preventDefault();
                
                // Get form data
                const formData = new FormData(searchForm);
                const searchData = {
                    keywords: formData.get('keywords'),
                    location: document.getElementById('location').value,
                    jobType: document.getElementById('jobType').value,
                    experience: document.getElementById('experience').value,
                    aiMatching: searchForm.querySelector('input[type="checkbox"]').checked,
                    googleSheets: searchForm.querySelectorAll('input[type="checkbox"]')[1].checked
                };
                
                // Show progress
                progressContainer.style.display = 'block';
                searchForm.querySelector('button[type="submit"]').disabled = true;
                
                // Simulate search progress
                let progress = 0;
                const progressInterval = setInterval(() => {
                    progress += Math.random() * 15;
                    if (progress >= 100) {
                        progress = 100;
                        clearInterval(progressInterval);
                        
                        // Hide progress and show results
                        setTimeout(() => {
                            progressContainer.style.display = 'none';
                            searchForm.querySelector('button[type="submit"]').disabled = false;
                            showToast('Search completed! Found 15 matching jobs.');
                            
                            // Scroll to results
                            document.querySelector('.results-section').scrollIntoView({
                                behavior: 'smooth'
                            });
                        }, 500);
                    }
                    
                    progressPercent.textContent = Math.round(progress);
                    document.querySelector('.progress-fill').style.width = progress + '%';
                }, 200);
            });
        }
    }
    
    // Modal Management
    function initModals() {
        const modal = document.getElementById('jobModal');
        const modalClose = modal?.querySelector('.modal-close');
        const viewButtons = document.querySelectorAll('.icon-btn[title="View Details"]');
        
        viewButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.stopPropagation();
                showJobModal();
            });
        });
        
        modalClose?.addEventListener('click', closeModal);
        
        modal?.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeModal();
            }
        });
        
        function showJobModal() {
            modal.classList.add('show');
            document.body.style.overflow = 'hidden';
        }
        
        function closeModal() {
            modal.classList.remove('show');
            document.body.style.overflow = '';
        }
    }
    
    // File Upload
    function initFileUpload() {
        const uploadArea = document.getElementById('resumeUpload');
        const fileInput = document.getElementById('resumeFile');
        
        if (uploadArea && fileInput) {
            uploadArea.addEventListener('click', function() {
                fileInput.click();
            });
            
            uploadArea.addEventListener('dragover', function(e) {
                e.preventDefault();
                this.style.borderColor = 'var(--primary)';
                this.style.background = 'var(--bg-secondary)';
            });
            
            uploadArea.addEventListener('dragleave', function(e) {
                e.preventDefault();
                this.style.borderColor = '';
                this.style.background = '';
            });
            
            uploadArea.addEventListener('drop', function(e) {
                e.preventDefault();
                this.style.borderColor = '';
                this.style.background = '';
                
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    handleFileUpload(files[0]);
                }
            });
            
            fileInput.addEventListener('change', function() {
                if (this.files.length > 0) {
                    handleFileUpload(this.files[0]);
                }
            });
        }
        
        function handleFileUpload(file) {
            // Validate file type
            const validTypes = ['application/pdf', 'application/msword', 
                               'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
            
            if (!validTypes.includes(file.type)) {
                showToast('Please upload a PDF or Word document', 'error');
                return;
            }
            
            // Show uploaded file
            const uploadedFile = uploadArea.nextElementSibling;
            if (uploadedFile) {
                uploadedFile.style.display = 'flex';
                uploadedFile.querySelector('span').textContent = file.name;
            }
            
            showToast('Resume uploaded successfully!');
        }
    }
    
    // Toast Notifications
    function showToast(message, type = 'success') {
        const toast = document.getElementById('toast');
        const toastMessage = toast.querySelector('.toast-message');
        const toastIcon = toast.querySelector('i');
        
        // Update message
        toastMessage.textContent = message;
        
        // Update icon based on type
        toastIcon.className = '';
        switch(type) {
            case 'success':
                toastIcon.className = 'fas fa-check-circle';
                break;
            case 'error':
                toastIcon.className = 'fas fa-exclamation-circle';
                break;
            case 'warning':
                toastIcon.className = 'fas fa-exclamation-triangle';
                break;
            case 'info':
                toastIcon.className = 'fas fa-info-circle';
                break;
        }
        
        // Show toast
        toast.classList.add('show');
        
        // Hide after 3 seconds
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }
    
    // Tooltips
    function initTooltips() {
        const tooltipElements = document.querySelectorAll('[title]');
        
        tooltipElements.forEach(element => {
            const title = element.getAttribute('title');
            element.removeAttribute('title');
            element.dataset.tooltip = title;
        });
    }
    
    // Table Sorting
    const tables = document.querySelectorAll('.data-table');
    tables.forEach(table => {
        const headers = table.querySelectorAll('th');
        headers.forEach((header, index) => {
            header.style.cursor = 'pointer';
            header.addEventListener('click', () => {
                sortTable(table, index);
            });
        });
    });
    
    function sortTable(table, column) {
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        // Toggle sort direction
        const isAscending = table.dataset.sortColumn == column && 
                           table.dataset.sortDirection === 'asc';
        
        table.dataset.sortColumn = column;
        table.dataset.sortDirection = isAscending ? 'desc' : 'asc';
        
        // Sort rows
        rows.sort((a, b) => {
            const aValue = a.cells[column].textContent.trim();
            const bValue = b.cells[column].textContent.trim();
            
            // Check if numeric
            const aNum = parseFloat(aValue);
            const bNum = parseFloat(bValue);
            
            if (!isNaN(aNum) && !isNaN(bNum)) {
                return isAscending ? bNum - aNum : aNum - bNum;
            }
            
            // String comparison
            if (isAscending) {
                return bValue.localeCompare(aValue);
            } else {
                return aValue.localeCompare(bValue);
            }
        });
        
        // Re-append sorted rows
        rows.forEach(row => tbody.appendChild(row));
    }
    
    // Filter Chips
    const filterChips = document.querySelectorAll('.filter-chip');
    filterChips.forEach(chip => {
        chip.addEventListener('click', function() {
            // Toggle active state
            if (this.classList.contains('active')) {
                this.classList.remove('active');
            } else {
                // Remove active from others if not multi-select
                filterChips.forEach(c => c.classList.remove('active'));
                this.classList.add('active');
            }
            
            // Apply filter logic here
            filterJobs(this.textContent);
        });
    });
    
    function filterJobs(filterType) {
        // Implement filtering logic based on filter type
        console.log('Filtering by:', filterType);
    }
    
    // Tags Input
    const tagsInputs = document.querySelectorAll('.tags-input');
    tagsInputs.forEach(tagsInput => {
        const input = tagsInput.querySelector('input');
        
        if (input) {
            input.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' || e.key === ',') {
                    e.preventDefault();
                    const value = this.value.trim();
                    
                    if (value) {
                        addTag(tagsInput, value);
                        this.value = '';
                    }
                }
            });
        }
        
        // Remove tag on click
        tagsInput.addEventListener('click', function(e) {
            if (e.target.classList.contains('fa-times')) {
                e.target.parentElement.remove();
            }
        });
    });
    
    function addTag(container, text) {
        const tag = document.createElement('span');
        tag.className = 'tag';
        tag.innerHTML = `${text} <i class="fas fa-times"></i>`;
        
        const input = container.querySelector('input');
        container.insertBefore(tag, input);
    }
    
    // Action Buttons
    document.addEventListener('click', function(e) {
        // Save job button
        if (e.target.closest('.icon-btn[title="Save"]')) {
            e.preventDefault();
            const button = e.target.closest('.icon-btn');
            button.classList.toggle('active');
            
            if (button.classList.contains('active')) {
                showToast('Job saved successfully!');
            } else {
                showToast('Job removed from saved list');
            }
        }
        
        // Apply button
        if (e.target.closest('.icon-btn[title="Apply"]')) {
            e.preventDefault();
            const button = e.target.closest('.icon-btn');
            
            // Open job URL in new tab
            window.open('https://www.linkedin.com/jobs', '_blank');
            
            // Update button state
            button.innerHTML = '<i class="fas fa-check"></i>';
            button.disabled = true;
            button.title = 'Already Applied';
            
            // Update status badge
            const row = button.closest('tr');
            if (row) {
                const statusBadge = row.querySelector('.status-badge');
                statusBadge.className = 'status-badge applied';
                statusBadge.textContent = 'Applied';
            }
            
            showToast('Redirecting to LinkedIn...');
        }
    });
    
    // Settings Form
    const settingsForms = document.querySelectorAll('.settings-form');
    settingsForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Save settings to localStorage
            const formData = new FormData(form);
            const settings = {};
            
            for (let [key, value] of formData.entries()) {
                settings[key] = value;
            }
            
            localStorage.setItem('dashboardSettings', JSON.stringify(settings));
            showToast('Settings saved successfully!');
        });
    });
    
    // Export functionality
    const exportButton = document.querySelector('.btn:has(i.fa-download)');
    if (exportButton) {
        exportButton.addEventListener('click', function() {
            exportToSheets();
        });
    }
    
    function exportToSheets() {
        showToast('Exporting to Google Sheets...');
        
        // Simulate export process
        setTimeout(() => {
            showToast('Successfully exported 42 jobs to Google Sheets!');
        }, 2000);
    }
    
    // Profile dropdown
    const profileBtn = document.querySelector('.profile-btn');
    if (profileBtn) {
        profileBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            // Toggle dropdown menu (implement dropdown menu as needed)
        });
    }
    
    // Initialize any remaining interactive elements
    initProgressBars();
    initNotifications();
    
    function initProgressBars() {
        const progressBars = document.querySelectorAll('.skill-fill');
        progressBars.forEach(bar => {
            const width = bar.style.width;
            bar.style.width = '0';
            setTimeout(() => {
                bar.style.width = width;
            }, 100);
        });
    }
    
    function initNotifications() {
        const notificationBtn = document.querySelector('.notification-btn');
        if (notificationBtn) {
            notificationBtn.addEventListener('click', function() {
                showToast('No new notifications');
            });
        }
    }
    
    // Make showToast available globally
    window.showToast = showToast;
});

// Utility functions
function formatDate(date) {
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    }).format(date);
}

function formatNumber(num) {
    return new Intl.NumberFormat('en-US').format(num);
}