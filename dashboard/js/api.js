// API Integration Layer
class JobAutomatorAPI {
    constructor() {
        // Base URL for API - update with your actual backend URL
        this.baseURL = 'http://localhost:8000/api';
        
        // Initialize WebSocket for real-time updates
        this.initWebSocket();
        
        // Cache for API responses
        this.cache = new Map();
        this.cacheTimeout = 5 * 60 * 1000; // 5 minutes
    }
    
    // WebSocket initialization for real-time updates
    initWebSocket() {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsURL = `${wsProtocol}//${window.location.hostname}:8000/ws`;
        
        try {
            this.ws = new WebSocket(wsURL);
            
            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.updateConnectionStatus(true);
            };
            
            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleRealtimeUpdate(data);
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateConnectionStatus(false);
            };
            
            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.updateConnectionStatus(false);
                // Attempt to reconnect after 5 seconds
                setTimeout(() => this.initWebSocket(), 5000);
            };
        } catch (error) {
            console.error('Failed to initialize WebSocket:', error);
        }
    }
    
    // Update connection status indicator
    updateConnectionStatus(isConnected) {
        const statusDot = document.querySelector('.status-dot');
        const statusText = document.querySelector('.status-text');
        
        if (statusDot) {
            statusDot.classList.toggle('active', isConnected);
        }
        
        if (statusText) {
            statusText.textContent = isConnected ? 'Sync Active' : 'Sync Offline';
        }
    }
    
    // Handle real-time updates from WebSocket
    handleRealtimeUpdate(data) {
        switch (data.type) {
            case 'job_found':
                this.handleNewJob(data.job);
                break;
            case 'search_progress':
                this.updateSearchProgress(data.progress);
                break;
            case 'search_complete':
                this.handleSearchComplete(data.results);
                break;
            case 'sync_complete':
                window.showToast('Google Sheets sync completed!');
                break;
            default:
                console.log('Unknown update type:', data.type);
        }
    }
    
    // Fetch wrapper with error handling
    async fetchAPI(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        
        // Check cache first
        const cacheKey = `${endpoint}_${JSON.stringify(options)}`;
        if (options.method === 'GET' && this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < this.cacheTimeout) {
                return cached.data;
            }
        }
        
        try {
            const response = await fetch(url, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                }
            });
            
            if (!response.ok) {
                throw new Error(`API Error: ${response.status} ${response.statusText}`);
            }
            
            const data = await response.json();
            
            // Cache GET requests
            if (options.method === 'GET') {
                this.cache.set(cacheKey, {
                    data: data,
                    timestamp: Date.now()
                });
            }
            
            return data;
        } catch (error) {
            console.error('API Request failed:', error);
            throw error;
        }
    }
    
    // Job Search API
    async searchJobs(searchParams) {
        try {
            // For demo purposes, return mock data
            // Replace with actual API call
            return this.getMockSearchResults(searchParams);
            
            // Actual API call:
            // return await this.fetchAPI('/jobs/search', {
            //     method: 'POST',
            //     body: JSON.stringify(searchParams)
            // });
        } catch (error) {
            window.showToast('Failed to search jobs', 'error');
            throw error;
        }
    }
    
    // Get job details
    async getJobDetails(jobId) {
        try {
            // Mock data for demo
            return this.getMockJobDetails(jobId);
            
            // Actual API call:
            // return await this.fetchAPI(`/jobs/${jobId}`);
        } catch (error) {
            window.showToast('Failed to load job details', 'error');
            throw error;
        }
    }
    
    // Save job
    async saveJob(jobId) {
        try {
            // Mock response
            return { success: true, message: 'Job saved successfully' };
            
            // Actual API call:
            // return await this.fetchAPI(`/jobs/${jobId}/save`, {
            //     method: 'POST'
            // });
        } catch (error) {
            window.showToast('Failed to save job', 'error');
            throw error;
        }
    }
    
    // Mark job as applied
    async markAsApplied(jobId) {
        try {
            // Mock response
            return { success: true, message: 'Job marked as applied' };
            
            // Actual API call:
            // return await this.fetchAPI(`/jobs/${jobId}/apply`, {
            //     method: 'POST'
            // });
        } catch (error) {
            window.showToast('Failed to update job status', 'error');
            throw error;
        }
    }
    
    // Get dashboard statistics
    async getDashboardStats() {
        try {
            // Mock data for demo
            return {
                totalJobs: 1234,
                activeSearches: 5,
                averageMatch: 78,
                sheetssynced: 42,
                recentActivity: this.getMockRecentActivity()
            };
            
            // Actual API call:
            // return await this.fetchAPI('/dashboard/stats');
        } catch (error) {
            console.error('Failed to load dashboard stats:', error);
            // Return default values on error
            return {
                totalJobs: 0,
                activeSearches: 0,
                averageMatch: 0,
                sheetsSynced: 0,
                recentActivity: []
            };
        }
    }
    
    // Upload resume
    async uploadResume(file) {
        try {
            const formData = new FormData();
            formData.append('resume', file);
            
            // Mock response
            return {
                success: true,
                analysis: {
                    skills: ['Python', 'JavaScript', 'React', 'AWS'],
                    experience: '5 years',
                    matchingKeywords: ['Full Stack', 'Developer', 'Engineer']
                }
            };
            
            // Actual API call:
            // return await fetch(`${this.baseURL}/profile/resume`, {
            //     method: 'POST',
            //     body: formData
            // }).then(res => res.json());
        } catch (error) {
            window.showToast('Failed to upload resume', 'error');
            throw error;
        }
    }
    
    // Export to Google Sheets
    async exportToSheets(jobs) {
        try {
            // Mock response
            return {
                success: true,
                sheetsUrl: 'https://docs.google.com/spreadsheets/d/example',
                jobsExported: jobs.length
            };
            
            // Actual API call:
            // return await this.fetchAPI('/export/sheets', {
            //     method: 'POST',
            //     body: JSON.stringify({ jobs })
            // });
        } catch (error) {
            window.showToast('Failed to export to Google Sheets', 'error');
            throw error;
        }
    }
    
    // Save settings
    async saveSettings(settings) {
        try {
            // Mock response
            return { success: true, message: 'Settings saved' };
            
            // Actual API call:
            // return await this.fetchAPI('/settings', {
            //     method: 'PUT',
            //     body: JSON.stringify(settings)
            // });
        } catch (error) {
            window.showToast('Failed to save settings', 'error');
            throw error;
        }
    }
    
    // Handle new job from real-time update
    handleNewJob(job) {
        // Add to table or update UI
        const table = document.querySelector('.results-table tbody');
        if (table) {
            const row = this.createJobRow(job);
            table.insertBefore(row, table.firstChild);
            
            // Highlight new row
            row.style.animation = 'fadeIn 0.5s ease';
            
            // Show notification
            window.showToast(`New job found: ${job.title} at ${job.company}`);
        }
    }
    
    // Update search progress
    updateSearchProgress(progress) {
        const progressBar = document.querySelector('.progress-fill');
        const progressText = document.getElementById('progressPercent');
        
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }
        
        if (progressText) {
            progressText.textContent = Math.round(progress);
        }
    }
    
    // Handle search complete
    handleSearchComplete(results) {
        window.showToast(`Search completed! Found ${results.count} matching jobs.`);
        
        // Update results table
        this.updateResultsTable(results.jobs);
        
        // Hide progress bar
        const progressContainer = document.getElementById('searchProgress');
        if (progressContainer) {
            progressContainer.style.display = 'none';
        }
        
        // Enable search button
        const searchBtn = document.querySelector('#jobSearchForm button[type="submit"]');
        if (searchBtn) {
            searchBtn.disabled = false;
        }
    }
    
    // Create job row for table
    createJobRow(job) {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <strong>${job.title}</strong>
                <span class="text-muted">Posted ${job.postedDate}</span>
            </td>
            <td>${job.company}</td>
            <td>${job.location}</td>
            <td>
                <div class="match-score ${this.getMatchClass(job.matchScore)}">${job.matchScore}%</div>
            </td>
            <td>
                <span class="status-badge ${job.status}">${job.status}</span>
            </td>
            <td>
                <div class="action-buttons">
                    <button class="icon-btn" title="View Details" data-job-id="${job.id}">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="icon-btn" title="Save" data-job-id="${job.id}">
                        <i class="fas fa-bookmark"></i>
                    </button>
                    <button class="icon-btn" title="Apply" data-job-id="${job.id}">
                        <i class="fas fa-paper-plane"></i>
                    </button>
                </div>
            </td>
        `;
        return row;
    }
    
    // Get match score class
    getMatchClass(score) {
        if (score >= 80) return 'high';
        if (score >= 50) return 'medium';
        return 'low';
    }
    
    // Update results table
    updateResultsTable(jobs) {
        const tbody = document.querySelector('.results-table tbody');
        if (!tbody) return;
        
        // Clear existing rows
        tbody.innerHTML = '';
        
        // Add new rows
        jobs.forEach(job => {
            const row = this.createJobRow(job);
            tbody.appendChild(row);
        });
    }
    
    // Mock data generators for demo
    getMockSearchResults(params) {
        const jobs = [];
        const companies = ['Google', 'Microsoft', 'Amazon', 'Apple', 'Meta', 'Netflix', 'Spotify', 'Adobe'];
        const titles = ['Senior Developer', 'Software Engineer', 'Full Stack Developer', 'Data Engineer', 'DevOps Engineer'];
        const locations = ['San Francisco, CA', 'New York, NY', 'Seattle, WA', 'Austin, TX', 'Remote'];
        
        for (let i = 0; i < 15; i++) {
            jobs.push({
                id: `job_${Date.now()}_${i}`,
                title: titles[Math.floor(Math.random() * titles.length)],
                company: companies[Math.floor(Math.random() * companies.length)],
                location: locations[Math.floor(Math.random() * locations.length)],
                matchScore: Math.floor(Math.random() * 40) + 60,
                status: 'new',
                postedDate: `${Math.floor(Math.random() * 7) + 1} days ago`,
                description: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit...',
                salary: `$${Math.floor(Math.random() * 50) + 100}k - $${Math.floor(Math.random() * 50) + 150}k`,
                applicants: Math.floor(Math.random() * 200) + 10
            });
        }
        
        return {
            success: true,
            count: jobs.length,
            jobs: jobs
        };
    }
    
    getMockJobDetails(jobId) {
        return {
            id: jobId,
            title: 'Senior Python Developer',
            company: 'Tech Corp',
            location: 'San Francisco, CA',
            salary: '$150k - $200k',
            applicants: '45 applicants',
            description: `
                We are looking for a talented Senior Python Developer to join our growing team.
                You will be responsible for developing and maintaining our core backend services,
                working with modern technologies and frameworks.
                
                Requirements:
                • 5+ years of Python development experience
                • Strong knowledge of Django or Flask
                • Experience with PostgreSQL and Redis
                • Familiarity with AWS services
                • Excellent problem-solving skills
            `,
            skills: ['Python', 'Django', 'PostgreSQL', 'AWS', 'Docker', 'Kubernetes'],
            matchScore: 92,
            recommendations: [
                'Strong match with your Python expertise',
                'Consider highlighting your Django projects',
                'AWS experience is a plus'
            ],
            interviewTips: [
                'Prepare examples of scalable Python applications',
                'Review Django best practices',
                'Be ready to discuss cloud architecture'
            ]
        };
    }
    
    getMockRecentActivity() {
        return [
            {
                type: 'success',
                title: 'Senior Developer at Tech Corp',
                description: '95% match',
                time: '2 hours ago'
            },
            {
                type: 'info',
                title: 'Synced 23 jobs to Google Sheets',
                description: '',
                time: '5 hours ago'
            },
            {
                type: 'warning',
                title: 'New high-match job found',
                description: 'Product Manager at StartupXYZ',
                time: '1 day ago'
            }
        ];
    }
}

// Initialize API instance
const api = new JobAutomatorAPI();

// Export for use in other modules
window.JobAutomatorAPI = api;