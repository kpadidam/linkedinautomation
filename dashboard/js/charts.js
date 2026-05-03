// Chart.js Configuration and Initialization
document.addEventListener('DOMContentLoaded', function() {
    
    // Wait a bit for the DOM to fully render
    setTimeout(() => {
        // Chart default configuration
        if (typeof Chart !== 'undefined') {
            Chart.defaults.font.family = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
            Chart.defaults.color = getComputedStyle(document.documentElement).getPropertyValue('--text-secondary');
            
            // Initialize all charts
            initMatchesChart();
            initKeywordsChart();
            initDailyJobsChart();
            initTopCompaniesChart();
            initMatchTrendChart();
        } else {
            console.error('Chart.js not loaded');
        }
    }, 100);
    
    // Update charts on theme change
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            setTimeout(() => {
                updateChartColors();
            }, 100);
        });
    }
    
    // Job Matches Over Time Chart
    function initMatchesChart() {
        const ctx = document.getElementById('matchesChart');
        if (!ctx) {
            console.log('matchesChart canvas not found');
            return;
        }
        
        // Set canvas dimensions
        ctx.height = 300;
        
        const matchesChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: getLast7Days(),
                datasets: [{
                    label: 'High Match (>80%)',
                    data: [12, 19, 15, 25, 22, 30, 28],
                    borderColor: '#22C55E',
                    backgroundColor: 'rgba(34, 197, 94, 0.1)',
                    tension: 0.4,
                    fill: true
                }, {
                    label: 'Medium Match (50-80%)',
                    data: [25, 30, 28, 32, 35, 40, 38],
                    borderColor: '#F59E0B',
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    tension: 0.4,
                    fill: true
                }, {
                    label: 'Low Match (<50%)',
                    data: [8, 10, 7, 12, 10, 15, 12],
                    borderColor: '#EF4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 15,
                            usePointStyle: true
                        }
                    },
                    tooltip: {
                        backgroundColor: getComputedStyle(document.documentElement)
                            .getPropertyValue('--bg-primary'),
                        titleColor: getComputedStyle(document.documentElement)
                            .getPropertyValue('--text-primary'),
                        bodyColor: getComputedStyle(document.documentElement)
                            .getPropertyValue('--text-secondary'),
                        borderColor: getComputedStyle(document.documentElement)
                            .getPropertyValue('--border'),
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 8,
                        displayColors: true,
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: getComputedStyle(document.documentElement)
                                .getPropertyValue('--text-muted')
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: getComputedStyle(document.documentElement)
                                .getPropertyValue('--border-light'),
                            drawBorder: false
                        },
                        ticks: {
                            color: getComputedStyle(document.documentElement)
                                .getPropertyValue('--text-muted'),
                            callback: function(value) {
                                return value + ' jobs';
                            }
                        }
                    }
                }
            }
        });
        
        // Store chart instance for updates
        window.matchesChart = matchesChart;
    }
    
    // Top Keywords Pie Chart
    function initKeywordsChart() {
        const ctx = document.getElementById('keywordsChart');
        if (!ctx) return;
        
        const keywordsChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Python', 'JavaScript', 'React', 'AWS', 'Docker', 'Machine Learning'],
                datasets: [{
                    data: [30, 25, 20, 15, 8, 12],
                    backgroundColor: [
                        '#2563EB',
                        '#3B82F6',
                        '#22C55E',
                        '#F59E0B',
                        '#A855F7',
                        '#06B6D4'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            padding: 10,
                            usePointStyle: true,
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: getComputedStyle(document.documentElement)
                            .getPropertyValue('--bg-primary'),
                        titleColor: getComputedStyle(document.documentElement)
                            .getPropertyValue('--text-primary'),
                        bodyColor: getComputedStyle(document.documentElement)
                            .getPropertyValue('--text-secondary'),
                        borderColor: getComputedStyle(document.documentElement)
                            .getPropertyValue('--border'),
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 8,
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${label}: ${percentage}%`;
                            }
                        }
                    }
                }
            }
        });
        
        window.keywordsChart = keywordsChart;
    }
    
    // Daily Jobs Chart (Statistics Page)
    function initDailyJobsChart() {
        const ctx = document.getElementById('dailyJobsChart');
        if (!ctx) return;
        
        const dailyJobsChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: getLast30Days(),
                datasets: [{
                    label: 'Jobs Scraped',
                    data: generateRandomData(30, 20, 100),
                    backgroundColor: '#2563EB',
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: getComputedStyle(document.documentElement)
                            .getPropertyValue('--bg-primary'),
                        titleColor: getComputedStyle(document.documentElement)
                            .getPropertyValue('--text-primary'),
                        bodyColor: getComputedStyle(document.documentElement)
                            .getPropertyValue('--text-secondary'),
                        borderColor: getComputedStyle(document.documentElement)
                            .getPropertyValue('--border'),
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 8
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: getComputedStyle(document.documentElement)
                                .getPropertyValue('--text-muted'),
                            maxRotation: 45,
                            minRotation: 45,
                            autoSkip: true,
                            maxTicksLimit: 10
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: getComputedStyle(document.documentElement)
                                .getPropertyValue('--border-light'),
                            drawBorder: false
                        },
                        ticks: {
                            color: getComputedStyle(document.documentElement)
                                .getPropertyValue('--text-muted')
                        }
                    }
                }
            }
        });
        
        window.dailyJobsChart = dailyJobsChart;
    }
    
    // Top Companies Chart
    function initTopCompaniesChart() {
        const ctx = document.getElementById('topCompaniesChart');
        if (!ctx) return;
        
        const topCompaniesChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Google', 'Microsoft', 'Amazon', 'Apple', 'Meta', 'Netflix', 'Tesla', 'Spotify'],
                datasets: [{
                    label: 'Job Postings',
                    data: [45, 38, 35, 32, 28, 22, 18, 15],
                    backgroundColor: [
                        '#2563EB',
                        '#3B82F6',
                        '#22C55E',
                        '#F59E0B',
                        '#A855F7',
                        '#06B6D4',
                        '#EF4444',
                        '#10B981'
                    ],
                    borderRadius: 6
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: getComputedStyle(document.documentElement)
                            .getPropertyValue('--bg-primary'),
                        titleColor: getComputedStyle(document.documentElement)
                            .getPropertyValue('--text-primary'),
                        bodyColor: getComputedStyle(document.documentElement)
                            .getPropertyValue('--text-secondary'),
                        borderColor: getComputedStyle(document.documentElement)
                            .getPropertyValue('--border'),
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 8
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: {
                            color: getComputedStyle(document.documentElement)
                                .getPropertyValue('--border-light'),
                            drawBorder: false
                        },
                        ticks: {
                            color: getComputedStyle(document.documentElement)
                                .getPropertyValue('--text-muted')
                        }
                    },
                    y: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: getComputedStyle(document.documentElement)
                                .getPropertyValue('--text-secondary')
                        }
                    }
                }
            }
        });
        
        window.topCompaniesChart = topCompaniesChart;
    }
    
    // Match Trend Chart
    function initMatchTrendChart() {
        const ctx = document.getElementById('matchTrendChart');
        if (!ctx) return;
        
        const matchTrendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: getLast7Days(),
                datasets: [{
                    label: 'Average Match Score',
                    data: [72, 75, 73, 78, 76, 80, 82],
                    borderColor: '#2563EB',
                    backgroundColor: 'rgba(37, 99, 235, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointRadius: 6,
                    pointHoverRadius: 8,
                    pointBackgroundColor: '#2563EB',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: getComputedStyle(document.documentElement)
                            .getPropertyValue('--bg-primary'),
                        titleColor: getComputedStyle(document.documentElement)
                            .getPropertyValue('--text-primary'),
                        bodyColor: getComputedStyle(document.documentElement)
                            .getPropertyValue('--text-secondary'),
                        borderColor: getComputedStyle(document.documentElement)
                            .getPropertyValue('--border'),
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 8,
                        callbacks: {
                            label: function(context) {
                                return `Match Score: ${context.parsed.y}%`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: getComputedStyle(document.documentElement)
                                .getPropertyValue('--text-muted')
                        }
                    },
                    y: {
                        beginAtZero: false,
                        min: 0,
                        max: 100,
                        grid: {
                            color: getComputedStyle(document.documentElement)
                                .getPropertyValue('--border-light'),
                            drawBorder: false
                        },
                        ticks: {
                            color: getComputedStyle(document.documentElement)
                                .getPropertyValue('--text-muted'),
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                }
            }
        });
        
        window.matchTrendChart = matchTrendChart;
    }
    
    // Helper function to get last 7 days
    function getLast7Days() {
        const days = [];
        const today = new Date();
        
        for (let i = 6; i >= 0; i--) {
            const date = new Date(today);
            date.setDate(today.getDate() - i);
            days.push(date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }));
        }
        
        return days;
    }
    
    // Helper function to get last 30 days
    function getLast30Days() {
        const days = [];
        const today = new Date();
        
        for (let i = 29; i >= 0; i--) {
            const date = new Date(today);
            date.setDate(today.getDate() - i);
            days.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
        }
        
        return days;
    }
    
    // Generate random data for demo
    function generateRandomData(count, min, max) {
        const data = [];
        for (let i = 0; i < count; i++) {
            data.push(Math.floor(Math.random() * (max - min + 1)) + min);
        }
        return data;
    }
    
    // Update chart colors when theme changes
    function updateChartColors() {
        const charts = [
            window.matchesChart,
            window.keywordsChart,
            window.dailyJobsChart,
            window.topCompaniesChart,
            window.matchTrendChart
        ];
        
        charts.forEach(chart => {
            if (chart) {
                // Update default colors
                Chart.defaults.color = getComputedStyle(document.documentElement)
                    .getPropertyValue('--text-secondary');
                
                // Update scales
                if (chart.options.scales) {
                    if (chart.options.scales.x) {
                        chart.options.scales.x.ticks.color = getComputedStyle(document.documentElement)
                            .getPropertyValue('--text-muted');
                        if (chart.options.scales.x.grid) {
                            chart.options.scales.x.grid.color = getComputedStyle(document.documentElement)
                                .getPropertyValue('--border-light');
                        }
                    }
                    if (chart.options.scales.y) {
                        chart.options.scales.y.ticks.color = getComputedStyle(document.documentElement)
                            .getPropertyValue('--text-muted');
                        if (chart.options.scales.y.grid) {
                            chart.options.scales.y.grid.color = getComputedStyle(document.documentElement)
                                .getPropertyValue('--border-light');
                        }
                    }
                }
                
                // Update tooltip
                if (chart.options.plugins && chart.options.plugins.tooltip) {
                    chart.options.plugins.tooltip.backgroundColor = getComputedStyle(document.documentElement)
                        .getPropertyValue('--bg-primary');
                    chart.options.plugins.tooltip.titleColor = getComputedStyle(document.documentElement)
                        .getPropertyValue('--text-primary');
                    chart.options.plugins.tooltip.bodyColor = getComputedStyle(document.documentElement)
                        .getPropertyValue('--text-secondary');
                    chart.options.plugins.tooltip.borderColor = getComputedStyle(document.documentElement)
                        .getPropertyValue('--border');
                }
                
                chart.update();
            }
        });
    }
    
    // Simulate real-time updates
    setInterval(() => {
        if (window.matchesChart) {
            // Update with new data point
            const datasets = window.matchesChart.data.datasets;
            datasets.forEach(dataset => {
                // Remove first point and add new one
                dataset.data.shift();
                dataset.data.push(Math.floor(Math.random() * 40) + 10);
            });
            
            // Update labels
            window.matchesChart.data.labels = getLast7Days();
            window.matchesChart.update('none'); // No animation for real-time updates
        }
    }, 10000); // Update every 10 seconds
});