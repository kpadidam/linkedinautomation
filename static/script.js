// LinkedIn Job Automation - JavaScript

const API_URL = '/api';

// Tab Management
function showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active class from all buttons
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(`${tabName}-tab`).classList.add('active');
    
    // Add active class to clicked button
    event.target.classList.add('active');
    
    // Load tab-specific data
    if (tabName === 'jobs') {
        loadJobs();
    } else if (tabName === 'profile') {
        loadProfile();
    } else if (tabName === 'statistics') {
        loadStatistics();
    }
}

// Job Search
document.getElementById('search-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const searchData = {
        keywords: formData.get('keywords'),
        location: formData.get('location'),
        job_type: formData.get('job_type') || null,
        experience_level: formData.get('experience_level') || null,
        posted_within: formData.get('posted_within'),
        max_results: parseInt(formData.get('max_results')),
        remote: formData.get('remote') === 'on',
        enable_matching: formData.get('enable_matching') === 'on',
        save_to_sheets: formData.get('save_to_sheets') === 'on'
    };
    
    try {
        showStatus('search-status', 'Starting job search...', 'warning');
        document.getElementById('search-results').style.display = 'block';
        
        const response = await fetch(`${API_URL}/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(searchData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showStatus('search-status', result.message, 'success');
            
            // Show Google Sheets link if available
            if (result.sheet_url) {
                const sheetLink = document.getElementById('sheet-link');
                sheetLink.style.display = 'block';
                sheetLink.querySelector('a').href = result.sheet_url;
            }
            
            // Start monitoring search progress
            monitorSearchProgress(result.search_id);
        } else {
            showStatus('search-status', `Error: ${result.detail}`, 'error');
        }
    } catch (error) {
        showStatus('search-status', `Error: ${error.message}`, 'error');
    }
});

// Monitor Search Progress
async function monitorSearchProgress(searchId) {
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    
    const checkInterval = setInterval(async () => {
        try {
            const response = await fetch(`${API_URL}/search/${searchId}`);
            const searchStatus = await response.json();
            
            if (searchStatus.status === 'completed') {
                clearInterval(checkInterval);
                progressFill.style.width = '100%';
                progressText.textContent = `Search completed! Found ${searchStatus.jobs_scraped} jobs, ${searchStatus.jobs_matched} matched.`;
                
                // Refresh jobs list
                loadJobs();
            } else if (searchStatus.status === 'failed') {
                clearInterval(checkInterval);
                progressText.textContent = `Search failed: ${searchStatus.error_message}`;
                showStatus('search-status', 'Search failed', 'error');
            } else {
                // Update progress
                const progress = searchStatus.jobs_scraped / searchStatus.total_results * 100;
                progressFill.style.width = `${progress}%`;
                progressText.textContent = `Processing... ${searchStatus.jobs_scraped} of ${searchStatus.total_results} jobs`;
            }
        } catch (error) {
            clearInterval(checkInterval);
            progressText.textContent = 'Error checking search status';
        }
    }, 2000); // Check every 2 seconds
}

// Load Jobs
async function loadJobs() {
    const jobsList = document.getElementById('jobs-list');
    jobsList.innerHTML = '<div class="spinner"></div>';
    
    const statusFilter = document.getElementById('status-filter').value;
    const minScore = document.getElementById('min-score-filter').value;
    
    let url = `${API_URL}/jobs?limit=100`;
    if (statusFilter) url += `&status=${statusFilter}`;
    if (minScore) url += `&min_score=${minScore}`;
    
    try {
        const response = await fetch(url);
        const jobs = await response.json();
        
        if (jobs.length === 0) {
            jobsList.innerHTML = '<p>No jobs found. Start a new search to discover opportunities!</p>';
            return;
        }
        
        jobsList.innerHTML = jobs.map(job => createJobCard(job)).join('');
    } catch (error) {
        jobsList.innerHTML = `<p class="error">Error loading jobs: ${error.message}</p>`;
    }
}

// Filter Jobs
function filterJobs() {
    loadJobs();
}

// Create Job Card
function createJobCard(job) {
    const matchClass = job.resume_match_score >= 80 ? 'match-high' : 
                       job.resume_match_score >= 60 ? 'match-medium' : 'match-low';
    
    const matchScore = job.resume_match_score ? 
        `<span class="job-match ${matchClass}">${job.resume_match_score.toFixed(1)}% Match</span>` : '';
    
    const keywords = job.keywords ? job.keywords.slice(0, 5).map(k => 
        `<span class="tag">${k}</span>`).join('') : '';
    
    return `
        <div class="job-card" onclick="showJobDetails('${job.job_id}')">
            <div class="job-header">
                <div>
                    <div class="job-title">${job.title}</div>
                    <div class="job-company">${job.company}</div>
                    <div class="job-location">${job.location}</div>
                </div>
                ${matchScore}
            </div>
            <div class="job-details">
                <p>${job.job_type || 'Full-time'} • ${job.posted_date || 'Recently posted'}</p>
                <div class="job-tags">${keywords}</div>
            </div>
        </div>
    `;
}

// Show Job Details
async function showJobDetails(jobId) {
    const modal = document.getElementById('job-modal');
    const jobDetails = document.getElementById('job-details');
    
    jobDetails.innerHTML = '<div class="spinner"></div>';
    modal.style.display = 'block';
    
    try {
        const response = await fetch(`${API_URL}/jobs/${jobId}`);
        const job = await response.json();
        
        jobDetails.innerHTML = `
            <h2>${job.title}</h2>
            <h3>${job.company} - ${job.location}</h3>
            
            <div class="job-meta">
                <p><strong>Type:</strong> ${job.job_type || 'Not specified'}</p>
                <p><strong>Experience:</strong> ${job.experience_level || 'Not specified'}</p>
                <p><strong>Salary:</strong> ${job.salary_range || 'Not specified'}</p>
                <p><strong>Posted:</strong> ${job.posted_date || 'Recently'}</p>
                <p><strong>Applicants:</strong> ${job.applicants_count || 'Not available'}</p>
                ${job.resume_match_score ? 
                    `<p><strong>Match Score:</strong> ${job.resume_match_score.toFixed(1)}%</p>` : ''}
            </div>
            
            <div class="job-description">
                <h4>Description</h4>
                <p>${job.description || 'No description available'}</p>
            </div>
            
            ${job.requirements && job.requirements.length > 0 ? `
                <div class="job-requirements">
                    <h4>Requirements</h4>
                    <ul>${job.requirements.map(r => `<li>${r}</li>`).join('')}</ul>
                </div>
            ` : ''}
            
            ${job.url ? `
                <div class="job-actions">
                    <a href="${job.url}" target="_blank" class="btn btn-primary">View on LinkedIn</a>
                    <button onclick="updateJobStatus('${job.job_id}', 'saved')" class="btn btn-secondary">Save</button>
                    <button onclick="updateJobStatus('${job.job_id}', 'applied')" class="btn btn-success">Mark as Applied</button>
                </div>
            ` : ''}
        `;
    } catch (error) {
        jobDetails.innerHTML = `<p class="error">Error loading job details: ${error.message}</p>`;
    }
}

// Close Job Modal
function closeJobModal() {
    document.getElementById('job-modal').style.display = 'none';
}

// Update Job Status
async function updateJobStatus(jobId, status) {
    try {
        const response = await fetch(`${API_URL}/jobs/${jobId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ status })
        });
        
        if (response.ok) {
            alert(`Job status updated to ${status}`);
            closeJobModal();
            loadJobs();
        }
    } catch (error) {
        alert(`Error updating job status: ${error.message}`);
    }
}

