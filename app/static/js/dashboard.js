/**
 * Dashboard JavaScript for AutoScoring Application
 */

document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const uploadForm = document.getElementById('uploadForm');
    const studentUploadZone = document.getElementById('studentUploadZone');
    const studentFiles = document.getElementById('studentFiles');
    const studentFileList = document.getElementById('studentFileList');
    const answerKeyUploadZone = document.getElementById('answerKeyUploadZone');
    const answerKeyFile = document.getElementById('answerKeyFile');
    const answerKeyFileName = document.getElementById('answerKeyFileName');
    const questionDocUploadZone = document.getElementById('questionDocUploadZone');
    const questionDocFiles = document.getElementById('questionDocFiles');
    const questionDocFileList = document.getElementById('questionDocFileList');
    const additionalNotes = document.getElementById('additionalNotes');
    const submitBtn = document.getElementById('submitBtn');
    const progressContainer = document.getElementById('progressContainer');
    const progressBar = document.getElementById('progressBar');
    const progressMessage = document.getElementById('progressMessage');
    const resultContainer = document.getElementById('resultContainer');
    const resultAlert = document.getElementById('resultAlert');
    const resultMessage = document.getElementById('resultMessage');
    const downloadBtn = document.getElementById('downloadBtn');
    const newScoringBtn = document.getElementById('newScoringBtn');

    // Store selected files
    let selectedStudentFiles = [];
    let selectedQuestionDocs = [];

    // Allowed extensions for question documents
    const questionDocExtensions = [
        'pdf', 'doc', 'docx',
        'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'heic', 'heif',
        'tiff', 'tif', 'svg', 'ico', 'raw', 'cr2', 'nef', 'arw'
    ];

    // Student files upload zone
    studentUploadZone.addEventListener('click', () => studentFiles.click());
    studentUploadZone.addEventListener('dragover', handleDragOver);
    studentUploadZone.addEventListener('dragleave', handleDragLeave);
    studentUploadZone.addEventListener('drop', handleStudentDrop);
    studentFiles.addEventListener('change', handleStudentFileSelect);

    // Answer key upload zone
    answerKeyUploadZone.addEventListener('click', () => answerKeyFile.click());
    answerKeyUploadZone.addEventListener('dragover', handleDragOver);
    answerKeyUploadZone.addEventListener('dragleave', handleDragLeave);
    answerKeyUploadZone.addEventListener('drop', handleAnswerKeyDrop);
    answerKeyFile.addEventListener('change', handleAnswerKeySelect);

    // Question document upload zone
    if (questionDocUploadZone && questionDocFiles) {
        questionDocUploadZone.addEventListener('click', () => questionDocFiles.click());
        questionDocUploadZone.addEventListener('dragover', handleDragOver);
        questionDocUploadZone.addEventListener('dragleave', handleDragLeave);
        questionDocUploadZone.addEventListener('drop', handleQuestionDocDrop);
        questionDocFiles.addEventListener('change', handleQuestionDocSelect);
    }

    // Form submission
    uploadForm.addEventListener('submit', handleFormSubmit);

    // New scoring button
    newScoringBtn.addEventListener('click', resetForm);

    // Drag and drop handlers
    function handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        this.classList.add('dragover');
    }

    function handleDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        this.classList.remove('dragover');
    }

    function handleStudentDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        this.classList.remove('dragover');
        
        const files = Array.from(e.dataTransfer.files).filter(f => f.type === 'application/pdf');
        if (files.length > 0) {
            addStudentFiles(files);
        }
    }

    function handleAnswerKeyDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        this.classList.remove('dragover');
        
        const files = Array.from(e.dataTransfer.files).filter(f => f.type === 'application/pdf');
        if (files.length > 0) {
            setAnswerKeyFile(files[0]);
        }
    }

    function handleQuestionDocDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        this.classList.remove('dragover');
        
        const files = Array.from(e.dataTransfer.files).filter(f => isAllowedQuestionDoc(f));
        if (files.length > 0) {
            addQuestionDocs(files);
        }
    }

    // Check if file is allowed for question documents
    function isAllowedQuestionDoc(file) {
        const ext = file.name.split('.').pop().toLowerCase();
        return questionDocExtensions.includes(ext);
    }

    // File selection handlers
    function handleStudentFileSelect(e) {
        const files = Array.from(e.target.files);
        addStudentFiles(files);
    }

    function handleAnswerKeySelect(e) {
        if (e.target.files.length > 0) {
            setAnswerKeyFile(e.target.files[0]);
        }
    }

    function handleQuestionDocSelect(e) {
        const files = Array.from(e.target.files);
        addQuestionDocs(files);
    }

    // Add student files to list
    function addStudentFiles(files) {
        files.forEach(file => {
            // Check if already added
            if (!selectedStudentFiles.some(f => f.name === file.name && f.size === file.size)) {
                selectedStudentFiles.push(file);
            }
        });
        
        updateStudentFileList();
        updateUploadZoneState();
    }

    // Add question document files to list
    function addQuestionDocs(files) {
        // Limit to 10 files
        const remainingSlots = 10 - selectedQuestionDocs.length;
        const filesToAdd = files.slice(0, remainingSlots);
        
        filesToAdd.forEach(file => {
            // Check if already added
            if (!selectedQuestionDocs.some(f => f.name === file.name && f.size === file.size)) {
                selectedQuestionDocs.push(file);
            }
        });
        
        if (files.length > remainingSlots) {
            alert(`Hanya ${remainingSlots} file yang dapat ditambahkan. Maksimal 10 file dokumen soal.`);
        }
        
        updateQuestionDocFileList();
        updateQuestionDocUploadZoneState();
    }

    // Update student file list display
    function updateStudentFileList() {
        studentFileList.innerHTML = '';
        
        if (selectedStudentFiles.length === 0) {
            return;
        }

        const countBadge = document.createElement('div');
        countBadge.className = 'mb-2';
        countBadge.innerHTML = `<span class="badge bg-primary">${selectedStudentFiles.length} file dipilih</span>`;
        studentFileList.appendChild(countBadge);

        selectedStudentFiles.forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            
            // Safe DOM construction (no innerHTML with user data)
            const fileNameSpan = document.createElement('span');
            fileNameSpan.className = 'file-name';
            fileNameSpan.title = file.name;
            
            const icon = document.createElement('i');
            icon.className = 'bi bi-file-earmark-pdf text-danger me-2';
            fileNameSpan.appendChild(icon);
            fileNameSpan.appendChild(document.createTextNode(file.name));
            
            const removeSpan = document.createElement('span');
            removeSpan.className = 'remove-file';
            removeSpan.dataset.index = index;
            removeSpan.title = 'Hapus';
            
            const removeIcon = document.createElement('i');
            removeIcon.className = 'bi bi-x-circle';
            removeSpan.appendChild(removeIcon);
            
            fileItem.appendChild(fileNameSpan);
            fileItem.appendChild(removeSpan);
            studentFileList.appendChild(fileItem);
        });

        // Add remove file handlers
        document.querySelectorAll('#studentFileList .remove-file').forEach(btn => {
            btn.addEventListener('click', function() {
                const index = parseInt(this.dataset.index);
                selectedStudentFiles.splice(index, 1);
                updateStudentFileList();
                updateUploadZoneState();
            });
        });
    }

    // Update question document file list display
    function updateQuestionDocFileList() {
        if (!questionDocFileList) return;
        
        questionDocFileList.innerHTML = '';
        
        if (selectedQuestionDocs.length === 0) {
            return;
        }

        const countBadge = document.createElement('div');
        countBadge.className = 'mb-2';
        countBadge.innerHTML = `<span class="badge bg-info">${selectedQuestionDocs.length}/10 file dokumen soal</span>`;
        questionDocFileList.appendChild(countBadge);

        selectedQuestionDocs.forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            const ext = file.name.split('.').pop().toLowerCase();
            const isImage = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'heic', 'heif', 'tiff', 'tif'].includes(ext);
            const iconClass = isImage ? 'bi-file-earmark-image text-success' : 
                         (ext === 'pdf' ? 'bi-file-earmark-pdf text-danger' : 'bi-file-earmark-word text-primary');
            
            // Safe DOM construction (no innerHTML with user data)
            const fileNameSpan = document.createElement('span');
            fileNameSpan.className = 'file-name';
            fileNameSpan.title = file.name;
            
            const icon = document.createElement('i');
            icon.className = `bi ${iconClass} me-2`;
            fileNameSpan.appendChild(icon);
            fileNameSpan.appendChild(document.createTextNode(file.name));
            
            const removeSpan = document.createElement('span');
            removeSpan.className = 'remove-question-doc';
            removeSpan.dataset.index = index;
            removeSpan.title = 'Hapus';
            
            const removeIcon = document.createElement('i');
            removeIcon.className = 'bi bi-x-circle';
            removeSpan.appendChild(removeIcon);
            
            fileItem.appendChild(fileNameSpan);
            fileItem.appendChild(removeSpan);
            questionDocFileList.appendChild(fileItem);
        });

        // Add remove file handlers
        document.querySelectorAll('#questionDocFileList .remove-question-doc').forEach(btn => {
            btn.addEventListener('click', function() {
                const index = parseInt(this.dataset.index);
                selectedQuestionDocs.splice(index, 1);
                updateQuestionDocFileList();
                updateQuestionDocUploadZoneState();
            });
        });
    }

    // Update upload zone appearance
    function updateUploadZoneState() {
        if (selectedStudentFiles.length > 0) {
            studentUploadZone.classList.add('has-files');
        } else {
            studentUploadZone.classList.remove('has-files');
        }
    }

    // Update question doc upload zone appearance
    function updateQuestionDocUploadZoneState() {
        if (!questionDocUploadZone) return;
        
        if (selectedQuestionDocs.length > 0) {
            questionDocUploadZone.classList.add('has-files');
        } else {
            questionDocUploadZone.classList.remove('has-files');
        }
    }

    // Set answer key file
    function setAnswerKeyFile(file) {
        // Safe DOM construction (no innerHTML with user data)
        answerKeyFileName.innerHTML = '';
        
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        
        const fileNameSpan = document.createElement('span');
        fileNameSpan.className = 'file-name';
        fileNameSpan.title = file.name;
        
        const icon = document.createElement('i');
        icon.className = 'bi bi-file-earmark-check text-success me-2';
        fileNameSpan.appendChild(icon);
        fileNameSpan.appendChild(document.createTextNode(file.name));
        
        const removeSpan = document.createElement('span');
        removeSpan.className = 'remove-answer-key';
        removeSpan.title = 'Hapus';
        
        const removeIcon = document.createElement('i');
        removeIcon.className = 'bi bi-x-circle';
        removeSpan.appendChild(removeIcon);
        
        fileItem.appendChild(fileNameSpan);
        fileItem.appendChild(removeSpan);
        answerKeyFileName.appendChild(fileItem);
        
        answerKeyUploadZone.classList.add('has-files');

        // Add remove handler
        document.querySelector('.remove-answer-key').addEventListener('click', function() {
            answerKeyFile.value = '';
            answerKeyFileName.innerHTML = '';
            answerKeyUploadZone.classList.remove('has-files');
        });
    }

    // Form submission
    async function handleFormSubmit(e) {
        e.preventDefault();

        // Validate
        if (selectedStudentFiles.length === 0) {
            alert('Silakan pilih file laporan mahasiswa terlebih dahulu.');
            return;
        }

        const scoreMin = parseInt(document.getElementById('scoreMin').value);
        const scoreMax = parseInt(document.getElementById('scoreMax').value);

        if (scoreMin >= scoreMax) {
            alert('Nilai minimum harus lebih kecil dari nilai maksimum.');
            return;
        }

        // Prepare form data
        const formData = new FormData();
        formData.append('csrf_token', document.querySelector('[name=csrf_token]').value);
        formData.append('score_min', scoreMin);
        formData.append('score_max', scoreMax);
        formData.append('enable_evaluation', document.getElementById('enableEvaluation').checked);

        // Add student files
        selectedStudentFiles.forEach(file => {
            formData.append('student_files', file);
        });

        // Add answer key if selected
        if (answerKeyFile.files.length > 0) {
            formData.append('answer_key', answerKeyFile.files[0]);
        }

        // Add question documents if selected
        selectedQuestionDocs.forEach(file => {
            formData.append('question_documents', file);
        });

        // Add additional notes if provided
        if (additionalNotes && additionalNotes.value.trim()) {
            formData.append('additional_notes', additionalNotes.value.trim());
        }

        // Disable form and show progress
        setFormDisabled(true);
        showProgress();

        try {
            // Upload files
            updateProgress(0, 'Mengunggah dokumen...');
            
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (!result.success) {
                throw new Error(result.error || 'Terjadi kesalahan saat mengunggah file.');
            }

            // Start listening to progress
            const jobId = result.job_id;
            listenToProgress(jobId);

        } catch (error) {
            console.error('Upload error:', error);
            showError(error.message);
            setFormDisabled(false);
            hideProgress();
        }
    }

    // Listen to SSE progress updates
    function listenToProgress(jobId) {
        const eventSource = new EventSource(`/api/progress/${jobId}`);

        eventSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            
            updateProgress(data.progress, data.message);

            if (data.status === 'completed') {
                eventSource.close();
                showResult(jobId, data.message);
            } else if (data.status === 'failed' || data.status === 'error') {
                eventSource.close();
                showError(data.message);
                setFormDisabled(false);
            }
        };

        eventSource.onerror = function(error) {
            console.error('SSE error:', error);
            eventSource.close();
            // Try polling as fallback
            pollProgress(jobId);
        };
    }

    // Fallback polling for progress
    async function pollProgress(jobId) {
        const checkProgress = async () => {
            try {
                const response = await fetch(`/api/job/${jobId}`);
                const data = await response.json();

                if (!data.success) {
                    throw new Error(data.error);
                }

                const job = data.job;
                const progress = (job.processed_files / job.total_files) * 100;
                updateProgress(progress, job.status_message || 'Memproses...');

                if (job.status === 'completed') {
                    showResult(jobId, `Berhasil menilai ${job.total_files} laporan.`);
                } else if (job.status === 'failed') {
                    showError(job.status_message || 'Terjadi kesalahan.');
                    setFormDisabled(false);
                } else {
                    // Continue polling
                    setTimeout(checkProgress, 2000);
                }
            } catch (error) {
                console.error('Poll error:', error);
                showError('Gagal memantau progress. Silakan refresh halaman.');
                setFormDisabled(false);
            }
        };

        checkProgress();
    }

    // Update progress display
    function updateProgress(percent, message) {
        progressBar.style.width = `${percent}%`;
        progressBar.textContent = `${Math.round(percent)}%`;
        progressMessage.textContent = message;
    }

    // Show progress container
    function showProgress() {
        progressContainer.classList.add('active');
        resultContainer.classList.remove('active');
    }

    // Hide progress container
    function hideProgress() {
        progressContainer.classList.remove('active');
    }

    // Show result
    function showResult(jobId, message) {
        hideProgress();
        
        resultAlert.className = 'alert alert-success';
        resultAlert.querySelector('.alert-heading').innerHTML = '<i class="bi bi-check-circle me-2"></i>Penilaian Selesai!';
        resultMessage.textContent = message;
        downloadBtn.href = `/api/download/${jobId}`;
        
        resultContainer.classList.add('active');
        setFormDisabled(false);
    }

    // Show error
    function showError(message) {
        hideProgress();
        
        resultAlert.className = 'alert alert-danger';
        resultAlert.querySelector('.alert-heading').innerHTML = '<i class="bi bi-exclamation-circle me-2"></i>Terjadi Kesalahan';
        resultMessage.textContent = message;
        downloadBtn.style.display = 'none';
        
        resultContainer.classList.add('active');
    }

    // Set form disabled state
    function setFormDisabled(disabled) {
        submitBtn.disabled = disabled;
        studentFiles.disabled = disabled;
        answerKeyFile.disabled = disabled;
        if (questionDocFiles) questionDocFiles.disabled = disabled;
        if (additionalNotes) additionalNotes.disabled = disabled;
        document.getElementById('scoreMin').disabled = disabled;
        document.getElementById('scoreMax').disabled = disabled;
        document.getElementById('enableEvaluation').disabled = disabled;

        if (disabled) {
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Memproses...';
            studentUploadZone.style.pointerEvents = 'none';
            answerKeyUploadZone.style.pointerEvents = 'none';
            if (questionDocUploadZone) questionDocUploadZone.style.pointerEvents = 'none';
        } else {
            submitBtn.innerHTML = '<i class="bi bi-play-circle me-2"></i>Mulai Penilaian';
            studentUploadZone.style.pointerEvents = 'auto';
            answerKeyUploadZone.style.pointerEvents = 'auto';
            if (questionDocUploadZone) questionDocUploadZone.style.pointerEvents = 'auto';
        }
    }

    // Reset form for new scoring
    function resetForm() {
        // Clear selected files
        selectedStudentFiles = [];
        selectedQuestionDocs = [];
        studentFiles.value = '';
        answerKeyFile.value = '';
        if (questionDocFiles) questionDocFiles.value = '';
        if (additionalNotes) additionalNotes.value = '';
        
        // Clear displays
        studentFileList.innerHTML = '';
        answerKeyFileName.innerHTML = '';
        if (questionDocFileList) questionDocFileList.innerHTML = '';
        studentUploadZone.classList.remove('has-files');
        answerKeyUploadZone.classList.remove('has-files');
        if (questionDocUploadZone) questionDocUploadZone.classList.remove('has-files');
        
        // Hide result
        resultContainer.classList.remove('active');
        downloadBtn.style.display = '';
        
        // Reset progress
        updateProgress(0, 'Mempersiapkan...');
        
        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
});
