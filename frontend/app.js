// TruthGuard AI - Enhanced Frontend Application

class TruthGuardAI {
    constructor() {
        this.apiBaseUrl = 'https://truthguard-ai-nwp9.onrender.com';
        this.currentTab = 'text';
        this.initializeApp();
    }

    initializeApp() {
        this.setupEventListeners();
        this.loadSystemStats();
    }

    setupEventListeners() {
        // Tab navigation
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        // Text analysis
        document.getElementById('analyzeBtn').addEventListener('click', () => this.analyzeText());
        document.getElementById('contentInput').addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') this.analyzeText();
        });

        // Image upload
        document.getElementById('imageInput').addEventListener('change', (e) => this.handleImageUpload(e));
        document.getElementById('uploadArea').addEventListener('click', () => {
            document.getElementById('imageInput').click();
        });

        // Drag and drop for images
        const uploadArea = document.getElementById('uploadArea');
        uploadArea.addEventListener('dragover', (e) => e.preventDefault());
        uploadArea.addEventListener('drop', (e) => this.handleImageDrop(e));
    }

    switchTab(tabName) {
        // Update active tab
        document.querySelectorAll('.nav-tab').forEach(tab => tab.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
        
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        document.getElementById(`${tabName}-tab`).classList.add('active');
        
        this.currentTab = tabName;
    }

    async analyzeText() {
        const content = document.getElementById('contentInput').value.trim();
        if (!content) {
            this.showAlert('Please enter some content to analyze.', 'warning');
            return;
        }

        this.showLoading(true);
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/check`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    content: content,
                    content_type: 'text',
                    language: document.getElementById('languageSelect').value,
                    include_education: document.getElementById('includeEducation').checked
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            this.displayResults(result);
            
        } catch (error) {
            console.error('Analysis error:', error);
            this.showAlert('Failed to analyze content. Please try again.', 'error');
        } finally {
            this.showLoading(false);
        }
    }

    displayResults(result) {
        // Show results section
        document.getElementById('resultsSection').style.display = 'block';
        
        // Update trust score
        this.updateTrustScore(result.overall_trust_score, result.overall_verdict);
        
        // Display claims
        this.displayClaims(result.claims);
        
        // Display explanation
        document.getElementById('explanationText').textContent = result.explanation;
        
        // Display sources
        this.displaySources(result.sources);
        
        // Display educational content
        if (result.educational_insights) {
            this.displayEducationalInsights(result.educational_insights);
        }

        // Scroll to results
        document.getElementById('resultsSection').scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start' 
        });
    }

    updateTrustScore(score, verdict) {
        const scoreElement = document.getElementById('trustScore');
        const verdictElement = document.getElementById('verdict');
        
        scoreElement.textContent = Math.round(score);
        verdictElement.textContent = verdict;
        
        // Apply color coding
        const scoreCircle = document.querySelector('.score-circle');
        scoreCircle.className = 'score-circle';
        
        if (score >= 80) {
            scoreCircle.classList.add('high');
            verdictElement.className = 'verdict high';
        } else if (score >= 60) {
            scoreCircle.classList.add('medium');
            verdictElement.className = 'verdict medium';
        } else {
            scoreCircle.classList.add('low');
            verdictElement.className = 'verdict low';
        }
    }

    displayClaims(claims) {
        const claimsList = document.getElementById('claimsList');
        claimsList.innerHTML = '';
        
        claims.forEach((claim, index) => {
            const claimElement = document.createElement('div');
            claimElement.className = `claim-item ${claim.trust_level.toLowerCase()}`;
            
            claimElement.innerHTML = `
                <div class="claim-header">
                    <span class="claim-index">#${index + 1}</span>
                    <span class="claim-status ${claim.trust_level.toLowerCase()}">${claim.trust_level}</span>
                    <span class="claim-confidence">${Math.round(claim.confidence)}% confidence</span>
                </div>
                <div class="claim-text">${claim.claim_text}</div>
                <div class="claim-explanation">${claim.explanation}</div>
                ${claim.manipulation_techniques.length > 0 ? 
                    `<div class="manipulation-techniques">
                        <strong>Detected techniques:</strong> 
                        ${claim.manipulation_techniques.map(tech => `<span class="technique-tag">${tech}</span>`).join('')}
                    </div>` : ''
                }
            `;
            
            claimsList.appendChild(claimElement);
        });
    }

    displaySources(sources) {
        const sourcesList = document.getElementById('sourcesList');
        sourcesList.innerHTML = '';
        
        sources.forEach(source => {
            const li = document.createElement('li');
            li.innerHTML = `<i class="fas fa-external-link-alt"></i> ${source}`;
            sourcesList.appendChild(li);
        });
    }

    displayEducationalInsights(insights) {
        const educationalSection = document.getElementById('educationalSection');
        const educationalContent = document.getElementById('educationalContent');
        
        educationalContent.innerHTML = '';
        
        if (insights.manipulation_techniques_detected && insights.manipulation_techniques_detected.length > 0) {
            const techniquesDiv = document.createElement('div');
            techniquesDiv.className = 'educational-subsection';
            techniquesDiv.innerHTML = `
                <h4><i class="fas fa-exclamation-triangle"></i> Manipulation Techniques Detected</h4>
                ${insights.manipulation_techniques_detected.map(tech => `
                    <div class="technique-explanation">
                        <strong>${tech}:</strong> 
                        ${insights.technique_explanations[tech]?.description || 'Technique used to mislead readers'}
                        ${insights.technique_explanations[tech]?.detection_tips ? 
                            `<br><em>Tips:</em> ${insights.technique_explanations[tech].detection_tips.join(', ')}` : ''
                        }
                    </div>
                `).join('')}
            `;
            educationalContent.appendChild(techniquesDiv);
        }

        if (insights.verification_tips) {
            const tipsDiv = document.createElement('div');
            tipsDiv.className = 'educational-subsection';
            tipsDiv.innerHTML = `
                <h4><i class="fas fa-lightbulb"></i> Verification Tips</h4>
                <ul>
                    ${insights.verification_tips.map(tip => `<li>${tip}</li>`).join('')}
                </ul>
            `;
            educationalContent.appendChild(tipsDiv);
        }

        educationalSection.style.display = 'block';
    }

    async handleImageUpload(event) {
        const file = event.target.files[0];
        if (file) {
            this.displayImagePreview(file);
        }
    }

    handleImageDrop(event) {
        event.preventDefault();
        const file = event.dataTransfer.files[0];
        if (file && file.type.startsWith('image/')) {
            document.getElementById('imageInput').files = event.dataTransfer.files;
            this.displayImagePreview(file);
        }
    }

    displayImagePreview(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            document.getElementById('previewImg').src = e.target.result;
            document.getElementById('imagePreview').style.display = 'block';
            
            document.getElementById('analyzeImageBtn').onclick = () => this.analyzeImage(file);
        };
        reader.readAsDataURL(file);
    }

    async analyzeImage(file) {
        this.showLoading(true);
        
        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch(`${this.apiBaseUrl}/check-image`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            
            // Switch to text tab to show results
            this.switchTab('text');
            this.displayResults(result);
            
        } catch (error) {
            console.error('Image analysis error:', error);
            this.showAlert('Failed to analyze image. Please try again.', 'error');
        } finally {
            this.showLoading(false);
        }
    }

    async loadSystemStats() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/stats`);
            const stats = await response.json();
            
            document.getElementById('languagesSupported').textContent = stats.supported_languages || 6;
            
        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    }

    showLoading(show) {
        document.getElementById('loadingModal').style.display = show ? 'flex' : 'none';
    }

    showAlert(message, type = 'info') {
        // Create alert element
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.innerHTML = `
            <i class="fas fa-${type === 'error' ? 'exclamation-circle' : type === 'warning' ? 'exclamation-triangle' : 'info-circle'}"></i>
            <span>${message}</span>
            <button class="alert-close">&times;</button>
        `;
        
        // Add to page
        document.body.appendChild(alert);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (alert.parentNode) {
                alert.parentNode.removeChild(alert);
            }
        }, 5000);
        
        // Manual close
        alert.querySelector('.alert-close').onclick = () => {
            if (alert.parentNode) {
                alert.parentNode.removeChild(alert);
            }
        };
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    new TruthGuardAI();
});

// Sample data for testing
window.sampleTexts = {
    misinformation: "COVID-19 vaccines contain microchips that track your location and can control your thoughts through 5G networks.",
    misleading: "The government has completely banned beef consumption across all states in India.",
    verified: "The Reserve Bank of India announced the repo rate decision in its latest monetary policy meeting."
};

// Add sample text buttons
document.addEventListener('DOMContentLoaded', () => {
    const inputGroup = document.querySelector('.input-group');
    const sampleButtons = document.createElement('div');
    sampleButtons.className = 'sample-buttons';
    sampleButtons.innerHTML = `
        <p>Try sample texts:</p>
        <button onclick="document.getElementById('contentInput').value = window.sampleTexts.misinformation" class="btn-sample">Misinformation Sample</button>
        <button onclick="document.getElementById('contentInput').value = window.sampleTexts.misleading" class="btn-sample">Misleading Sample</button>
        <button onclick="document.getElementById('contentInput').value = window.sampleTexts.verified" class="btn-sample">Verified Sample</button>
    `;
    inputGroup.appendChild(sampleButtons);
});



