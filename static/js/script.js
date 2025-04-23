document.addEventListener('DOMContentLoaded', function() {
    // Theme toggle functionality
    const themeToggle = document.getElementById('theme-toggle');
    const body = document.body;
    
    // Check for saved theme preference or use preferred color scheme
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    // Apply dark mode if saved or preferred
    if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
        body.classList.add('dark-mode');
    }
    
    // Theme toggle button click event
    themeToggle.addEventListener('click', function() {
        // Toggle dark mode class
        body.classList.toggle('dark-mode');
        
        // Save preference
        if (body.classList.contains('dark-mode')) {
            localStorage.setItem('theme', 'dark');
        } else {
            localStorage.setItem('theme', 'light');
        }
        
        // Reinitialize flatpickr to update its theme
        reinitializeFlatpickr();
    });
    
    // Function to reinitialize flatpickr with current theme
    function reinitializeFlatpickr() {
        // Destroy existing instances
        document.querySelectorAll('.flatpickr-input').forEach(input => {
            if (input._flatpickr) {
                input._flatpickr.destroy();
            }
        });
        
        // Reinitialize with current theme
        initializeDatePickers();
        initializeTimePickers();
    }
    
    // Initialize date pickers
    function initializeDatePickers() {
        flatpickr('.date-picker', {
            dateFormat: 'Y/m/d',
            minDate: 'today',
            altInput: true,
            altFormat: 'F j, Y'
        });
        
        // Add date recommendations
        const shutdownDatePicker = document.getElementById('shutdown-date');
        const retireDatePicker = document.getElementById('retire-date');
        
        if (shutdownDatePicker) {
            addDateRecommendations(shutdownDatePicker, 0);
        }
        
        if (retireDatePicker) {
            addDateRecommendations(retireDatePicker, 7);
        }
    }
    
    // Initialize time pickers
    function initializeTimePickers() {
        flatpickr('.time-picker', {
            enableTime: true,
            noCalendar: true,
            dateFormat: 'H:i:S',
            time_24hr: true,
            defaultHour: 20  // Default to 8:00 PM
        });
        
        // Add time recommendations
        const timePickers = document.querySelectorAll('.time-picker');
        timePickers.forEach(picker => {
            // Check if recommendations already exist
            if (!picker.parentNode.querySelector('.time-recommendations')) {
                addTimeRecommendations(picker);
            }
        });
    }
    
    // Initialize date and time pickers
    initializeDatePickers();
    initializeTimePickers();

    // Standard maintenance hour time suggestions
    function addTimeRecommendations(picker) {
        // Standard maintenance hours
        const maintenanceHours = [
            { display: '8:00 PM', value: '20:00:00' },
            { display: '9:00 PM', value: '21:00:00' },
            { display: '10:00 PM', value: '22:00:00' },
            { display: '11:00 PM', value: '23:00:00' }
        ];
        
        const recommendationsDiv = document.createElement('div');
        recommendationsDiv.className = 'time-recommendations';
        
        maintenanceHours.forEach(time => {
            const timeButton = document.createElement('span');
            timeButton.className = 'time-recommendation';
            timeButton.textContent = time.display;
            timeButton.dataset.value = time.value; // Store actual value as data attribute
            timeButton.addEventListener('click', () => {
                const fp = picker._flatpickr;
                fp.setDate(time.value, true);
            });
            recommendationsDiv.appendChild(timeButton);
        });
        
        picker.parentNode.appendChild(recommendationsDiv);
    }

    // Date recommendations (next day, next week, end of month)
    function addDateRecommendations(picker, offset) {
        // Remove existing recommendations if any
        const existingRecommendations = picker.parentNode.querySelector('.date-recommendations');
        if (existingRecommendations) {
            existingRecommendations.remove();
        }
        
        const recommendationsDiv = document.createElement('div');
        recommendationsDiv.className = 'date-recommendations';
        
        // Get today's date
        const today = new Date();
        
        // Next day
        const tomorrow = new Date(today);
        tomorrow.setDate(today.getDate() + 1);
        
        // Next week
        const nextWeek = new Date(today);
        nextWeek.setDate(today.getDate() + 7);
        
        // End of month
        const endOfMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        
        const dateOptions = [
            { label: 'Tomorrow', date: formatDate(addDays(tomorrow, offset)) },
            { label: 'Next Week', date: formatDate(addDays(nextWeek, offset)) },
            { label: 'End of Month', date: formatDate(addDays(endOfMonth, offset)) }
        ];
        
        dateOptions.forEach(option => {
            const dateButton = document.createElement('span');
            dateButton.className = 'date-recommendation';
            dateButton.textContent = option.label;
            dateButton.addEventListener('click', () => {
                const fp = picker._flatpickr;
                fp.setDate(option.date, true);
            });
            recommendationsDiv.appendChild(dateButton);
        });
        
        picker.parentNode.appendChild(recommendationsDiv);
    }

    // DNS Zone management
    const dnsZoneSelect = document.getElementById('dns-zone');
    const customZoneInput = document.getElementById('custom-zone-input');
    const addZoneBtn = document.getElementById('add-zone-btn');
    
    // Load custom zones from localStorage if available
    const loadCustomZones = () => {
        try {
            const customZones = JSON.parse(localStorage.getItem('customDnsZones')) || [];
            customZones.forEach(zone => {
                if (!Array.from(dnsZoneSelect.options).some(option => option.value === zone)) {
                    addZoneToDropdown(zone);
                }
            });
        } catch(e) {
            console.error('Error loading custom zones:', e);
        }
    };
    
    // Add custom zone to dropdown and localStorage
    const addZoneToDropdown = (zone) => {
        // Create new option
        const option = document.createElement('option');
        option.value = zone;
        option.textContent = zone;
        dnsZoneSelect.appendChild(option);
        
        // Select the new option
        dnsZoneSelect.value = zone;
        
        // Save to localStorage
        try {
            let customZones = JSON.parse(localStorage.getItem('customDnsZones')) || [];
            if (!customZones.includes(zone)) {
                customZones.push(zone);
                localStorage.setItem('customDnsZones', JSON.stringify(customZones));
            }
        } catch(e) {
            console.error('Error saving custom zone:', e);
        }
    };
    
    // Add custom zone button click handler
    addZoneBtn.addEventListener('click', () => {
        const zone = customZoneInput.value.trim();
        
        if (!zone) return;
        
        // Basic validation - must be a valid domain
        if (!/^[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.[a-zA-Z]{2,}$/.test(zone)) {
            alert('Please enter a valid domain name (e.g., example.com)');
            return;
        }
        
        // Check if zone already exists in dropdown
        if (Array.from(dnsZoneSelect.options).some(option => option.value === zone)) {
            alert('This DNS zone already exists in the list.');
            dnsZoneSelect.value = zone;
            return;
        }
        
        addZoneToDropdown(zone);
        customZoneInput.value = '';
    });
    
    // Allow adding zone with enter key
    customZoneInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            addZoneBtn.click();
        }
    });
    
    // Load custom zones when page loads
    loadCustomZones();

    // Record names list management
    const recordNameInput = document.getElementById('record-name-input');
    const addRecordBtn = document.getElementById('add-record-btn');
    const recordNamesList = document.getElementById('record-names-list');
    const recordNames = [];

    // Add record name
    addRecordBtn.addEventListener('click', addRecordName);
    recordNameInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            addRecordName();
        }
    });

    function addRecordName() {
        const recordName = recordNameInput.value.trim();
        if (recordName === '') return;
        
        if (recordNames.includes(recordName)) {
            alert('This record name has already been added.');
            return;
        }
        
        recordNames.push(recordName);
        updateRecordNamesList();
        recordNameInput.value = '';
        recordNameInput.focus();
    }

    function removeRecordName(index) {
        recordNames.splice(index, 1);
        updateRecordNamesList();
    }

    function updateRecordNamesList() {
        recordNamesList.innerHTML = '';
        
        if (recordNames.length === 0) {
            recordNamesList.innerHTML = '<li class="list-group-item text-muted">No VMs added yet</li>';
            return;
        }
        
        recordNames.forEach((name, index) => {
            const li = document.createElement('li');
            li.className = 'list-group-item';
            li.innerHTML = `
                ${name}
                <span class="remove-record" data-index="${index}">&times;</span>
            `;
            recordNamesList.appendChild(li);
            
            // Add event listener to remove button
            li.querySelector('.remove-record').addEventListener('click', function() {
                removeRecordName(this.dataset.index);
            });
        });
    }

    // Initialize empty list
    updateRecordNamesList();

    // Form submission
    const form = document.getElementById('retirement-form');
    const submitBtn = document.getElementById('submit-btn');
    const statusModal = new bootstrap.Modal(document.getElementById('statusModal'));
    const statusContent = document.getElementById('status-content');

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (recordNames.length === 0) {
            alert('Please add at least one VM record name.');
            return;
        }
        
        const shutdownDate = document.getElementById('shutdown-date').value;
        const shutdownTime = document.getElementById('shutdown-time').value;
        const retireDate = document.getElementById('retire-date').value;
        const retireTime = document.getElementById('retire-time').value;
        const dnsServer = document.getElementById('dns-server').value;
        const dnsZone = document.getElementById('dns-zone').value;
        
        if (!shutdownDate || !shutdownTime || !retireDate || !retireTime) {
            alert('Please fill in all date and time fields.');
            return;
        }
        
        // Disable button and show loading
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Submitting...';
        
        // Prepare data for API
        const data = {
            record_names: recordNames,
            schedule_shutdown_date: shutdownDate,
            schedule_shutdown_time: shutdownTime,
            schedule_retire_date: retireDate,
            schedule_retire_time: retireTime,
            dns_server: dnsServer,
            dns_zone: dnsZone
        };
        
        // Send to API
        fetch('/api/launch-job', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            submitBtn.disabled = false;
            submitBtn.innerHTML = 'Schedule VM Retirement';
            
            if (data.error) {
                statusContent.innerHTML = `
                    <div class="alert alert-danger">
                        <h4>Error</h4>
                        <p>${data.error}</p>
                    </div>
                `;
            } else {
                statusContent.innerHTML = `
                    <div class="alert alert-success">
                        <h4>Success!</h4>
                        <p>VM retirement job has been scheduled successfully.</p>
                        <p><strong>Job ID:</strong> ${data.job_id || 'N/A'}</p>
                    </div>
                    
                    <p>The following VMs have been scheduled for retirement:</p>
                    <ul>
                        ${recordNames.map(name => `<li>${name}</li>`).join('')}
                    </ul>
                    <p><strong>Shutdown:</strong> ${shutdownDate} at ${shutdownTime}</p>
                    <p><strong>Retirement:</strong> ${retireDate} at ${retireTime}</p>
                    <p><strong>DNS Zone:</strong> ${dnsZone}</p>
                    
                    <div class="mt-4">
                        <h5>Next Steps:</h5>
                        <a href="https://ansibleaap.chrobinson.com/#/jobs/${data.job_id || ''}" target="_blank" class="btn btn-outline-primary">
                            <i class="fas fa-external-link-alt me-2"></i> View Job Output
                        </a>
                    </div>
                `;
            }
            
            statusModal.show();
        })
        .catch(error => {
            submitBtn.disabled = false;
            submitBtn.innerHTML = 'Schedule VM Retirement';
            
            statusContent.innerHTML = `
                <div class="alert alert-danger">
                    <h4>Error</h4>
                    <p>There was an error communicating with the server: ${error.message}</p>
                </div>
            `;
            
            statusModal.show();
        });
    });

    // Helper function to add days to a date
    function addDays(date, days) {
        const result = new Date(date);
        result.setDate(result.getDate() + days);
        return result;
    }

    // Helper function to format a date as YYYY/MM/DD
    function formatDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}/${month}/${day}`;
    }
});