// Load Profile
async function loadProfile() {
    try {
        const response = await fetch(`${API_URL}/profile`);
        const profile = await response.json();
        
        document.getElementById('profile-name').value = profile.name || '';
        document.getElementById('profile-email').value = profile.email || '';
        document.getElementById('profile-skills').value = profile.skills ? profile.skills.join(', ') : '';
    } catch (error) {
        console.error('Error loading profile:', error);
    }
}

// Update Profile
document.getElementById('profile-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const profileData = {
        name: formData.get('name'),
        email: formData.get('email'),
        skills: formData.get('skills').split(',').map(s => s.trim()).filter(s => s),
        resume_text: formData.get('resume_text')
    };
    
    try {
        const response = await fetch(`${API_URL}/profile`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(profileData)
        });
        
        if (response.ok) {
            showStatus('profile-status', 'Profile updated successfully!', 'success');
        } else {
            showStatus('profile-status', 'Error updating profile', 'error');
        }
    } catch (error) {
        showStatus('profile-status', `Error: ${error.message}`, 'error');
    }
});

// Load Statistics
async function loadStatistics() {
    try {
        const response = await fetch(`${API_URL}/statistics`);
        const stats = await response.json();
        
        document.getElementById('total-jobs').textContent = stats.total_jobs;
        document.getElementById('applied-jobs').textContent = stats.applied_jobs;
        document.getElementById('high-match-jobs').textContent = stats.high_match_jobs;
        document.getElementById('avg-match-score').textContent = `${stats.average_match_score}%`;
        
        // Load recent searches
        const searchesResponse = await fetch(`${API_URL}/searches?limit=5`);
        const searches = await searchesResponse.json();
        
        const searchesList = document.getElementById('recent-searches-list');
        searchesList.innerHTML = searches.map(search => `
            <div class="search-item">
                <div>
                    <span class="search-keywords">${search.keywords}</span> in ${search.location}
                    <div class="search-date">${new Date(search.started_at).toLocaleString()}</div>
                </div>
                <div>
                    <span class="tag">${search.status}</span>
                    <span>${search.jobs_scraped} jobs</span>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

// Create New Sheet
async function createNewSheet() {
    if (!confirm('Create a new Google Sheet for job tracking?')) return;
    
    try {
        const response = await fetch(`${API_URL}/sheets/create`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert(`New sheet created! URL: ${result.sheet_url}`);
            window.open(result.sheet_url, '_blank');
        } else {
            alert(`Error: ${result.detail}`);
        }
    } catch (error) {
        alert(`Error creating sheet: ${error.message}`);
    }
}

// Cleanup Old Data
async function cleanupOldData() {
    const days = prompt('Delete jobs older than how many days? (7-365)', '30');
    if (!days) return;
    
    const daysInt = parseInt(days);
    if (isNaN(daysInt) || daysInt < 7 || daysInt > 365) {
        alert('Please enter a number between 7 and 365');
        return;
    }
    
    if (!confirm(`Delete all jobs older than ${daysInt} days?`)) return;
    
    try {
        const response = await fetch(`${API_URL}/cleanup?days=${daysInt}`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert(result.message);
            loadStatistics();
        } else {
            alert(`Error: ${result.detail}`);
        }
    } catch (error) {
        alert(`Error cleaning up data: ${error.message}`);
    }
}

// Show Status Message
function showStatus(elementId, message, type) {
    const statusElement = document.getElementById(elementId);
    statusElement.textContent = message;
    statusElement.className = `status-message ${type}`;
    statusElement.style.display = 'block';
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        statusElement.style.display = 'none';
    }, 5000);
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('job-modal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Check API health
    fetch(`${API_URL}/health`)
        .then(response => response.json())
        .then(data => {
            console.log('API Status:', data.status);
        })
        .catch(error => {
            console.error('API not available:', error);
            alert('API server is not running. Please start the server first.');
        });
});